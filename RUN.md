# 🚀 빠른 실행 가이드

## Windows PowerShell 실행 방법

### 1단계: MongoDB 실행
```powershell
# 관리자 권한으로 PowerShell 실행 후
mongod
```

### 2단계: FastAPI 서버 실행
```powershell
# 프로젝트 루트에서
.\.venv\Scripts\Activate.ps1
python -m uvicorn fastapi_backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3단계: 프론트엔드 실행 (선택)
```powershell
# 새 터미널에서
cd client
python -m http.server 3000
```

## 주요 명령어

### 가상환경 활성화
```powershell
.\.venv\Scripts\Activate.ps1
```

### 가상환경 비활성화
```powershell
deactivate
```

### 서버 실행 (포트 8000)
```bash
python -m uvicorn fastapi_backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 서버 실행 (포트 변경)
```bash
python -m uvicorn fastapi_backend.app.main:app --reload --host 0.0.0.0 --port 8001
```

## 접속 주소

- **API 서버**: http://127.0.0.1:8000
- **API 문서**: http://127.0.0.1:8000/docs
- **프론트엔드**: http://127.0.0.1:3000/login.html (HTTP 서버 실행 시)

## 환경 변수 설정

`fastapi_backend/.env` 파일 생성:
```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=chatbot_db
```

