# app/main.py
from fastapi import FastAPI, HTTPException
import os, httpx

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/auth/google/exchange-id-token")
async def exchange_id_token(payload: dict):
    # 기대 바디: { provider, id_token, client_id, (nonce?) }
    required = ["provider", "id_token", "client_id"]
    if any(k not in payload for k in required):
        raise HTTPException(status_code=400, detail={"error":"missing fields","got":list(payload.keys())})

    SUPABASE_URL = os.environ.get("SUPABASE_URL")    # e.g. https://<project>.supabase.co
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise HTTPException(status_code=500, detail="missing env SUPABASE_URL / SUPABASE_ANON_KEY")

    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=id_token"
    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, json=payload)

    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=data)

    return data
