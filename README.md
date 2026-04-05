# 🚀 LLM-Upgrade Backend

> Supabase 기반 인증 및 데이터 관리를 사용하는 **LLM-Upgrade FastAPI 서버**입니다.
> FastAPI, Pydantic, Supabase REST API를 활용해 인증, 스레드, 메시지 관리 기능을 제공합니다.

---

## 📦 프로젝트 개요

이 백엔드는 LLM-Upgrade 서비스의 핵심 API 서버입니다.

* 로그인 및 토큰 관리 (`/auth/...`)
* 스레드 및 메시지 관리 (`/threads/...`)
* 헬스체크 (`/health`)

---

## 🧩 기술 스택

| 구분        | 내용                          |
| --------- | --------------------------- |
| Framework | FastAPI                     |
| Database  | Supabase (PostgreSQL + RLS) |
| Language  | Python 3.10+                |
| Auth      | Supabase Auth (JWT 기반)      |
| Infra     | Docker / AWS EC2            |
| Docs      | Swagger UI (`/docs`)        |

---

## 📁 폴더 구조

```bash
app/
 ┣ db/                # Supabase 연결 및 인증 종속성
 ┃ ┣ deps.py          # access_token → current_user 변환
 ┃ ┗ supabase.py      # Supabase REST API 유틸
 ┣ repository/        # 비즈니스 로직 (DB 연동)
 ┃ ┣ auth.py          # 로그인, 토큰 교환, 로그아웃
 ┃ ┗ thread.py        # 스레드/메시지 CRUD
 ┣ routes/            # 라우팅 계층 (엔드포인트 정의)
 ┃ ┣ auth.py          # /auth/*
 ┃ ┣ thread.py        # /threads/*
 ┃ ┗ health.py        # /health
 ┣ schemas/           # Pydantic 스키마 정의
 ┃ ┣ auth.py          # 인증 관련 스키마
 ┃ ┗ thread.py        # 스레드/메시지 스키마
 ┗ main.py            # FastAPI 앱 진입점
```

---

## ⚙️ 환경 설정

루트에 `.env` 파일을 생성하고, 공유받은 값을 입력하세요.

---

## 🐍 가상환경 및 설치

```bash
# 가상환경 생성
python -m venv venv

# 활성화 (Windows)
source venv/Scripts/activate

# 활성화 (Mac/Linux)
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

---

## ▶️ 서버 실행

```bash
uvicorn app.main:app --reload
```

기본 실행 주소:
http://127.0.0.1:8000

---

## 🧾 API 문서

* Swagger UI: http://127.0.0.1:8000/docs
* ReDoc: http://127.0.0.1:8000/redoc

---

## 🧪 Postman 테스트

* Authorization → Bearer Token 설정
* 발급받은 access_token 입력
* `/auth/refresh`는 HttpOnly 쿠키 기반으로 동작

---

## 🤖 LLM 설정

### 환경 변수

* `LLM_PRIMARY_BASE_URL` (기본: https://llm.ycc.club)
* `LLM_PRIMARY_PATH` (기본: /api/generate)
* `LLM_FALLBACK_BASE_URL` (선택: http://127.0.0.1:11434)
* `LLM_FALLBACK_PATH` (기본: /api/generate 또는 /api/chat)
* `LLM_FALLBACK_KIND` (same_as_primary | ollama | openai_compatible)
* `LLM_REQUEST_TIMEOUT_SECS` (기본: 60)
* `LLM_TLS_VERIFY` (기본: True)

헬스체크:

```
GET /health/llm
```

---

## 🦙 Ollama 사용 방법

```bash
# 모델 다운로드
ollama pull llama3.1:8b

# 서버 실행
ollama serve
```

### 환경 변수 예시

```env
LLM_PRIMARY_BASE_URL=https://llm.ycc.club
LLM_PRIMARY_PATH=/api/generate
LLM_FALLBACK_KIND=ollama
LLM_FALLBACK_BASE_URL=http://127.0.0.1:11434
LLM_FALLBACK_PATH=/api/chat
LLM_FALLBACK_MODEL=llama3.1:8b
LLM_REQUEST_TIMEOUT_SECS=60
```

---

## ⚠️ 실행 전 주의사항

```bash
# FE 실행 전에 반드시 백엔드 먼저 실행
uvicorn app.main:app --reload
```
