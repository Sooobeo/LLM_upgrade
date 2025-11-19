# app/services/llm.py
from __future__ import annotations
from typing import List, Dict, Literal, Optional

from app.core.config import settings

# --- 타입 정의 ---
Role = Literal["system", "user", "assistant"]
Provider = Literal["gpt", "gemini"]


# ====================================
# 1) OpenAI GPT (Chat Completions)
# ====================================
try:
    import openai

    if getattr(settings, "OPENAI_API_KEY", None):
        openai.api_key = settings.OPENAI_API_KEY
except ImportError:
    openai = None  # 설치 안 되어 있어도 서버가 죽지 않게


def call_gpt_chat(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
) -> str:
    """
    OpenAI Chat Completions 기반 GPT 호출.
    - messages: [{"role": "system"|"user"|"assistant", "content": "..."} ...]
    - model_name: 없으면 settings.OPENAI_DEFAULT_MODEL 사용
    """
    if openai is None:
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다.")

    model = model_name or getattr(settings, "OPENAI_DEFAULT_MODEL", "gpt-4.1-mini")

    resp = openai.chat.completions.create(
        model=model,
        messages=messages,
    )
    try:
        return resp.choices[0].message.content or ""
    except Exception:
        return ""


# ====================================
# 2) Google Gemini
# ====================================

try:
    import google.generativeai as genai

    if getattr(settings, "GEMINI_API_KEY", None):
        genai.configure(api_key=settings.GEMINI_API_KEY)
except ImportError:
    genai = None  # 설치 안 되어 있어도 서버가 죽지 않게


def call_gemini_chat(
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
) -> str:
    """
    Gemini 채팅 호출(단순 버전).
    - messages: [{"role": "system"|"user"|"assistant", "content": "..."} ...]
    Gemini 입력 포맷에 맞게 변환해서 호출 후, 텍스트만 반환.
    """
    if genai is None:
        raise RuntimeError("google-generativeai 패키지가 설치되어 있지 않습니다.")

    model = model_name or getattr(settings, "GEMINI_DEFAULT_MODEL", "gemini-1.5-flash")

    # Gemini용 contents 변환 (아주 단순 매핑)
    contents = []
    for m in messages:
        role = m["role"]
        text = m["content"]

        if role == "system":
            # system은 그냥 user로 보내되 [SYSTEM] 태그
            contents.append({"role": "user", "parts": [f"[SYSTEM] {text}"]})
        else:
            contents.append({"role": role, "parts": [text]})

    gm = genai.GenerativeModel(model)
    response = gm.generate_content(contents)

    try:
        return response.text or ""
    except Exception:
        return ""


# ====================================
# 3) 공통 디스패처
# ====================================

def call_llm_chat(
    provider: Provider,
    messages: List[Dict[str, str]],
    model_name: Optional[str] = None,
) -> str:
    """
    provider에 따라 GPT 또는 Gemini를 호출하는 공통 함수.
    - provider: "gpt" 또는 "gemini"
    - messages: [{"role": "system"|"user"|"assistant", "content": "..."} ...]
    """
    if provider == "gpt":
        return call_gpt_chat(messages=messages, model_name=model_name)
    elif provider == "gemini":
        return call_gemini_chat(messages=messages, model_name=model_name)
    else:
        raise ValueError(f"지원하지 않는 provider: {provider}")
