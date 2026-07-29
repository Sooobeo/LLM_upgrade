<<<<<<< HEAD
# LLM Upgrade

FastAPI + Supabase 백엔드와 Next.js 프론트엔드로 구성된 대화 기록 및
워크스페이스 애플리케이션입니다.

## 요구 환경

- Python 3.10 이상 (Python 3.13 확인 완료)
- Node.js 18.17 이상
- Supabase 프로젝트
- 선택 사항: LLM API 또는 로컬 Ollama

## 1. 백엔드 실행

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

`.env`의 `SUPABASE_URL`, `SUPABASE_ANON_KEY`를 실제 값으로 바꾼 뒤 실행합니다.
관리자 사용자 조회와 워크스페이스 멤버 기능을 사용하려면
`SUPABASE_SERVICE_ROLE_KEY`도 필요합니다.

```bash
python -m uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- LLM 상태: http://127.0.0.1:8000/health/llm

## 2. 프론트엔드 실행

별도 터미널에서:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

macOS/Linux에서는 `cp .env.example .env.local`을 사용합니다.

프론트엔드는 기본적으로 http://localhost:3000, 백엔드는
http://127.0.0.1:8000을 사용합니다.

## 검사 명령

```powershell
# 저장소 루트
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\python.exe -m pip check

# frontend 폴더
npm run lint
npm run build
```

실제 비밀 키가 든 `.env`와 `frontend/.env.local`은 Git에 커밋하지 마세요.

## Google Gemini 모델

Gemini를 사용하려면 저장소 루트의 `.env`에 서버용 API 키를 설정합니다.

```env
GEMINI_API_KEY=your-google-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_2_5_COMPAT_MODEL=gemini-3.6-flash
```

API 키에는 `NEXT_PUBLIC_` 접두사를 붙이지 마세요. 프론트엔드 번들에 키가
노출됩니다. 설정 후 백엔드를 재시작하면 새 스레드와 기존 채팅의 모델
선택 목록에는 `gemini-2.5-flash`가 표시됩니다. Google은 신규 API 키에
2.5 Flash 제공을 종료했으므로 실제 요청은 `GEMINI_2_5_COMPAT_MODEL`에
설정된 최신 호환 모델로 실행됩니다.
=======

>>>>>>> ababa4b71edbbbfde7706f291ec75b693c092180
