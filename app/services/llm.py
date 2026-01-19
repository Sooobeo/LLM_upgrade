from __future__ import annotations

from typing import Any, Iterable, Optional

import requests

from app.core.config import settings


class LLMError(Exception):
    """LLM 호출 실패(네트워크/타임아웃/응답형식 오류 등)를 통일적으로 표현."""


def build_ollama_generate_prompt(
    messages: Iterable[dict[str, Any]],
) -> str:
    """
    thread messages를 Ollama /api/generate 의 prompt로 직렬화.

    기대 메시지 형태 예:
      {"role": "user" | "assistant", "content": "..."}  (그 외 키는 무시)
    """
    lines: list[str] = []
    for m in messages:
        role = (m.get("role") or "").strip().lower()
        content = (m.get("content") or "").strip()
        if not content:
            continue

        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
        else:
            # 알 수 없는 role은 user로 취급하거나 스킵할 수 있음.
            # 여기서는 스킵하지 않고 user로 처리.
            lines.append(f"User: {content}")

    # 모델이 이어서 답하도록 마지막에 Assistant: 프롬프트를 둔다
    if not lines or not lines[-1].startswith("Assistant:"):
        lines.append("Assistant:")

    return "\n".join(lines)


def call_generate(
    *,
    messages: Iterable[dict[str, Any]],
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout_sec: Optional[int] = None,
) -> str:
    """
    Ollama 호환 /api/generate 호출.
    - stream=false로 단일 JSON 응답을 받는다.
    - 응답 JSON의 'response' 필드를 텍스트로 반환한다.
    """
    _base = (base_url or settings.LLM_BASE_URL).rstrip("/")
    _model = model or settings.LLM_MODEL
    _timeout = timeout_sec or settings.LLM_TIMEOUT_SEC

    url = f"{_base}/api/generate"
    prompt = build_ollama_generate_prompt(messages)

    payload = {
        "model": _model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=_timeout)
    except requests.RequestException as e:
        raise LLMError(f"LLM request failed: {e}") from e

    if resp.status_code >= 400:
        # 가능하면 서버가 준 에러 메시지도 포함
        detail = resp.text[:500] if resp.text else ""
        raise LLMError(f"LLM error: HTTP {resp.status_code} {detail}")

    try:
        data = resp.json()
    except ValueError as e:
        raise LLMError(f"LLM returned non-JSON response: {resp.text[:500]}") from e

    # Ollama /api/generate의 핵심 결과 필드
    answer = (data.get("response") or "").strip()
    if not answer:
        raise LLMError(f"LLM response missing 'response' field: {data}")

    return answer
