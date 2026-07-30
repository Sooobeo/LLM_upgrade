# llm upgrade: chat archiving

FastAPI, Supabase, Next.js로 구성된 대화 스레드 및 Gemini 브랜치 시각화 애플리케이션입니다.

## 로컬 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

다른 터미널에서:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

실제 비밀 값이 든 `.env`와 `frontend/.env.local`은 Git에 커밋하지 마세요.
`GEMINI_API_KEY`와 `SUPABASE_SERVICE_ROLE_KEY`는 서버 환경변수로만 설정하며
`NEXT_PUBLIC_` 접두사를 붙이면 안 됩니다.

Supabase 스키마와 RLS 정책은 배포 대상 프로젝트에 미리 적용되어 있어야 합니다.
배포 후 서로 다른 두 사용자로 상대방의 개인 스레드를 읽거나 수정할 수 없는지
반드시 확인하세요.

## 운영 배포 필수 설정

```env
APP_ENV=prod
CORS_ORIGINS=https://app.example.com
TRUSTED_HOSTS=api.example.com
ENABLE_PRODUCTION_API_DOCS=false
```

- 프론트와 API는 HTTPS로 제공해야 합니다.
- `CORS_ORIGINS`와 `TRUSTED_HOSTS`에는 실제 주소만 쉼표로 구분해 입력합니다.
- API 앞단 프록시에서도 요청 본문 크기 제한과 분산 rate limit을 설정하세요.
- refresh token은 백엔드의 HttpOnly 쿠키에만 저장됩니다.
- 운영 환경에서는 `/docs`, `/openapi.json`, `/_env_check`, debug 라우터가 비활성화됩니다.

## 검사

```powershell
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check

cd frontend
npm ci
npm run lint
npm run build
npm audit
```
