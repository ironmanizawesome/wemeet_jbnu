# app/main.py
import os
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .recommendation import CropRecommendationService


# =========================================================
# 0. 환경변수 로드 (.env 파일을 fastapi_backend 경로에서 찾기)
# =========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # fastapi_backend
env_path = os.path.join(BASE_DIR, ".env")

if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
    print(f"✅ .env 파일 로드 완료: {env_path}")
else:
    print(f"⚠️ .env 파일을 찾을 수 없습니다: {env_path}")

# =========================================================
# 1. 환경 변수 읽기
# =========================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "chatbot_db")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 가 .env 에 설정되지 않았습니다.")

print("🔑 OPENAI_API_KEY:", OPENAI_API_KEY[:12] + "..." if OPENAI_API_KEY else None)

# =========================================================
# 2. FastAPI 앱 생성
# =========================================================
app = FastAPI(title="귀농 청년 맞춤 챗봇 (FastAPI + MongoDB + LangChain)")

# CORS 설정 (React 프론트엔드 연동 대비)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계에서는 전체 허용, 운영 시 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 3. MongoDB 연결
# =========================================================
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
profiles_collection = db["profiles"]
users_collection = db["users"]
diaries_collection = db["diaries"]

# 초기 사용자 데이터 설정 (이미 있으면 건너뜀)
if users_collection.count_documents({"username": "nongbi"}) == 0:
    users_collection.insert_one({
        "username": "nongbi",
        "password": "1234",  # 실제 운영 환경에서는 해시화 필요
        "email": "nongbi@example.com"
    })
    print("✅ 초기 사용자 데이터 생성 완료 (nongbi/1234)")

# =========================================================
# 4. LangChain 설정
# =========================================================
llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model=OPENAI_MODEL,
    temperature=0.3,  # 답변 안정성 중심
)

system_template = """
당신은 '귀농 청년 맞춤 에이전트'입니다.
항상 존댓말을 사용합니다.
사용자의 귀농/농업 관련 상황(지역, 토지 규모, 자본금, 경험)을 고려해서,
현실적이고 신중한 조언을 제공합니다.

사용자 프로필 정보:
{profile_hint}

규칙:
- 모르는 정보는 아는 척하지 말고, 추가 확인이 필요하다고 말합니다.
- 너무 긴 답변 대신 핵심 위주로 설명하고, 필요하다면 다음에 무엇을 물어보면 좋을지 한 가지 정도만 제안합니다.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_template),
        ("human", "{user_message}"),
    ]
)

feedback_system_template = """
당신은 농가 운영을 코칭하는 'AI 농사 코치'입니다.
항상 존댓말을 쓰고, 복잡한 전문 용어는 설명을 덧붙입니다.
사용자가 작성한 농사 일지와 할 일 목록을 검토하여
1) 칭찬할 점, 2) 주의/개선 사항, 3) 다음 행동 제안을 간결하게 제공합니다.

사용자 프로필(선택):
{profile_hint}

오늘 농사 일지:
{diary}

할 일 목록/상태:
{todo_hint}

사용자 추가 요청:
{question}

규칙:
- 일지에 없는 내용은 추측하지 않습니다.
- 실행 가능한 조언을 2~3개 제안합니다.
- 필요한 경우 체크리스트나 우선순위를 제공합니다.
"""

feedback_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", feedback_system_template),
    ]
)

# =========================================================
# 5. Pydantic 모델 정의
# =========================================================
class Profile(BaseModel):
    userId: str
    region: Optional[str] = None
    region_detail: Optional[str] = None
    land_size: Optional[float] = None
    land_unit: Optional[str] = None
    land_area: Optional[str] = None
    workforce: Optional[int] = None
    capital_amount: Optional[float] = None
    capital_unit: Optional[str] = None
    capital: Optional[str] = None
    age: Optional[int] = None
    experience: Optional[str] = None
    experience_years: Optional[float] = None
    has_cert: Optional[bool] = None
    crops: Optional[List[str]] = None


class ChatRequest(BaseModel):
    userId: str
    message: str


class ChatResponse(BaseModel):
    answer: str


class Crop(BaseModel):
    name: str
    season: Optional[str] = None
    purpose: Optional[str] = None
    level: Optional[str] = None
    environment: Optional[str] = None


class RecommendationRequest(BaseModel):
    season: Optional[str] = None
    level: Optional[str] = None
    sunlight: Optional[str] = None


class RecommendationResponse(BaseModel):
    results: List[Crop]


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None
    email: Optional[str] = None


class TodoItem(BaseModel):
    text: str
    checked: bool = False


class FeedbackRequest(BaseModel):
    userId: Optional[str] = None
    diary: str
    todos: Optional[List[TodoItem]] = None
    question: Optional[str] = None


class FeedbackResponse(BaseModel):
    feedback: str


class DiaryRequest(BaseModel):
    userId: str
    content: str
    date: Optional[str] = None
    todos: Optional[List[TodoItem]] = None
    photo_url: Optional[str] = None


class DiaryEntryResponse(BaseModel):
    id: str
    userId: str
    content: str
    date: Optional[str] = None
    todos: List[TodoItem] = []
    photo_url: Optional[str] = None
    created_at: str
    updated_at: str


class DiaryListResponse(BaseModel):
    diaries: List[DiaryEntryResponse]


def serialize_diary(doc: dict) -> DiaryEntryResponse:
    return DiaryEntryResponse(
        id=str(doc["_id"]),
        userId=doc["userId"],
        content=doc.get("content", ""),
        date=doc.get("date"),
        todos=[TodoItem(**item) if isinstance(item, dict) else TodoItem(text=str(item)) for item in doc.get("todos", [])],
        photo_url=doc.get("photo_url"),
        created_at=doc["created_at"].isoformat(),
        updated_at=doc["updated_at"].isoformat(),
    )

# =========================================================
# 6. 헬스 체크 API
# =========================================================
@app.get("/health")
def health():
    return {"status": "ok"}

# =========================================================
# 6-1. 로그인 API
# =========================================================
@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    # 사용자 조회
    user = users_collection.find_one({"username": req.username}, {"_id": False})
    
    if not user:
        return LoginResponse(
            success=False,
            message="아이디 또는 비밀번호가 올바르지 않습니다."
        )
    
    # 비밀번호 확인 (실제 운영 환경에서는 해시 비교 필요)
    if user.get("password") != req.password:
        return LoginResponse(
            success=False,
            message="아이디 또는 비밀번호가 올바르지 않습니다."
        )
    
    # 로그인 성공
    return LoginResponse(
        success=True,
        message="로그인 성공",
        username=user.get("username"),
        email=user.get("email")
    )

# =========================================================
# 7. 프로필 저장 / 업데이트
# =========================================================
def build_profile_payload(profile: Profile) -> dict:
    payload = profile.dict()

    if payload.get("land_size") is not None:
        unit = payload.get("land_unit") or ""
        payload["land_area"] = f"{payload['land_size']} {unit}".strip()

    if payload.get("capital_amount") is not None:
        unit = payload.get("capital_unit") or ""
        payload["capital"] = f"{payload['capital_amount']} {unit}".strip()

    if payload.get("crops") is None:
        payload["crops"] = []

    if payload.get("has_cert") is not None:
        payload["has_cert"] = bool(payload["has_cert"])

    return payload


@app.get("/profile/{user_id}")
def get_profile(user_id: str):
    stored = profiles_collection.find_one({"userId": user_id}, {"_id": False})
    return {"ok": bool(stored), "profile": stored}


@app.post("/profile")
def save_profile(profile: Profile):
    payload = build_profile_payload(profile)
    profiles_collection.update_one(
        {"userId": profile.userId},
        {"$set": payload},
        upsert=True,
    )
    stored = profiles_collection.find_one({"userId": profile.userId}, {"_id": False})
    return {"ok": True, "profile": stored}

# =========================================================
# 8. 프로필 기반 챗봇 대화
# =========================================================
def profile_to_hint(profile_doc: Optional[dict]) -> str:
    if not profile_doc:
        return "등록된 프로필이 없습니다. (지역/토지규모/자본금/경험 정보 없음)"

    parts = []
    if profile_doc.get("region"):
        parts.append(f"지역={profile_doc['region']}")
    if profile_doc.get("land_area"):
        parts.append(f"토지규모={profile_doc['land_area']}")
    if profile_doc.get("capital"):
        parts.append(f"자본금={profile_doc['capital']}")
    if profile_doc.get("experience"):
        parts.append(f"경험={profile_doc['experience']}")

    return ", ".join(parts) if parts else "등록된 프로필이 있으나, 상세 정보가 비어 있습니다."


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    profile_doc = profiles_collection.find_one({"userId": req.userId}, {"_id": False})
    profile_hint = profile_to_hint(profile_doc)

    chain = prompt | llm
    result = chain.invoke(
        {
            "profile_hint": profile_hint,
            "user_message": req.message,
        }
    )

    answer_text = result.content if hasattr(result, "content") else str(result)
    return ChatResponse(answer=answer_text)


# =========================================================
# 9. 농사 일지 AI 피드백
# =========================================================
@app.post("/feedback", response_model=FeedbackResponse)
def create_feedback(payload: FeedbackRequest):
    diary = (payload.diary or "").strip()
    if not diary:
        raise HTTPException(status_code=400, detail="농사 일지 내용이 필요합니다.")

    profile_doc = None
    profile_hint = "등록된 프로필이 없습니다."
    if payload.userId:
        profile_doc = profiles_collection.find_one({"userId": payload.userId}, {"_id": False})
        profile_hint = profile_to_hint(profile_doc)

    todos = payload.todos or []
    if todos:
        todo_hint_parts = []
        for item in todos:
            status = "[완료]" if item.checked else "[진행중]"
            todo_hint_parts.append(f"{status} {item.text}")
        todo_hint = "\n".join(f"- {text}" for text in todo_hint_parts)
    else:
        todo_hint = "등록된 할 일 정보 없음"

    question = payload.question.strip() if payload.question else "일지 전반에 대한 코칭을 제공해주세요."

    chain = feedback_prompt | llm
    result = chain.invoke(
        {
            "profile_hint": profile_hint,
            "diary": diary,
            "todo_hint": todo_hint,
            "question": question,
        }
    )
    advice = result.content if hasattr(result, "content") else str(result)
    return FeedbackResponse(feedback=advice)

# =========================================================
# 10. 농사 일지 저장 / 조회
# =========================================================
@app.post("/diaries", response_model=DiaryEntryResponse)
def create_diary(payload: DiaryRequest):
    if not payload.userId:
        raise HTTPException(status_code=400, detail="userId가 필요합니다.")

    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="농사 일지 내용이 비어 있습니다.")

    now = datetime.utcnow()
    doc = {
        "userId": payload.userId,
        "content": content,
        "date": payload.date or now.strftime("%Y-%m-%d"),
        "todos": [todo.dict() for todo in (payload.todos or [])],
        "photo_url": payload.photo_url,
        "created_at": now,
        "updated_at": now,
    }
    result = diaries_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_diary(doc)


@app.get("/diaries/{user_id}", response_model=DiaryListResponse)
def list_diaries(user_id: str):
    cursor = diaries_collection.find({"userId": user_id}).sort("created_at", -1)
    diaries = [serialize_diary(doc) for doc in cursor]
    return DiaryListResponse(diaries=diaries)

# =========================================================
# 11. 작물 추천
# =========================================================
recommendation_service = CropRecommendationService()


@app.post("/recommendations", response_model=RecommendationResponse)
def create_recommendations(payload: RecommendationRequest):
    matches = recommendation_service.recommend(
        season=payload.season,
        level=payload.level,
        sunlight=payload.sunlight,
    )
    return {"results": matches}
