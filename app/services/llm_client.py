# app/services/llm_client.py
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMUpstreamError(RuntimeError):
    def __init__(
        self,
        provider: str,
        status: Optional[int] = None,
        message: str = "",
        body_snippet: Optional[str] = None,
        code: str = "LLM_FAILED",
    ):
        super().__init__(message)
        self.provider = provider
        self.status = status
        self.body_snippet = body_snippet
        self.code = code

    def __repr__(self) -> str:
        parts = [f"provider={self.provider}"]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.body_snippet:
            parts.append(f"body={self.body_snippet[:80]}")
        if self.args and self.args[0]:
            parts.append(f"msg={self.args[0]}")
        return f"LLMUpstreamError({', '.join(parts)})"


def _build_url(base: str, path: str) -> str:
    base = (base or "").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _safe_host(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        return parsed.netloc or url
    except Exception:
        return url


def describe_llm_config(model: Optional[str] = None) -> Dict[str, Any]:
    primary_model = model or settings.LLM_MODEL
    fallback_model = settings.LLM_FALLBACK_MODEL or settings.LLM_MODEL or model
    return {
        "mode": settings.LLM_MODE,
        "primary": {
            "model": primary_model,
            "base_url": settings.LLM_PRIMARY_BASE_URL,
            "path": settings.LLM_PRIMARY_PATH,
            "host": _safe_host(settings.LLM_PRIMARY_BASE_URL),
        },
        "fallback": {
            "model": fallback_model,
            "base_url": settings.LLM_FALLBACK_BASE_URL,
            "path": settings.LLM_FALLBACK_PATH,
            "host": _safe_host(settings.LLM_FALLBACK_BASE_URL),
            "kind": (settings.LLM_FALLBACK_KIND or "same_as_primary"),
        },
    }


def validate_llm_config() -> None:
    if not settings.LLM_PRIMARY_BASE_URL:
        raise RuntimeError("LLM_PRIMARY_BASE_URL is not set; add it to your .env for local dev.")
    if not settings.LLM_PRIMARY_PATH:
        raise RuntimeError("LLM_PRIMARY_PATH is not set; add it to your .env for local dev.")
    if not settings.LLM_MODEL:
        raise RuntimeError("LLM_MODEL is not set; add it to your .env for local dev.")


def _build_payload(kind: str, model: str, messages: List[Dict[str, str]], endpoint_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Adapter for upstream payloads.
    - mode chat: {"model": "...", "messages": [...], "stream": false}
    - mode generate (internal/ollama-generate-like): {"model": "...", "prompt": "...", "stream": false}
    """
    mode = (settings.LLM_MODE or "chat").lower()
    path = (endpoint_path or "").lower()
    if path.endswith("/generate"):
        mode = "generate"
    elif path.endswith("/chat"):
        mode = "chat"

    def to_prompt(msgs: List[Dict[str, str]]) -> str:
        lines = [f"{m.get('role','user')}: {m.get('content','')}" for m in msgs]
        last_user = next((m for m in reversed(msgs) if m.get("role") == "user"), None)
        if last_user:
            lines.append(f"Answer the last user message directly: {last_user.get('content','')}")
        return "\n".join(lines)

    if kind == "ollama":
        if mode == "generate":
            return {"model": model, "prompt": to_prompt(messages), "stream": False}
        return {"model": model, "messages": messages, "stream": False}

    if mode == "generate":
        return {"model": model, "prompt": to_prompt(messages), "stream": False}

    return {"model": model, "messages": messages, "stream": False}


def _extract_assistant(kind: str, data: Any) -> str:
    """
    Extract assistant text from a *single* upstream JSON object.
    Important: If upstream contains the canonical text field but it's empty,
    we return "" (not an exception). Empty handling is done by caller.
    """
    if not isinstance(data, dict):
        return str(data) if data is not None else ""

    # 1) chat-style: {"message":{"content":...}}
    msg = data.get("message")
    if isinstance(msg, dict) and "content" in msg:
        c = msg.get("content")
        if isinstance(c, str):
            return c
        if c is not None:
            return str(c)
        return ""

    # 2) internal/generate-style: {"response": "...", "done": ...}
    if "response" in data:
        v = data.get("response")
        if isinstance(v, str):
            return v
        if v is not None:
            return str(v)
        return ""

    # 3) OpenAI-like: {"choices":[...]}
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        for choice in reversed(choices):
            if not isinstance(choice, dict):
                continue
            m = choice.get("message")
            if isinstance(m, dict) and "content" in m:
                c = m.get("content")
                if isinstance(c, str):
                    return c
                if c is not None:
                    return str(c)
                return ""
            if "text" in choice:
                t = choice.get("text")
                if isinstance(t, str):
                    return t
                if t is not None:
                    return str(t)
                return ""

    # 4) Generic fallbacks
    for key in ("assistant_content", "output_text", "text", "content", "assistant"):
        if key in data:
            v = data.get(key)
            if isinstance(v, str):
                return v
            if v is not None:
                return str(v)
            return ""

    # If nothing matches, this is a real schema mismatch
    raise ValueError(f"Could not extract assistant text from keys: {list(data.keys())}")


def _should_fallback(exc: LLMUpstreamError) -> bool:
    return exc.status in {502, 503, 504} or exc.status is None or exc.code == "MODEL_NOT_AVAILABLE"


def _looks_like_stream(text: str, content_type: str) -> bool:
    ct = (content_type or "").lower()
    if "text/event-stream" in ct or "application/x-ndjson" in ct:
        return True
    # Heuristic: multiple JSON objects separated by newlines or SSE 'data:' frames
    if "\n" in (text or "") and ("data:" in text or text.strip().count("\n") >= 1):
        return True
    return False


def _iter_stream_frames(raw_text: str) -> List[str]:
    """
    Supports:
      - SSE frames: lines like 'data: {json}'
      - NDJSON: one JSON object per line
      - Loose: ignores blank lines
    """
    frames: List[str] = []
    for line in (raw_text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("data:"):
            s = s[len("data:") :].strip()
        if s in ("[DONE]", "DONE"):
            continue
        frames.append(s)
    return frames


def _parse_one_or_stream_json(kind: str, text: str, content_type: str) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (assistant_text, debug_info).
    If response is streaming-like, aggregates assistant text across frames.
    """
    debug: Dict[str, Any] = {}

    # First, try single JSON
    try:
        data = json.loads(text)
        assistant = _extract_assistant(kind, data)
        debug["mode"] = "single_json"
        debug["keys"] = list(data.keys()) if isinstance(data, dict) else type(data)
        return assistant, debug
    except Exception as single_exc:
        debug["single_json_error"] = repr(single_exc)

    # If not single JSON, attempt stream aggregation
    frames = _iter_stream_frames(text)
    aggregated: List[str] = []
    last_obj: Any = None
    done = None
    done_reason = None
    parsed_frames = 0

    for frame in frames:
        try:
            obj = json.loads(frame)
        except Exception:
            # ignore non-json lines
            continue

        parsed_frames += 1
        last_obj = obj

        # accumulate text chunks (can be empty for heartbeat frames)
        try:
            chunk = _extract_assistant(kind, obj)
        except ValueError:
            chunk = ""  # schema mismatch inside stream: ignore for aggregation

        if chunk:
            aggregated.append(chunk)

        if isinstance(obj, dict):
            if "done" in obj:
                done = obj.get("done")
            if "done_reason" in obj:
                done_reason = obj.get("done_reason")

    debug["mode"] = "stream_aggregate"
    debug["parsed_frames"] = parsed_frames
    if isinstance(last_obj, dict):
        debug["last_keys"] = list(last_obj.keys())
        debug["done"] = done
        debug["done_reason"] = done_reason

    if aggregated:
        return "".join(aggregated), debug

    # If we parsed frames but got no text, try last_obj's response-like fields (even if empty)
    if last_obj is not None:
        try:
            last_text = _extract_assistant(kind, last_obj)
            return last_text, debug
        except Exception:
            pass

    # Nothing usable
    raise ValueError("No parsable assistant content found in stream-like response.")


async def _post_llm(
    provider: str,
    base: str,
    path: str,
    payload: Dict[str, Any],
    kind: str,
    timeout: httpx.Timeout,
    verify: bool,
    request_id: str,
) -> str:
    url = _build_url(base, path)
    headers = {"Cache-Control": "no-store", "X-Request-ID": request_id}

    try:
        async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
            resp = await client.post(url, json=payload, headers=headers)

        status = resp.status_code
        text = resp.text or ""
        ct = resp.headers.get("content-type", "")

        if settings.APP_ENV == "dev":
            last_user = (
                next((m for m in reversed(payload.get("messages", [])) if m.get("role") == "user"), None)
                if isinstance(payload, dict)
                else None
            )
            logger.info(
                "LLM request debug",
                extra={
                    "provider": provider,
                    "url": url,
                    "model": payload.get("model") if isinstance(payload, dict) else None,
                    "msg_count": len(payload.get("messages", [])) if isinstance(payload, dict) else None,
                    "last_user_len": len(last_user.get("content", "")) if last_user else None,
                    "resp_status": status,
                    "resp_ct": ct,
                    "resp_snippet": text[:300],
                },
            )

        if status >= 400:
            snippet = text[:200]
            logger.warning(
                "LLM provider error",
                extra={"provider": provider, "url": url, "status": status, "body_snippet": snippet},
            )
            msg = f"status={status}"
            code = "LLM_FAILED"
            if status == 404:
                code = "MODEL_NOT_AVAILABLE"
                msg = "Model not available on current provider" if kind != "ollama" else "Fallback Ollama model not available. Run: ollama pull <model>"
            raise LLMUpstreamError(provider=provider, status=status, message=msg, body_snippet=snippet, code=code)

        # Parse single JSON or aggregate stream
        try:
            assistant, parse_debug = _parse_one_or_stream_json(kind, text, ct)
        except ValueError as exc:
            # Schema mismatch / stream parse failure: 502 (bad gateway)
            raise LLMUpstreamError(
                provider=provider,
                status=502,
                message=f"LLM response parse failed: {exc}",
                body_snippet=(text[:300] if text else None),
                code="BAD_UPSTREAM_SCHEMA",
            )

        if settings.APP_ENV == "dev":
            logger.info(
                "LLM response parse debug",
                extra={
                    "provider": provider,
                    "parse_mode": parse_debug.get("mode"),
                    "parsed_frames": parse_debug.get("parsed_frames"),
                    "done": parse_debug.get("done"),
                    "done_reason": parse_debug.get("done_reason"),
                    "resp_keys": parse_debug.get("keys") or parse_debug.get("last_keys"),
                    "assistant_len": len(assistant or ""),
                    "assistant_preview": (assistant or "")[:120],
                },
            )

        # Empty completion → classify properly so retry/fallback works
        if assistant is None or not str(assistant).strip():
            raise LLMUpstreamError(
                provider=provider,
                status=status,
                message="empty assistant_content",
                body_snippet=(text[:300] if text else None),
                code="EMPTY_COMPLETION",
            )

        return assistant

    except httpx.HTTPError as exc:
        logger.warning(
            "LLM provider httpx error",
            extra={"provider": provider, "url": url, "exc": repr(exc)},
        )
        status = exc.response.status_code if getattr(exc, "response", None) is not None else None
        raise LLMUpstreamError(provider=provider, status=status, message=repr(exc), code="HTTP_ERROR")


async def generate(model: Optional[str], messages: List[Dict[str, str]]) -> str:
    validate_llm_config()

    requested_model = model or settings.LLM_MODEL
    if not requested_model:
        raise RuntimeError("LLM_MODEL must be configured (env LLM_MODEL).")

    # Ensure a system prompt to reduce echoing user input on minimal models.
    msgs = list(messages) if messages else []
    has_system = any((m.get("role") or "").lower() == "system" for m in msgs)
    if not has_system:
        msgs = [{"role": "system", "content": settings.LLM_SYSTEM_PROMPT}] + msgs

    timeout = httpx.Timeout(
        connect=float(settings.LLM_CONNECT_TIMEOUT),
        read=float(settings.LLM_READ_TIMEOUT),
        write=float(settings.LLM_READ_TIMEOUT),
        pool=5.0,
    )
    verify_flag = settings.LLM_TLS_VERIFY
    request_id = uuid.uuid4().hex

    primary_payload = _build_payload(
        "same_as_primary",
        requested_model,
        msgs,
        settings.LLM_PRIMARY_PATH,
    )

    def should_retry(exc: LLMUpstreamError) -> bool:
        # Retry on transient connectivity and on empty completions (common with stream end frames / flaky upstream)
        return _should_fallback(exc) or exc.code == "EMPTY_COMPLETION"

    max_retries = max(0, int(settings.LLM_MAX_RETRIES))
    attempt = 0
    backoffs = [0.5, 1.5, 3.0]

    primary_error: LLMUpstreamError | None = None

    while True:
        try:
            return await _post_llm(
                provider="primary",
                base=settings.LLM_PRIMARY_BASE_URL,
                path=settings.LLM_PRIMARY_PATH,
                payload=primary_payload,
                kind="same_as_primary",
                timeout=timeout,
                verify=verify_flag,
                request_id=request_id,
            )
        except LLMUpstreamError as exc:
            primary_error = exc
            if attempt >= max_retries or not should_retry(exc):
                break
            import asyncio

            await asyncio.sleep(backoffs[min(attempt, len(backoffs) - 1)])
            attempt += 1

    if not primary_error:
        raise LLMUpstreamError(provider="primary", status=None, message="unknown LLM failure", code="LLM_FAILED")

    # Fallback
    if not _should_fallback(primary_error) or not settings.LLM_FALLBACK_BASE_URL:
        raise primary_error

    fallback_kind = (settings.LLM_FALLBACK_KIND or "same_as_primary").lower()
    fallback_model = settings.LLM_FALLBACK_MODEL or settings.LLM_MODEL or requested_model

    if settings.APP_ENV in ("dev", "local") and fallback_model != requested_model:
        logger.warning("Fallback model override", extra={"requested": requested_model, "using": fallback_model})

    fallback_payload = _build_payload(
        fallback_kind,
        fallback_model,
        msgs,
        settings.LLM_FALLBACK_PATH,
    )

    try:
        return await _post_llm(
            provider="fallback",
            base=settings.LLM_FALLBACK_BASE_URL,
            path=settings.LLM_FALLBACK_PATH,
            payload=fallback_payload,
            kind=fallback_kind,
            timeout=timeout,
            verify=verify_flag,
            request_id=request_id,
        )
    except LLMUpstreamError as fallback_error:
        msg = f"Upstream LLM unavailable (primary status={primary_error.status}, fallback status={fallback_error.status})"
        raise LLMUpstreamError(
            provider="fallback",
            status=fallback_error.status,
            message=msg,
            body_snippet=fallback_error.body_snippet,
            code="LLM_FAILED",
        )


async def health_check() -> Dict[str, Any]:
    timeout = httpx.Timeout(connect=2.0, read=3.0, write=3.0, pool=3.0)
    verify_flag = settings.LLM_TLS_VERIFY
    request_id = uuid.uuid4().hex

    payload = _build_payload(
        "same_as_primary",
        settings.LLM_MODEL or "health-check",
        [{"role": "user", "content": "ping"}],
        settings.LLM_PRIMARY_PATH,
    )

    def ok_dict(ok: bool, status: Optional[int], error: Optional[str]):
        return {"ok": ok, "status": status, "error": error}

    primary_status: Dict[str, Any]
    try:
        await _post_llm(
            provider="primary",
            base=settings.LLM_PRIMARY_BASE_URL,
            path=settings.LLM_PRIMARY_PATH,
            payload=payload,
            kind="same_as_primary",
            timeout=timeout,
            verify=verify_flag,
            request_id=request_id,
        )
        primary_status = ok_dict(True, 200, None)
    except LLMUpstreamError as exc:
        primary_status = ok_dict(False, exc.status, repr(exc))

    fallback_status: Dict[str, Any] = ok_dict(False, None, "not configured")
    if settings.LLM_FALLBACK_BASE_URL:
        fallback_kind = (settings.LLM_FALLBACK_KIND or "same_as_primary").lower()
        fb_model = settings.LLM_FALLBACK_MODEL or "health-check"
        fb_payload = _build_payload(
            fallback_kind,
            fb_model,
            [{"role": "user", "content": "ping"}],
            settings.LLM_FALLBACK_PATH,
        )

        try:
            await _post_llm(
                provider="fallback",
                base=settings.LLM_FALLBACK_BASE_URL,
                path=settings.LLM_FALLBACK_PATH,
                payload=fb_payload,
                kind=fallback_kind,
                timeout=timeout,
                verify=verify_flag,
                request_id=request_id,
            )
            fallback_status = ok_dict(True, 200, None)
        except LLMUpstreamError as exc:
            fallback_status = ok_dict(False, exc.status, repr(exc))

    return {"primary": primary_status, "fallback": fallback_status, "config": describe_llm_config()}
