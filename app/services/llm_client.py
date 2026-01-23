from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
    base = base.rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def _build_payload(kind: str, model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Adapter for upstream payloads.
    - mode chat: {"model": "...", "messages": [...], "stream": false}
    - mode generate (ollama generate-like): {"model": "...", "prompt": "...", "stream": false}
    - ollama chat: {"model": "...", "messages": [...], "stream": false}
    """
    mode = (settings.LLM_MODE or "chat").lower()
    if kind == "ollama":
        if mode == "generate":
            lines = [f"{m.get('role','user')}: {m.get('content','')}" for m in messages]
            last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
            if last_user:
                lines.append(f"Answer the last user message directly: {last_user.get('content','')}")
            prompt = "\n".join(lines)
            return {"model": model, "prompt": prompt, "stream": False}
        return {"model": model, "messages": messages, "stream": False}
    if mode == "generate":
        lines = [f"{m.get('role','user')}: {m.get('content','')}" for m in messages]
        last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        if last_user:
            lines.append(f"Answer the last user message directly: {last_user.get('content','')}")
        prompt = "\n".join(lines)
        return {"model": model, "prompt": prompt, "stream": False}
    return {"model": model, "messages": messages, "stream": False}


def _extract_assistant(kind: str, data: Dict[str, Any]) -> str:
    """
    Robust extractor for various upstream shapes:
    - {"message": {"content": "..."}}
    - {"response": "..."} / {"content": "..."} / {"assistant": "..."}
    - {"choices":[...]} (use the last choice if present)
    - {"text": "..."} / {"output_text": "..."}
    """
    if isinstance(data, dict):
        if "message" in data and isinstance(data.get("message"), dict):
            if "content" in data["message"]:
                return data["message"]["content"]
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            choice = (data["choices"][-1] or data["choices"][0]) if data["choices"] else {}
            if isinstance(choice, dict):
                msg = choice.get("message") or {}
                if isinstance(msg, dict) and msg.get("content"):
                    return msg["content"]
                if choice.get("text"):
                    return choice["text"]
        for key in ("response", "assistant_content", "output_text", "text", "content", "assistant"):
            if key in data and isinstance(data.get(key), str) and data.get(key):
                return data[key]
    raise ValueError(f"Could not extract assistant text from keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")


def _should_fallback(exc: LLMUpstreamError) -> bool:
    return exc.status in {502, 503, 504} or exc.status is None


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
        if settings.APP_ENV == "dev":
            last_user = next((m for m in reversed(payload.get("messages", [])) if m.get("role") == "user"), None) if isinstance(payload, dict) else None
            logger.info(
                "LLM request debug",
                extra={
                    "provider": provider,
                    "url": url,
                    "model": payload.get("model") if isinstance(payload, dict) else None,
                    "msg_count": len(payload.get("messages", [])) if isinstance(payload, dict) else None,
                    "last_user_len": len(last_user.get("content", "")) if last_user else None,
                    "resp_status": status,
                    "resp_ct": resp.headers.get("content-type"),
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
                if kind == "ollama":
                    msg = "Fallback Ollama model not available. Run: ollama pull <model>"
                else:
                    msg = "Model not available on current provider"
            raise LLMUpstreamError(provider=provider, status=status, message=msg, body_snippet=snippet, code=code)
        try:
            data = resp.json()
        except Exception as exc:  # pragma: no cover - defensive
            raise LLMUpstreamError(provider=provider, status=status, message=f"invalid json: {exc}", body_snippet=text[:200])
        assistant = _extract_assistant(kind, data)
        if not assistant or not str(assistant).strip():
            raise LLMUpstreamError(
                provider=provider,
                status=status,
                message="empty assistant_content",
                body_snippet=str(data)[:200],
                code="EMPTY_COMPLETION",
            )
        if settings.APP_ENV == "dev":
            logger.info(
                "LLM response parsed",
                extra={
                    "provider": provider,
                    "assistant_len": len(assistant),
                    "assistant_preview": assistant[:80],
                    "resp_keys": list(data.keys()) if isinstance(data, dict) else type(data),
                    "resp_raw_preview": text[:300],
                },
            )
        return assistant
    except httpx.HTTPError as exc:
        logger.warning(
            "LLM provider httpx error",
            extra={"provider": provider, "url": url, "exc": repr(exc)},
        )
        status = exc.response.status_code if getattr(exc, "response", None) is not None else None
        raise LLMUpstreamError(provider=provider, status=status, message=repr(exc))


async def generate(model: str, messages: List[Dict[str, str]]) -> str:
    timeout = httpx.Timeout(
        connect=float(settings.LLM_CONNECT_TIMEOUT),
        read=float(settings.LLM_READ_TIMEOUT),
        write=float(settings.LLM_READ_TIMEOUT),
        pool=5.0,
    )
    verify_flag = settings.LLM_TLS_VERIFY
    import uuid
    request_id = uuid.uuid4().hex

    primary_payload = _build_payload("same_as_primary", model, messages)
    primary_error: LLMUpstreamError | None = None

    def should_retry(exc: LLMUpstreamError) -> bool:
        return _should_fallback(exc) or exc.code == "EMPTY_COMPLETION"

    max_retries = max(0, int(settings.LLM_MAX_RETRIES))

    attempt = 0
    primary_error = None
    backoffs = [0.5, 1.5, 3.0]
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

    # Fallback
    if not _should_fallback(primary_error) or not settings.LLM_FALLBACK_BASE_URL:
        raise primary_error  # type: ignore

    fallback_kind = (settings.LLM_FALLBACK_KIND or "same_as_primary").lower()
    # Ignore requested model for fallback; always use configured fallback model
    fallback_model = settings.LLM_FALLBACK_MODEL or model
    if settings.APP_ENV in ("dev", "local") and fallback_model != model:
        logger.warning("Fallback model override", extra={"requested": model, "using": fallback_model})
    fallback_payload = _build_payload(fallback_kind, fallback_model, messages)
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
        msg = f"Upstream LLM unavailable (primary status={primary_error.status if primary_error else None}, fallback status={fallback_error.status})"
        raise LLMUpstreamError(
            provider="fallback",
            status=fallback_error.status,
            message=msg,
            body_snippet=fallback_error.body_snippet,
        )


async def health_check() -> Dict[str, Any]:
    timeout = httpx.Timeout(connect=2.0, read=3.0, write=3.0, pool=3.0)
    verify_flag = settings.LLM_TLS_VERIFY
    payload = _build_payload("same_as_primary", "health-check", [{"role": "user", "content": "ping"}])

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
        )
        primary_status = ok_dict(True, 200, None)
    except LLMUpstreamError as exc:
        primary_status = ok_dict(False, exc.status, repr(exc))

    fallback_status: Dict[str, Any] = ok_dict(False, None, "not configured")
    if settings.LLM_FALLBACK_BASE_URL:
        fallback_kind = (settings.LLM_FALLBACK_KIND or "same_as_primary").lower()
        fb_model = settings.LLM_FALLBACK_MODEL or "health-check"
        fb_payload = _build_payload(fallback_kind, fb_model, [{"role": "user", "content": "ping"}])
        try:
            await _post_llm(
                provider="fallback",
                base=settings.LLM_FALLBACK_BASE_URL,
                path=settings.LLM_FALLBACK_PATH,
                payload=fb_payload,
                kind=fallback_kind,
                timeout=timeout,
                verify=verify_flag,
            )
            fallback_status = ok_dict(True, 200, None)
        except LLMUpstreamError as exc:
            fallback_status = ok_dict(False, exc.status, repr(exc))

    return {"primary": primary_status, "fallback": fallback_status}
