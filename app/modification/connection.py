#connection.py

import os
import sys
from functools import lru_cache
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv
import openai
from google import genai
from google.genai import types

#environment file containing login credential
env = ".env"

loaded_any = False

load_dotenv(dotenv_path=env, override=False)
print(f"[dotenv] loaded: {env}")
loaded_any = True

if loaded_any == 0:
    print(".env loading error")

def _get_url_and_key():
    #supabase key and secret parse
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") #for dev, use SUPABASE_ANON_KEY for publishing
    )
    return url, key

class ConfigError(RuntimeError):
    pass

#chacheing
@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url, key = _get_url_and_key()
    print(f"URL : {url}  \n KEY : {len(key)*"*"}")
    
    if not url:
        raise ConfigError("url is missing")
    elif not key:
        raise ConfigError("url parsed, but key is missing")
    
    return create_client(url, key)

"""
TBD

def model_ChatGPT(model_GPT, instruction, input_content):
    
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": input_content}
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
    #whenfirst used to generate the chat
    if init:
        response = client.models.generate_content(
        model= model_gemini,
        config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_budget=thinking_effort) #-1(auto) 0(no reasoning)~24576(flash) 128~32768(pro)
            ),
        thinking_config=types.ThinkingConfig(include_thoughts=think_config #True or False
            ),
        contents=input,
        )
    #when user want to continue the chatting.
    else:
        chat = client.chats.create(model=model_gemini)
        response = chat.send_message_stream(input)

    return response

"""