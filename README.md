# 농업 다마고치 게임 🌱

귀농 청년을 위한 농업 다마고치 게임입니다. 감자, 오이, 토마토, 당근, 부추 등 작물을 선택하여 키우는 게임입니다.

## 🚀 빠른 시작

### 1. 환경 변수 설정

프로젝트 루트의 `fastapi_backend/.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=chatbot_db
```

### 2. MongoDB 실행

**Windows (PowerShell - 관리자 권한):**
```powershell
mongod
```

**macOS/Linux:**
```bash
mongod
```

또는 MongoDB를 서비스로 설치한 경우 자동으로 실행됩니다.

### 3. Python 가상환경 설정

```powershell
# 가상환경 생성 (처음 한 번만)
python -m venv .venv

# 가상환경 활성화 (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 가상환경 활성화 (Windows CMD)
.venv\Scripts\activate.bat

# 가상환경 활성화 (macOS/Linux)
source .venv/bin/activate
```

**PowerShell 실행 정책 오류 시:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### 4. 의존성 설치

```bash
pip install -r requirements.txt
```

### 5. FastAPI 서버 실행

프로젝트 루트 디렉토리에서 실행:

```bash
python -m uvicorn fastapi_backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

또는 더 간단하게:

```bash
cd fastapi_backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**서버가 실행되면:**
- API 서버: http://127.0.0.1:8000
- API 문서 (Swagger UI): http://127.0.0.1:8000/docs
- 대체 API 문서 (ReDoc): http://127.0.0.1:8000/redoc

### 6. 프론트엔드 실행

프론트엔드는 정적 파일이므로 웹 서버로 실행하거나 직접 HTML 파일을 열면 됩니다.

**Python 내장 서버 (권장):**
```bash
# client 폴더에서
cd client
python -m http.server 3000
```

또는 프로젝트 루트에서:
```bash
python -m http.server 3000 --directory client
```

**프론트엔드 접속:**
- http://127.0.0.1:3000/login.html

## 📝 전체 실행 순서 요약

```powershell
# 1. MongoDB 실행 (별도 터미널, 관리자 권한)
mongod

# 2. 가상환경 활성화
.\.venv\Scripts\Activate.ps1

# 3. FastAPI 서버 실행
python -m uvicorn fastapi_backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 4. 프론트엔드 서버 실행 (별도 터미널)
cd client
python -m http.server 3000
```

## 🔧 기술 스택

### 백엔드
- **FastAPI**: REST API 서버
- **MongoDB**: 데이터베이스
- **LangChain + OpenAI**: AI 챗봇
- **Uvicorn**: ASGI 서버

### 프론트엔드
- 순수 HTML/CSS/JavaScript
- SessionStorage 기반 상태 관리

## 📁 프로젝트 구조

```
wemeet_jbnu/
├── client/                 # 프론트엔드
│   ├── login.html         # 로그인 페이지
│   ├── recommend.html     # 다마고치 선택 화면
│   ├── main.html          # 메인 게임 화면
│   └── ...
├── fastapi_backend/       # 백엔드
│   ├── app/
│   │   ├── main.py        # FastAPI 메인 앱
│   │   ├── recommendation.py  # 작물 추천 서비스
│   │   └── data/
│   │       └── 작물들.txt  # 작물 데이터
│   └── .env               # 환경 변수 (생성 필요)
├── requirements.txt       # Python 의존성
└── README.md
```

## 🌾 지원 작물

현재 선택 가능한 작물:
- 🥔 감자 (난이도: 하)
- 🥒 오이 (난이도: 상)
- 🍅 토마토 (난이도: 중)
- 🥕 당근 (난이도: 중)
- 🌿 부추 (난이도: 하)

## 🔑 기본 테스트 계정

```
아이디: nongbi
비밀번호: 1234
```

## 🐛 문제 해결

### MongoDB 연결 오류
- MongoDB가 실행 중인지 확인
- `MONGO_URI` 환경 변수가 올바른지 확인

### OpenAI API 키 오류
- `.env` 파일에 `OPENAI_API_KEY`가 설정되어 있는지 확인
- API 키가 유효한지 확인

### 포트 이미 사용 중
- 8000번 포트가 사용 중이면 다른 포트 지정:
```bash
python -m uvicorn fastapi_backend.app.main:app --reload --port 8001
```

### CORS 오류
- FastAPI CORS 설정이 `allow_origins=["*"]`로 되어 있어 문제없어야 합니다.
- 프론트엔드에서 API_BASE_URL이 올바르게 설정되어 있는지 확인

## 📚 API 엔드포인트

- `GET /health` - 서버 상태 확인
- `POST /auth/login` - 로그인
- `POST /profile` - 프로필 저장
- `GET /profile/{user_id}` - 프로필 조회
- `POST /chat` - 챗봇 대화
- `POST /recommendations` - 작물 추천

자세한 API 문서는 http://127.0.0.1:8000/docs 에서 확인할 수 있습니다.

## 📄 라이선스

MIT License

