import os
from functools import lru_cache
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv
# import openai
# from google import genai
# from google.genai import types


# -----------------------------
# 🔹 .env 파일 자동 로드
# -----------------------------
env_path = find_dotenv()
if env_path:
    load_dotenv(dotenv_path=env_path, override=False)
    print(f"[dotenv] loaded: {env_path}")
else:
    print("[dotenv] .env file not found!")


# -----------------------------
# 🔹 Supabase URL & Key 가져오기
# -----------------------------
def _get_url_and_key():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # for dev, use ANON_KEY for publishing
    return url, key


# -----------------------------
# 🔹 예외 클래스 정의
# -----------------------------
class ConfigError(RuntimeError):
    pass


# -----------------------------
# 🔹 Supabase 클라이언트 생성 (캐싱)
# -----------------------------
@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url, key = _get_url_and_key()

    key_mask = "*" * len(key or "")
    print(f"URL : {url}\nKEY : {key_mask}")

    if not url:
        raise ConfigError("SUPABASE_URL is missing")
    if not key:
        raise ConfigError("SUPABASE_SERVICE_ROLE_KEY is missing")

    return create_client(url, key)


# -----------------------------
# (Optional) 향후 확장용: OpenAI / Gemini 함수
# -----------------------------
"""
def model_ChatGPT(model_GPT, instruction, input_content):
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": input_content},
    ]
    try:
        response = openai.chat.completions.create(
            model=model_GPT,
            messages=messages
        )
        return response
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None


def model_Gemini(init, model_gemini, thinking_effort, think_config, input):
    client = genai.Client()

    if init:
        response = client.models.generate_content(
            model=model_gemini,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_budget=thinking_effort
                ),
                include_thoughts=think_config,
            ),
            contents=input,
        )
    else:
        chat = client.chats.create(model=model_gemini)
        response = chat.send_message_stream(input)

    return response
"""
