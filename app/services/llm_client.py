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
    ):
        super().__init__(message)
        self.provider = provider
        self.status = status
        self.body_snippet = body_snippet

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
    if kind == "ollama":
        return {"model": model, "messages": messages, "stream": False}
    # same_as_primary and openai_compatible use the same shape for now
    return {"model": model, "messages": messages, "stream": False}


def _extract_assistant(kind: str, data: Dict[str, Any]) -> str:
    if kind == "ollama":
        msg = data.get("message") or {}
        return msg.get("content") or data.get("content") or data.get("assistant") or ""
    # default extraction
    return (
        data.get("assistant_content")
        or data.get("content")
        or data.get("assistant")
        or data.get("message")
        or ""
    )


def _should_fallback(exc: LLMUpstreamError) -> bool:
    return exc.status in {502, 503, 504} or exc.status is None


async def _post_llm(provider: str, base: str, path: str, payload: Dict[str, Any], kind: str, timeout: httpx.Timeout, verify: bool) -> str:
    url = _build_url(base, path)
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
            resp = await client.post(url, json=payload)
        status = resp.status_code
        text = resp.text or ""
        if status >= 400:
            snippet = text[:200]
            logger.warning(
                "LLM provider error",
                extra={"provider": provider, "url": url, "status": status, "body_snippet": snippet},
            )
            msg = f"status={status}"
            if kind == "ollama" and status == 404:
                msg = "Fallback Ollama model not available. Run: ollama pull <model>"
            raise LLMUpstreamError(provider=provider, status=status, message=msg, body_snippet=snippet)
        try:
            data = resp.json()
        except Exception as exc:  # pragma: no cover - defensive
            raise LLMUpstreamError(provider=provider, status=status, message=f"invalid json: {exc}", body_snippet=text[:200])
        assistant = _extract_assistant(kind, data)
        if not assistant:
            raise LLMUpstreamError(provider=provider, status=status, message="empty assistant_content", body_snippet=str(data)[:300])
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
        connect=5.0,
        read=float(settings.LLM_REQUEST_TIMEOUT_SECS),
        write=float(settings.LLM_REQUEST_TIMEOUT_SECS),
        pool=5.0,
    )
    verify_flag = settings.LLM_TLS_VERIFY

    primary_payload = _build_payload("same_as_primary", model, messages)
    primary_error: LLMUpstreamError | None = None

    try:
        return await _post_llm(
            provider="primary",
            base=settings.LLM_PRIMARY_BASE_URL,
            path=settings.LLM_PRIMARY_PATH,
            payload=primary_payload,
            kind="same_as_primary",
            timeout=timeout,
            verify=verify_flag,
        )
    except LLMUpstreamError as exc:
        primary_error = exc

    # Fallback
    if not _should_fallback(primary_error) or not settings.LLM_FALLBACK_BASE_URL:
        raise primary_error  # type: ignore

    fallback_kind = (settings.LLM_FALLBACK_KIND or "same_as_primary").lower()
    fallback_model = settings.LLM_FALLBACK_MODEL or model
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
