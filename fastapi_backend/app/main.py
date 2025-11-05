# app/main.py
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv
from pymongo import MongoClient

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# -----------------------
# 0. 환경변수 로드
# -----------------------
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "chatbot_db")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY 가 .env 에 설정되지 않았습니다.")


# -----------------------
# 1. FastAPI 앱 생성
# -----------------------
app = FastAPI(title="귀농 청년 맞춤 챗봇 (FastAPI + MongoDB + Gemini)")

# CORS (나중에 프론트엔드 연동을 위해 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계에서는 * 허용, 운영 시 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------
# 2. MongoDB 연결
# -----------------------
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB_NAME]
profiles_collection = db["profiles"]  # user 프로필 저장 컬렉션


# -----------------------
# 3. LangChain + Gemini 설정
# -----------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",  # 필요하면 gemini-1.5-flash 등으로 변경 가능
    google_api_key=GEMINI_API_KEY,
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
- 너무 긴 답변 대신 핵심 위주로 설명하고,
  필요하다면 다음에 무엇을 물어보면 좋을지 한 가지 정도만 제안합니다.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_template),
        ("human", "{user_message}"),
    ]
)


# -----------------------
# 4. Pydantic 모델 정의
# -----------------------
class Profile(BaseModel):
    userId: str
    region: Optional[str] = None
    land_area: Optional[str] = None
    capital: Optional[str] = None
    experience: Optional[str] = None


class ChatRequest(BaseModel):
    userId: str
    message: str


class ChatResponse(BaseModel):
    answer: str


# -----------------------
# 5. 헬스 체크
# -----------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -----------------------
# 6. 프로필 저장 / 업데이트
# -----------------------
@app.post("/profile")
def save_profile(profile: Profile):
    """
    userId 기준으로 프로필을 upsert(있으면 업데이트, 없으면 생성)합니다.
    """
    profiles_collection.update_one(
        {"userId": profile.userId},
        {"$set": profile.dict()},
        upsert=True,
    )
    stored = profiles_collection.find_one({"userId": profile.userId}, {"_id": False})
    return {"ok": True, "profile": stored}


# -----------------------
# 7. 프로필 기반 챗봇 대화
# -----------------------
def profile_to_hint(profile_doc: Optional[dict]) -> str:
    """
    MongoDB에서 가져온 프로필 문서를 한 줄 설명으로 변환
    """
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

    if not parts:
        return "등록된 프로필이 있으나, 상세 정보가 비어 있습니다."
    return ", ".join(parts)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    1) userId로 MongoDB에서 프로필 조회
    2) 프로필을 LangChain 프롬프트에 주입
    3) Gemini 모델로 대답 생성
    """
    # 1) 프로필 조회
    profile_doc = profiles_collection.find_one({"userId": req.userId}, {"_id": False})
    profile_hint = profile_to_hint(profile_doc)

    # 2) LangChain Expression Language 체인 실행
    chain = prompt | llm
    result = chain.invoke(
        {
            "profile_hint": profile_hint,
            "user_message": req.message,
        }
    )

    # result 는 보통 AIMessage 객체
    answer_text = getattr(result, "content", str(result))

    return ChatResponse(answer=answer_text)
