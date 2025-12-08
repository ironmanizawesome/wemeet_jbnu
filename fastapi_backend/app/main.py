# app/main.py
import os
import re
import hashlib
import json
from typing import List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .recommendation import CropRecommendationService
from .game_service import get_crop_guide_for_game
from .crop_data_parser import (
    get_watering_frequency,
    get_fertilizing_period,
    get_growing_period,
    get_sickness_info,
    extract_temperature_from_text,
    extract_humidity_from_text
)


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
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
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
games_collection = db["games"]  # 게임 상태 저장
chat_responses_collection = db["chat_responses"]  # 챗봇 응답 캐시
crop_diary_collection = db["crop_diary"]  # 작물일기 저장
crop_collection_db = db["crop_collection"]  # 작물 도감 저장

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
    temperature=0.0,  # 최대 일관성을 위해 0으로 설정 (같은 입력에 항상 같은 출력)
    model_kwargs={"reasoning_effort": "low"},  # Fast 모드: 빠른 응답 우선 minimal low medium high중 고르기
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
- 같은 질문에는 항상 동일한 답변을 제공하여 일관성을 유지합니다.
- 답변은 명확하고 구체적이며, 항상 같은 형식과 구조를 유지합니다.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_template),
        ("human", "{user_message}"),
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


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class RegisterResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None


# =========================================================
# 게임 관련 모델
# =========================================================
class GameActionRequest(BaseModel):
    userId: str
    cropName: str
    actionType: str  # "water", "fertilizer", "pesticide"
    day: int
    currentHp: int
    actions: List[dict]
    previousActions: Optional[List[dict]] = None
    currentWeather: Optional[str] = None  # 현재 날씨 정보


class GameEvaluateResponse(BaseModel):
    newHp: int
    hpChange: int
    feedback: str
    speechBubble: Optional[str] = None  # 말풍선 대사 추가


class GameStateRequest(BaseModel):
    userId: str
    state: dict


class HarvestFeedbackRequest(BaseModel):
    userId: str
    cropName: str
    finalHp: int
    totalDays: int
    actions: List[dict]


class HarvestFeedbackResponse(BaseModel):
    message: str
    success: bool

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
# 6-2. 회원가입 API
# =========================================================
@app.post("/auth/register", response_model=RegisterResponse)
def register(req: RegisterRequest):
    # 유효성 검사
    if not req.username or len(req.username) < 2:
        return RegisterResponse(
            success=False,
            message="아이디는 2자 이상이어야 합니다."
        )
    
    if not req.password or len(req.password) < 4:
        return RegisterResponse(
            success=False,
            message="비밀번호는 4자 이상이어야 합니다."
        )
    
    # 아이디 중복 체크
    existing_user = users_collection.find_one({"username": req.username})
    if existing_user:
        return RegisterResponse(
            success=False,
            message="이미 사용 중인 아이디입니다."
        )
    
    # 이메일 중복 체크 (이메일이 제공된 경우)
    if req.email:
        existing_email = users_collection.find_one({"email": req.email})
        if existing_email:
            return RegisterResponse(
                success=False,
                message="이미 사용 중인 이메일입니다."
            )
    
    # 새 사용자 생성
    new_user = {
        "username": req.username,
        "password": req.password,  # 실제 운영 환경에서는 해시화 필요
        "email": req.email or f"{req.username}@example.com",
        "createdAt": datetime.now().isoformat()
    }
    
    users_collection.insert_one(new_user)
    print(f"✅ 새 사용자 등록 완료: {req.username}")
    
    return RegisterResponse(
        success=True,
        message="회원가입이 완료되었습니다! 로그인해주세요.",
        username=req.username
    )


# =========================================================
# 6-3. 아이디 중복 체크 API
# =========================================================
@app.get("/auth/check-username/{username}")
def check_username(username: str):
    existing_user = users_collection.find_one({"username": username})
    return {
        "available": existing_user is None,
        "message": "사용 가능한 아이디입니다." if existing_user is None else "이미 사용 중인 아이디입니다."
    }

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


def generate_cache_key(user_message: str, profile_hint: str) -> str:
    """질문과 프로필 정보를 기반으로 캐시 키 생성"""
    # 질문과 프로필 정보를 정규화 (공백 제거, 소문자 변환 등)
    normalized_message = user_message.strip().lower()
    normalized_profile = profile_hint.strip().lower()
    
    # 캐시 키 생성
    cache_data = f"{normalized_message}|||{normalized_profile}"
    cache_key = hashlib.sha256(cache_data.encode('utf-8')).hexdigest()
    return cache_key


def get_cached_response(cache_key: str) -> Optional[str]:
    """캐시에서 응답 가져오기"""
    cached = chat_responses_collection.find_one({"cache_key": cache_key}, {"_id": False})
    if cached:
        return cached.get("answer")
    return None


def save_cached_response(cache_key: str, user_message: str, profile_hint: str, answer: str):
    """응답을 캐시에 저장"""
    from datetime import datetime
    chat_responses_collection.update_one(
        {"cache_key": cache_key},
        {
            "$set": {
                "cache_key": cache_key,
                "user_message": user_message,
                "profile_hint": profile_hint,
                "answer": answer,
                "created_at": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat()
            }
        },
        upsert=True
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    profile_doc = profiles_collection.find_one({"userId": req.userId}, {"_id": False})
    profile_hint = profile_to_hint(profile_doc)
    
    # 캐시 키 생성
    cache_key = generate_cache_key(req.message, profile_hint)
    
    # 캐시에서 응답 확인
    cached_answer = get_cached_response(cache_key)
    if cached_answer:
        # 캐시 히트: 마지막 사용 시간 업데이트
        from datetime import datetime
        chat_responses_collection.update_one(
            {"cache_key": cache_key},
            {"$set": {"last_used": datetime.now().isoformat()}}
        )
        print(f"✅ 캐시 히트: {cache_key[:16]}...")
        return ChatResponse(answer=cached_answer)
    
    # 캐시 미스: 새로운 응답 생성
    print(f"❌ 캐시 미스: {cache_key[:16]}... - 새로운 응답 생성 중")
    
    chain = prompt | llm
    result = chain.invoke(
        {
            "profile_hint": profile_hint,
            "user_message": req.message,
        }
    )

    answer_text = result.content if hasattr(result, "content") else str(result)
    
    # 응답을 캐시에 저장
    save_cached_response(cache_key, req.message, profile_hint, answer_text)
    
    return ChatResponse(answer=answer_text)


# =========================================================
# 챗봇 캐시 관리 API (선택적)
# =========================================================

@app.get("/chat/cache/stats")
def get_cache_stats():
    """캐시 통계 정보"""
    total_count = chat_responses_collection.count_documents({})
    return {
        "total_cached_responses": total_count,
        "collection": "chat_responses"
    }


@app.delete("/chat/cache/clear")
def clear_cache():
    """모든 캐시 삭제 (주의: 모든 저장된 응답이 삭제됩니다)"""
    result = chat_responses_collection.delete_many({})
    return {
        "deleted_count": result.deleted_count,
        "message": "캐시가 모두 삭제되었습니다."
    }


@app.delete("/chat/cache/{cache_key}")
def delete_cache_item(cache_key: str):
    """특정 캐시 항목 삭제"""
    result = chat_responses_collection.delete_one({"cache_key": cache_key})
    if result.deleted_count > 0:
        return {"message": f"캐시 항목이 삭제되었습니다. (key: {cache_key[:16]}...)"}
    return {"message": "해당 캐시 항목을 찾을 수 없습니다."}


# =========================================================
# 9. 작물 추천
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


# =========================================================
# 10. 작물 상세 정보 (환경 정보 포함)
# =========================================================
def get_crop_environment_data(crop_name: str) -> dict:
    """작물별 환경 정보 반환 (온도, 습도 등)"""
    # 작물별 일반적인 환경 정보 데이터
    env_data = {
        "당근": {
            "temperature": "15~25°C",
            "temperature_note": "생육 최적 온도: 15~25°C",
            "humidity": "60~80%",
            "humidity_note": "토양 수분 70~80% 유지 (생육 중기)",
            "sunlight": "충분한 일조",
            "sunlight_note": "광합성을 위해 충분한 햇빛 필요",
            "soil_temperature": "10~20°C",
            "soil_temperature_note": "파종 적정 지온: 10~20°C"
        },
        "옥수수": {
            "temperature": "20~30°C",
            "temperature_note": "생육 최적 온도: 20~30°C (서리에 약함)",
            "humidity": "50~70%",
            "humidity_note": "과습에 약함, 물 빠짐이 좋은 밭 필요",
            "sunlight": "매우 높음",
            "sunlight_note": "하루 종일 햇빛이 드는 곳",
            "soil_temperature": "15°C 이상",
            "soil_temperature_note": "늦서리 후 파종 (4월 중순~6월 중순)"
        },
        "고구마": {
            "temperature": "20~30°C",
            "temperature_note": "생육 최적 온도: 20~30°C",
            "humidity": "적당한 수분",
            "humidity_note": "물 빠짐이 생명, 과습에 약함",
            "sunlight": "매우 중요",
            "sunlight_note": "햇빛을 많이 받아야 땅속 고구마가 굵어짐",
            "soil_temperature": "15°C 이상",
            "soil_temperature_note": "늦서리 후 정식 (4월 말~6월 초)"
        },
        "토마토": {
            "temperature": "20~25°C (주간), 15~18°C (야간)",
            "temperature_note": "생육 최적 온도: 주간 20~25°C, 야간 15~18°C",
            "humidity": "60~70%",
            "humidity_note": "과습 시 병해 발생, 환기 중요",
            "sunlight": "매우 중요",
            "sunlight_note": "햇빛 부족 시 열매 맺힘 불량",
            "soil_temperature": "15°C 이상",
            "soil_temperature_note": "정식 적정 지온: 15°C 이상"
        },
        "오이": {
            "temperature": "25~30°C (주간), 18~20°C (야간)",
            "temperature_note": "생육 최적 온도: 주간 25~30°C, 야간 18~20°C",
            "humidity": "70~80%",
            "humidity_note": "습도 높을 시 노균병 주의, 환기 필수",
            "sunlight": "충분한 일조",
            "sunlight_note": "햇빛이 잘 들어야 덩굴 튼튼, 열매 잘 맺힘",
            "soil_temperature": "18°C 이상",
            "soil_temperature_note": "정식 적정 지온: 18°C 이상"
        },
        "감자": {
            "temperature": "15~20°C",
            "temperature_note": "생육 최적 온도: 15~20°C",
            "humidity": "적당한 수분",
            "humidity_note": "과습 시 역병 발생, 배수 중요",
            "sunlight": "충분한 일조",
            "sunlight_note": "햇빛이 잘 드는 곳에서 감자가 잘 여뭅니다",
            "soil_temperature": "5~10°C",
            "soil_temperature_note": "파종 적정 지온: 5~10°C (3월 중하순)"
        },
        "상추": {
            "temperature": "15~20°C",
            "temperature_note": "생육 최적 온도: 15~20°C",
            "humidity": "적당한 수분",
            "humidity_note": "흙이 마르면 물 주기",
            "sunlight": "양지 또는 반양지",
            "sunlight_note": "햇빛을 크게 가리지 않음",
            "soil_temperature": "10~15°C",
            "soil_temperature_note": "파종 적정 지온: 10~15°C (3월 말~4월)"
        },
        "부추": {
            "temperature": "15~25°C",
            "temperature_note": "생육 최적 온도: 15~25°C",
            "humidity": "충분한 수분",
            "humidity_note": "물을 좋아하는 작물, 건조 시 섬유질 증가",
            "sunlight": "양지 또는 반양지",
            "sunlight_note": "햇빛을 잘 가리지 않음",
            "soil_temperature": "10°C 이상",
            "soil_temperature_note": "파종 적정 지온: 10°C 이상 (3월 하순~4월 중순)"
        }
    }
    
    return env_data.get(crop_name, {
        "temperature": "정보 없음",
        "temperature_note": "해당 작물의 온도 정보가 없습니다",
        "humidity": "정보 없음",
        "humidity_note": "해당 작물의 습도 정보가 없습니다",
        "sunlight": "정보 없음",
        "sunlight_note": "해당 작물의 일조량 정보가 없습니다",
        "soil_temperature": "정보 없음",
        "soil_temperature_note": "해당 작물의 토양 온도 정보가 없습니다"
    })


@app.get("/crops/{crop_name}")
def get_crop_detail(crop_name: str):
    """작물 상세 정보 조회 (환경 정보 포함)"""
    crops = recommendation_service._crops
    crop = next((c for c in crops if c["name"] == crop_name), None)
    
    if not crop:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"작물 '{crop_name}'을 찾을 수 없습니다.")
    
    # 환경 정보 추가
    env_data = get_crop_environment_data(crop_name)
    
    # 수확 시기 정보 추가
    harvest_period = get_growing_period(crop_name)
    
    # 물주기 정보는 crop_info.txt에서 가져올 수 있지만, 여기서는 간단히 환경 정보만 반환
    result = {
        **crop,
        "environment_data": env_data,
        "watering": "작물별 물주기 정보는 상세 페이지에서 확인하세요.",
        "growing_period": harvest_period[1] if harvest_period else None,  # 최적 수확일 (하위 호환성)
        "harvest_period": harvest_period  # (최소 수확일, 최적 수확일)
    }
    
    return result


# =========================================================
# 10. 게임 관련 API
# =========================================================

# 게임 판단을 위한 시스템 프롬프트
game_system_template = """
당신은 {crop_name} 작물 캐릭터입니다. 사용자가 당신을 키우고 있어요!

작물 가이드라인:
{crop_guide}

사용자가 방금 한 행동:
- 행동 유형: {action_type}
- 현재 재배 일수: {day}일
- 현재 건강도: {current_hp}/100
- 최근 행동 이력: {recent_actions}

⚠️ 중요: 가이드라인에 포함된 "현재 날씨" 정보를 반드시 확인하세요! 날씨 정보는 행동 평가에 매우 중요합니다.
- 맑은 날씨: 물주기에 적합
- 비/눈/천둥 날씨: 물주기 시 과습 위험 (페널티)
- 흐린 날씨: 물주기 시 주의 필요

말풍선 대사 작성 시 날씨 정보를 언급할 때는 가이드라인에 명시된 "현재 날씨"를 정확히 사용하세요. 다른 날씨를 추측하거나 언급하지 마세요!

당신은 작물 캐릭터로서, 사용자의 행동에 대해 귀여운 말풍선 대사를 해주세요!

규칙:
1. 가이드라인에 맞는 행동이면 HP가 증가 (기본 +3~+5, HP가 낮을수록 더 큰 회복)
2. 가이드라인과 약간 다르면 HP 유지 또는 소폭 감소 (-1~-3)
3. 가이드라인과 많이 다르면 HP 감소 (-5~-10)
4. 과도한 행동(예: 하루에 여러 번 물주기)이면 HP 감소
5. 작물에 맞지 않는 행동이면 HP 감소
6. **중요**: 현재 HP가 낮을 때(50 이하) 좋은 행동을 하면 더 큰 회복을 주세요 (최대 +8까지 가능)
7. **중요**: 현재 HP가 매우 낮을 때(30 이하) 좋은 행동을 하면 최대한 큰 회복을 주세요 (최대 +10까지 가능)

말풍선 대사 작성 규칙:
- 작물 캐릭터의 입장에서 직접 말하는 형식으로 작성
- 귀여운 말투 사용 (예: "~해줘", "~했어요", "~면 좋겠어요")
- 좋은 행동이면: 감사 표현 + 기쁨 표현
- 나쁜 행동이면: 아쉬움 표현 + 어떻게 해줬으면 하는지 구체적인 조언
- 중간이면: 격려 표현 + 개선 제안
- **중요**: HP가 감소할 때는 구체적으로 무엇이 필요한지 명확히 전달하세요!
  * 물이 필요하면: "저 너무 목말라요... 물을 주시면 좋을 것 같아요! 💧"
  * 비료가 필요하면: "저 너무 배고파요... 비료를 주시면 더 잘 자랄 수 있을 거예요! 🌿"
  * 과습이면: "물이 너무 많아서 힘들어요... 조금만 주시면 좋을 것 같아요! 😢"
  * 방치되었으면: "관리가 필요해요... 물과 비료를 챙겨주시면 좋겠어요! 🌱"
- 1-2문장으로 간결하게 (말풍선에 들어갈 수 있도록)

⚠️ 문법 규칙 (반드시 지켜주세요!):
- 날씨 단어(맑음, 비, 눈, 흐림)와 관리 행동(물, 비료, 농약)을 혼동하지 마세요!
- "물"은 관수(물주기)를 의미합니다. "맑음"은 날씨입니다. 절대 섞지 마세요!
- "비료"는 영양분을 주는 것입니다. "비"는 날씨입니다. 절대 섞지 마세요!
- 올바른 예: "물을 주셔서", "비료를 주셔서", "맑은 날에", "비가 오는 날에"
- 잘못된 예: "맑음료", "맑음을 주셔서" (이런 표현은 절대 사용하지 마세요!)
- 비료 주기를 언급할 때: "비료를 X일 간격으로 주시면 좋겠어요"

응답 형식 (JSON):
{{
    "hp_change": 숫자 (-10 ~ +10, HP가 낮을 때는 더 큰 회복 가능),
    "feedback": "사용자에게 보여줄 평가 메시지 (간단하게)",
    "speech_bubble": "작물 캐릭터가 말풍선으로 할 귀여운 대사 (1-2문장, 어떻게 해줬으면 하는지 포함)"
}}

예시:
- 좋은 경우: 
  {{
    "hp_change": 3,
    "feedback": "적절한 물주기입니다! (+3)",
    "speech_bubble": "물을 제때 주셔서 너무 좋아요! 이렇게 계속 잘 챙겨주시면 더 건강해질 거예요! 💚"
  }}
- 나쁜 경우 (과습 - 비/눈 날씨에 물을 준 경우):
  {{
    "hp_change": -5,
    "feedback": "물을 너무 많이 주셨어요. (-5)",
    "speech_bubble": "흠... 물이 너무 많아서 뿌리가 숨을 못 쉬고 있어요. 비 오는 날에는 물을 주지 말아주세요! 맑은 날에만 주시면 더 좋을 것 같아요 🌱"
  }}
  ⚠️ 주의: 위 예시는 "비" 날씨에 물을 준 경우입니다. 실제 날씨가 "맑음"이면 "맑은 날에 물을 주시면 좋겠어요"라고 말해야 합니다!
- 나쁜 경우 (물 부족):
  {{
    "hp_change": -5,
    "feedback": "물을 주지 않아서 건강도가 감소했습니다. (-5)",
    "speech_bubble": "저 너무 목말라요... 물을 주시면 더 건강해질 수 있을 거예요! 맑은 날에 물을 주시면 좋겠어요 💧"
  }}
- 나쁜 경우 (비료 부족):
  {{
    "hp_change": -3,
    "feedback": "비료를 주지 않아서 건강도가 감소했습니다. (-3)",
    "speech_bubble": "저 너무 배고파요... 비료를 주시면 더 잘 자랄 수 있을 거예요! 영양분이 필요해요 🌿"
  }}
- 중간:
  {{
    "hp_change": 0,
    "feedback": "관리 중입니다. (0)",
    "speech_bubble": "괜찮아요! 조금만 더 날씨를 보고 물을 주시면 더 건강해질 수 있을 거예요. 맑은 날에 물을 주시는 게 좋아요! ☀️"
  }}
"""

game_prompt = ChatPromptTemplate.from_messages([
    ("system", game_system_template),
    ("human", "이 행동을 평가해주세요.")
])


class GameActionRequest(BaseModel):
    userId: str
    cropName: str
    actionType: str  # "water", "fertilizer", "pesticide"
    day: int
    currentHp: int
    actions: List[dict]
    previousActions: Optional[List[dict]] = None
    currentWeather: Optional[str] = None  # 현재 날씨 정보


class GameEvaluateResponse(BaseModel):
    newHp: int
    hpChange: int
    feedback: str
    speechBubble: Optional[str] = None  # 말풍선 대사 추가


# 병해충 발생 체크를 위한 요청 모델
class PestCheckRequest(BaseModel):
    userId: str
    cropName: str
    day: int
    currentHp: int
    actions: List[dict]
    currentWeather: Optional[str] = None


# 병해충 발생 체크 응답 모델
class PestCheckResponse(BaseModel):
    pestOccurred: bool
    pestName: Optional[str] = None
    hpChange: int = 0
    feedback: str = ""


@app.post("/game/check-pest", response_model=PestCheckResponse)
def check_pest_occurrence(req: PestCheckRequest):
    """날짜 진행 시 병해충 발생 여부를 체크 (sickness.txt 기반)"""
    import random
    
    try:
        # 작물별 병해충 정보 가져오기
        sickness_info = get_sickness_info(req.cropName)
        
        # 기본 병해충 발생 확률 (절반으로 낮춤)
        base_probability = (0.05 + (req.day * 0.005)) * 0.5  # 날짜가 길수록 증가하지만 기본 확률을 절반으로
        base_probability = min(0.15, base_probability)  # 최대 확률도 절반으로 (0.3 -> 0.15)
        
        # HP가 낮을수록 확률 증가
        if req.currentHp < 50:
            base_probability *= 2.0
        elif req.currentHp < 70:
            base_probability *= 1.5
        
        # 관리 상태 평가 (최근 3일간의 행동)
        recent_actions = [a for a in req.actions if a.get("day", 0) >= req.day - 3]
        water_count = sum(1 for a in recent_actions if a.get("type") == "water")
        fertilizer_count = sum(1 for a in recent_actions if a.get("type") == "fertilizer")
        pesticide_count = sum(1 for a in recent_actions if a.get("type") == "pesticide")
        
        # 농약 살포 후 40일간 모든 병해충 방지 체크
        pesticide_actions = [a for a in req.actions if a.get("type") == "pesticide"]
        days_since_last_pesticide = None
        pesticide_protection_active = False
        if pesticide_actions:
            last_pesticide_day = max([a.get("day", 0) for a in pesticide_actions])
            days_since_last_pesticide = req.day - last_pesticide_day
            if days_since_last_pesticide < 40:
                pesticide_protection_active = True
        
        # 관리 상태에 따른 확률 조정
        management_score = 0
        if water_count > 0:
            management_score += 1
        if fertilizer_count > 0:
            management_score += 1
        if pesticide_count > 0:
            management_score += 1
        
        if management_score >= 2:
            base_probability *= 0.5
        elif management_score == 0:
            base_probability *= 3.0
        elif management_score == 1:
            base_probability *= 1.5
        
        # 날씨 기반 온도/습도 추정
        estimated_temp = 20
        estimated_humidity = 60
        
        weather_multiplier = 1.0
        if req.currentWeather:
            if req.currentWeather in ["비", "천둥"]:
                estimated_humidity = 85
                weather_multiplier = 2.0
            elif req.currentWeather == "맑음":
                estimated_humidity = 50
            elif req.currentWeather == "흐림":
                estimated_humidity = 75
                weather_multiplier = 1.3
        
        # sickness.txt에서 조건에 맞는 병해충 찾기
        possible_pests = []
        for sickness in sickness_info:
            desc = sickness.get("description", "")
            name = sickness.get("name", "")
            
            # 온도 조건 확인
            temp_range = extract_temperature_from_text(desc)
            if temp_range:
                temp_min, temp_max = temp_range
                if not (temp_min <= estimated_temp <= temp_max):
                    continue
            
            # 습도 조건 확인
            humidity_range = extract_humidity_from_text(desc)
            if humidity_range:
                hum_min, hum_max = humidity_range
                if not (hum_min <= estimated_humidity <= hum_max):
                    continue
            
            # 조건에 맞는 병해충 추가
            possible_pests.append(name)
        
        # 가능한 병해충이 없으면 기본 병해충 사용
        if not possible_pests:
            possible_pests = ["진딧물", "응애", "흰가루병", "역병", "노균병"]
        
        # 농약 살포 후 40일 이내면 모든 병해충 발생 방지
        if pesticide_protection_active:
            return PestCheckResponse(
                pestOccurred=False,
                hpChange=0,
                feedback=""
            )
        
        # 최종 확률 계산
        final_probability = min(0.15, base_probability * weather_multiplier)  # 최대 확률도 절반으로
        
        # 병해충 발생 여부 결정
        pest_occurred = random.random() < final_probability
        
        if pest_occurred:
            pest_type = random.choice(possible_pests)
            
            # HP 감소량 결정
            if management_score >= 2:
                hp_loss = random.randint(3, 5)
            elif management_score == 1:
                hp_loss = random.randint(5, 8)
            else:
                hp_loss = random.randint(8, 15)
            
            feedback = f"⚠️ {pest_type}이(가) 발생했습니다! ({hp_loss} HP 감소)"
            
            return PestCheckResponse(
                pestOccurred=True,
                pestName=pest_type,
                hpChange=-hp_loss,
                feedback=feedback
            )
        else:
            return PestCheckResponse(
                pestOccurred=False,
                hpChange=0,
                feedback=""
            )
            
    except Exception as e:
        print(f"병해충 체크 오류: {e}")
        return PestCheckResponse(
            pestOccurred=False,
            hpChange=0,
            feedback=""
        )


@app.post("/game/evaluate", response_model=GameEvaluateResponse)
def evaluate_game_action(req: GameActionRequest):
    """작물 관리 행동을 평가하고 HP를 계산 (txt 파일 데이터 기반)"""
    try:
        rule_based_hp_change = 0  # 규칙 기반 평가의 HP 변화를 별도로 저장
        feedback_parts = []
        
        # 1. 날씨 조건 체크: 습한 날씨(비, 눈)에 물을 주면 과습으로 판단
        weather_penalty_applied = False
        if req.actionType == "water" and req.currentWeather:
            if req.currentWeather in ["비", "눈", "천둥"]:
                rule_based_hp_change -= 8
                feedback_parts.append(f"⚠️ {req.currentWeather} 날씨에 물을 주면 과습이 될 수 있어요! 뿌리가 썩을 수 있습니다. (-8)")
                weather_penalty_applied = True
            elif req.currentWeather == "흐림":
                rule_based_hp_change -= 3
                feedback_parts.append(f"흐린 날씨에 물을 주는 것은 조금 위험할 수 있어요. (-3)")
                weather_penalty_applied = True
        
        # 2. 물주기 빈도 체크 (watering.txt 기반)
        # 날씨 페널티가 적용된 경우에는 빈도 체크를 건너뛰거나 조정
        if req.actionType == "water" and not weather_penalty_applied:
            watering_freq = get_watering_frequency(req.cropName, req.day)
            if watering_freq:
                # 해당 날짜의 물주기 빈도 확인
                # 현재 평가 중인 행동을 포함하여 오늘 물주기 횟수 확인
                # 현재 행동이 이미 actions에 포함되어 있을 수 있으므로, 현재 행동을 제외하고 계산
                today_actions = [a for a in req.actions if a.get("day") == req.day and a.get("type") == "water"]
                # 현재 평가 중인 행동도 오늘의 행동이므로 +1
                water_count_today = len(today_actions)
                # 현재 행동이 이미 포함되어 있지 않으면 +1 (일반적으로는 포함되어 있음)
                # 하지만 정확성을 위해 현재 행동 타임스탬프나 다른 식별자로 확인하는 것이 좋지만,
                # 간단하게는 현재 행동이 오늘이고 물주기면 포함된 것으로 간주
                
                # 날씨가 맑은 경우에만 정상 평가
                if req.currentWeather == "맑음" or not req.currentWeather:
                    # 빈도 파싱: "매일", "주 2~3회", "2~3일마다" 등
                    if "매일" in watering_freq:
                        # 매일 물을 주는 것이 정상
                        if water_count_today == 1:
                            rule_based_hp_change += 3
                            feedback_parts.append("적절한 물주기입니다! (+3)")
                        elif water_count_today > 1:
                            rule_based_hp_change -= 5
                            feedback_parts.append("하루에 여러 번 물을 주면 과습이 될 수 있어요! (-5)")
                    elif "겉흙 마르면" in watering_freq:
                        # "겉흙 마르면"은 필요할 때만 주는 것 (매일이 아님)
                        # 특히 감자 초반(0~10일)에는 과습을 피해야 함
                        if water_count_today == 0:
                            # 물을 주지 않았어도 페널티 없음 (겉흙이 마르지 않았을 수 있음)
                            pass
                        elif water_count_today == 1:
                            # 한 번 주는 것은 괜찮지만, 매일 주면 과습
                            # 최근 며칠간 물을 준 횟수 확인
                            recent_water_count = sum(1 for a in req.actions 
                                                    if a.get("type") == "water" 
                                                    and a.get("day") >= req.day - 2 
                                                    and a.get("day") <= req.day)
                            if recent_water_count >= 3:  # 최근 3일간 3번 이상 주면 과습
                                rule_based_hp_change -= 5
                                feedback_parts.append("'겉흙 마르면' 주는 것이므로 매일 주면 과습이 될 수 있어요! 특히 초반에는 과습을 피해야 합니다. (-5)")
                            else:
                                rule_based_hp_change += 1
                                feedback_parts.append("적절한 물주기입니다! (+1)")
                        elif water_count_today > 1:
                            rule_based_hp_change -= 5
                            feedback_parts.append("하루에 여러 번 물을 주면 과습이 될 수 있어요! '겉흙 마르면' 주는 것이므로 필요할 때만 주세요. (-5)")
                    elif "주 2~3회" in watering_freq:
                        # 주 2~3회면 3~4일마다 한 번
                        if water_count_today == 1:
                            rule_based_hp_change += 2
                            feedback_parts.append("적절한 물주기입니다! (+2)")
                        elif water_count_today > 1:
                            rule_based_hp_change -= 4
                            feedback_parts.append("물을 너무 자주 주셨어요. (-4)")
                    elif "주 1~2회" in watering_freq or "주 1회" in watering_freq:
                        # 주 1~2회면 3~7일마다 한 번
                        if water_count_today == 1:
                            rule_based_hp_change += 2
                            feedback_parts.append("적절한 물주기입니다! (+2)")
                        elif water_count_today > 1:
                            rule_based_hp_change -= 4
                            feedback_parts.append("물을 너무 자주 주셨어요. (-4)")
                    elif "2~3일마다" in watering_freq:
                        # 2~3일마다
                        if water_count_today == 1:
                            rule_based_hp_change += 2
                            feedback_parts.append("적절한 물주기입니다! (+2)")
                        elif water_count_today > 1:
                            rule_based_hp_change -= 4
                            feedback_parts.append("물을 너무 자주 주셨어요. (-4)")
                # 날씨가 맑지 않은 경우 (흐림 등) - 날씨 페널티가 없으면 기본적으로 좋은 행동으로 평가
                if req.currentWeather == "흐림" and not weather_penalty_applied:
                    # 흐린 날씨지만 페널티가 없으면 (비/눈이 아니면) 기본적으로 좋은 행동
                    if water_count_today == 1:
                        rule_based_hp_change += 2
                        feedback_parts.append("흐린 날씨지만 적절한 물주기입니다! (+2)")
                    elif water_count_today > 1:
                        rule_based_hp_change -= 3
                        feedback_parts.append("흐린 날씨에 물을 너무 많이 주면 위험할 수 있어요. (-3)")
            else:
                # watering.txt에 정보가 없을 때도 기본적으로 좋은 행동으로 평가
                # 날씨가 맑거나 없으면 기본 보너스
                if req.currentWeather == "맑음" or not req.currentWeather:
                    today_actions = [a for a in req.actions if a.get("day") == req.day and a.get("type") == "water"]
                    water_count_today = len(today_actions)
                    if water_count_today == 1:
                        rule_based_hp_change += 2
                        feedback_parts.append("적절한 물주기입니다! (+2)")
                    elif water_count_today > 1:
                        rule_based_hp_change -= 3
                        feedback_parts.append("하루에 여러 번 물을 주면 과습이 될 수 있어요! (-3)")
        
        # 3. 비료 주기 체크 (fertilizing.txt 기반)
        elif req.actionType == "fertilizer":
            fertilizing_period = get_fertilizing_period(req.cropName)
            if fertilizing_period:
                # 비료 주기 정보에서 숫자 추출
                period_match = re.search(r"(\d+)", fertilizing_period)
                if period_match:
                    expected_days = int(period_match.group(1))
                    # 마지막 비료 준 날짜 확인
                    last_fertilizer_days = [a.get("day") for a in req.actions if a.get("type") == "fertilizer"]
                    if last_fertilizer_days:
                        days_since_last = req.day - max(last_fertilizer_days)
                        if days_since_last >= expected_days - 2:  # ±2일 여유
                            rule_based_hp_change += 4
                            feedback_parts.append(f"적절한 시기에 비료를 주셨어요! (+4)")
                        elif days_since_last < expected_days - 2:
                            rule_based_hp_change -= 3
                            feedback_parts.append(f"비료를 너무 자주 주셨어요. {expected_days}일 간격이 적당합니다. (-3)")
                    else:
                        # 첫 비료
                        if req.day >= expected_days - 2:
                            rule_based_hp_change += 4
                            feedback_parts.append(f"적절한 시기에 비료를 주셨어요! (+4)")
                        else:
                            rule_based_hp_change -= 2
                            feedback_parts.append(f"비료 주기 시기가 이르네요. {expected_days}일 후가 적당합니다. (-2)")
        
        # 4. LLM 기반 종합 판단 (주 판단 로직)
        crop_guide = get_crop_guide_for_game(req.cropName)
        
        # 최근 행동 요약 및 분석
        recent_summary = ""
        if req.previousActions:
            water_count = sum(1 for a in req.previousActions if a.get("type") == "water")
            fert_count = sum(1 for a in req.previousActions if a.get("type") == "fertilizer")
            pest_count = sum(1 for a in req.previousActions if a.get("type") == "pesticide")
            recent_summary = f"최근 {len(req.previousActions)}일간 - 물주기: {water_count}회, 비료: {fert_count}회, 농약살포: {pest_count}회"
        else:
            recent_summary = "첫 관리입니다."
        
        # 최근 행동 분석 (HP 감소 시 구체적인 필요사항 판단을 위해)
        recent_water_count = sum(1 for a in req.actions if a.get("type") == "water" and a.get("day") >= req.day - 3)
        recent_fertilizer_count = sum(1 for a in req.actions if a.get("type") == "fertilizer" and a.get("day") >= req.day - 3)
        days_since_last_water = req.day
        days_since_last_fertilizer = req.day
        water_actions = [a for a in req.actions if a.get("type") == "water"]
        fertilizer_actions = [a for a in req.actions if a.get("type") == "fertilizer"]
        if water_actions:
            days_since_last_water = req.day - max([a.get("day") for a in water_actions])
        if fertilizer_actions:
            days_since_last_fertilizer = req.day - max([a.get("day") for a in fertilizer_actions])
        
        # 연속 판단 추적: 최근 행동들의 실제 HP 변화를 계산하여 연속성 확인
        consecutive_good = 0  # 연속으로 좋은 판단 횟수 (HP 증가)
        consecutive_bad = 0   # 연속으로 나쁜 판단 횟수 (HP 감소)
        
        # 최근 행동들을 실제로 평가하여 HP 변화 추적
        if req.previousActions and len(req.previousActions) > 0:
            # 최근 5개 행동만 확인 (성능 고려)
            recent_actions_to_check = req.previousActions[-5:] if len(req.previousActions) > 5 else req.previousActions
            
            # 각 행동을 평가하여 HP 변화 계산
            simulated_hp = req.currentHp
            recent_hp_changes = []
            
            for prev_action in reversed(recent_actions_to_check):
                action_day = prev_action.get("day", 0)
                action_type = prev_action.get("type", "")
                action_weather = prev_action.get("weather", "")
                
                # 간단한 평가 (실제 evaluate_game_action 호출은 성능상 부담)
                # 규칙 기반으로 빠르게 평가
                estimated_hp_change = 0
                
                if action_type == "water":
                    if action_weather in ["비", "눈", "천둥"]:
                        estimated_hp_change = -8  # 나쁨
                    elif action_weather == "흐림":
                        estimated_hp_change = -3  # 약간 나쁨
                    elif action_weather == "맑음":
                        # 물주기 빈도 확인
                        watering_freq = get_watering_frequency(req.cropName, action_day)
                        if watering_freq:
                            # 같은 날 물주기 횟수 확인
                            same_day_actions = [a for a in req.actions if a.get("day") == action_day and a.get("type") == "water"]
                            if len(same_day_actions) == 1:
                                estimated_hp_change = 2  # 좋음
                            elif len(same_day_actions) > 1:
                                estimated_hp_change = -5  # 나쁨
                        else:
                            estimated_hp_change = 1  # 기본적으로 좋음
                elif action_type == "fertilizer":
                    # 비료는 기본적으로 좋은 행동
                    estimated_hp_change = 2
                elif action_type == "pesticide":
                    # 농약은 기본적으로 좋은 행동
                    estimated_hp_change = 1
                
                recent_hp_changes.insert(0, estimated_hp_change)
                simulated_hp -= estimated_hp_change  # 역순으로 계산하므로 빼기
            
            # 연속성 계산 (최근부터 역순으로)
            for hp_change_val in reversed(recent_hp_changes):
                if hp_change_val > 0:
                    consecutive_good += 1
                    consecutive_bad = 0  # 좋은 판단이 나오면 나쁜 연속성 리셋
                elif hp_change_val < 0:
                    consecutive_bad += 1
                    consecutive_good = 0  # 나쁜 판단이 나오면 좋은 연속성 리셋
                else:
                    # 중립(0)이면 연속성 리셋
                    consecutive_good = 0
                    consecutive_bad = 0
                
                # 최대 3번까지만 연속성 확인 (너무 오래 반영하지 않음)
                if consecutive_good >= 3 or consecutive_bad >= 3:
                    break
        
        # 오늘 행동 요약
        today_actions = [a for a in req.actions if a.get("day") == req.day and a.get("type") == req.actionType]
        today_action_count = len(today_actions)
        
        # 날씨 정보를 가이드라인에 추가 (명확하게 강조)
        weather_info = ""
        if req.currentWeather:
            weather_info = f"\n\n⚠️ 현재 날씨: {req.currentWeather} ⚠️\n이 날씨 정보는 행동 평가에 매우 중요합니다. 말풍선 대사에서 날씨를 언급할 때는 반드시 이 날씨({req.currentWeather})를 정확히 사용하세요. 다른 날씨를 추측하거나 언급하지 마세요!"
        
        # 물주기/비료 정보 추가
        data_info = ""
        rule_based_info = ""  # 규칙 기반 평가 결과를 LLM에게 참고용으로 제공
        action_context = ""  # 최근 행동 분석 정보 (HP 감소 시 구체적인 필요사항 판단을 위해)
        
        if req.actionType == "water":
            watering_freq = get_watering_frequency(req.cropName, req.day)
            if watering_freq:
                data_info = f"\n권장 물주기 빈도: {watering_freq}"
            
            # 최근 물주기 정보
            action_context = f"\n최근 물주기 정보: 최근 3일간 {recent_water_count}회 물을 주셨고, 마지막 물주기로부터 {days_since_last_water}일이 지났습니다."
            if days_since_last_water >= 3:
                action_context += " 물이 부족할 수 있습니다."
            
            # 규칙 기반 평가 결과 요약
            if feedback_parts:
                rule_based_info = f"\n규칙 기반 평가 참고: {'; '.join(feedback_parts)}"
        elif req.actionType == "fertilizer":
            fertilizing_period = get_fertilizing_period(req.cropName)
            if fertilizing_period:
                data_info = f"\n권장 비료 주기: {fertilizing_period}"
            
            # 최근 비료 정보
            action_context = f"\n최근 비료 정보: 최근 3일간 {recent_fertilizer_count}회 비료를 주셨고, 마지막 비료로부터 {days_since_last_fertilizer}일이 지났습니다."
            if days_since_last_fertilizer >= 20:
                action_context += " 비료가 부족할 수 있습니다."
            
            # 규칙 기반 평가 결과 요약
            if feedback_parts:
                rule_based_info = f"\n규칙 기반 평가 참고: {'; '.join(feedback_parts)}"
        elif req.actionType == "fertilizer":
            fertilizing_period = get_fertilizing_period(req.cropName)
            if fertilizing_period:
                data_info = f"\n권장 비료 주기: {fertilizing_period}"
            # 규칙 기반 평가 결과 요약
            if feedback_parts:
                rule_based_info = f"\n규칙 기반 평가 참고: {'; '.join(feedback_parts)}"
        
        # 행동 유형 한국어 변환
        action_kr = {
            "water": "물주기",
            "fertilizer": "비료주기",
            "pesticide": "농약살포"
        }.get(req.actionType, req.actionType)
        
        # 연속성 정보를 LLM에게 제공
        continuity_info = ""
        if consecutive_good > 0:
            continuity_info = f"\n⚠️ 중요: 최근 {consecutive_good}번 연속으로 좋은 관리가 이루어졌습니다. 이번 행동도 좋다면 보너스를 적용하세요 (HP 증가량을 1.5~2배로 증가)."
        elif consecutive_bad > 0:
            continuity_info = f"\n⚠️ 중요: 최근 {consecutive_bad}번 연속으로 부적절한 관리가 이루어졌습니다. 이번 행동도 부적절하다면 페널티를 강화하세요 (HP 감소량을 1.5~2배로 증가)."
        
        # LLM 판단 초기화 (None으로 초기화하여 LLM이 호출되지 않았음을 표시)
        llm_hp_change = None
        llm_feedback = None
        llm_speech_bubble = None
        
        # LLM이 종합적으로 판단 (규칙 기반 평가 결과를 참고하되, 최종 판단은 LLM이 수행)
        try:
            # 날씨 정보 디버깅
            if req.currentWeather:
                print(f"🌤️ 날씨 정보 전달: {req.currentWeather} (행동: {action_kr}, 날짜: {req.day})")
            
            chain = game_prompt | llm
            result = chain.invoke({
                "crop_name": req.cropName,  # 작물 이름 추가
                "crop_guide": crop_guide + weather_info + data_info + action_context + rule_based_info + continuity_info,
                "action_type": action_kr,
                "day": req.day,
                "current_hp": req.currentHp,
                "recent_actions": f"{recent_summary}\n오늘 {action_kr} 횟수: {today_action_count}회"
            })
            
            # JSON 응답 파싱 시도
            response_text = result.content if hasattr(result, "content") else str(result)
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    eval_result = json.loads(json_match.group())
                    # LLM 판단 결과
                    llm_hp_change = int(eval_result.get("hp_change", 0))
                    llm_feedback = eval_result.get("feedback", "관리 중입니다.")
                    llm_speech_bubble = eval_result.get("speech_bubble", None)  # 말풍선 대사
                    print(f"✅ LLM 응답 파싱 성공: hp_change={llm_hp_change}, feedback={llm_feedback[:50]}")
                    # 날씨 정보 일치 확인 및 수정
                    if req.currentWeather and llm_speech_bubble:
                        # LLM이 잘못된 날씨를 언급했는지 확인
                        weather_types = ["맑음", "비", "눈", "흐림", "천둥", "바람"]
                        mentioned_weathers = [w for w in weather_types if w in llm_speech_bubble]
                        if mentioned_weathers and req.currentWeather not in mentioned_weathers:
                            print(f"⚠️ 경고: LLM이 잘못된 날씨를 언급했습니다! 실제 날씨: {req.currentWeather}, 언급된 날씨: {mentioned_weathers}")
                            # 잘못된 날씨 언급을 실제 날씨로 수정
                            for wrong_weather in mentioned_weathers:
                                if wrong_weather != req.currentWeather:
                                    llm_speech_bubble = llm_speech_bubble.replace(wrong_weather, req.currentWeather)
                            print(f"✅ 날씨 정보 수정 완료: {llm_speech_bubble[:100]}")
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    print(f"❌ LLM JSON 파싱 오류: {e}, 응답: {response_text[:200]}")
                    # 파싱 실패 시 규칙 기반 평가 사용을 위해 llm_hp_change를 None으로 설정
                    llm_hp_change = None
                    llm_feedback = None
                    llm_speech_bubble = None
            else:
                print(f"❌ LLM JSON 패턴 매칭 실패, 응답: {response_text[:200]}")
                # JSON 패턴을 찾지 못한 경우
                llm_hp_change = None
                llm_feedback = None
                llm_speech_bubble = None
                
                # HP가 낮을 때 좋은 행동에 대한 추가 보너스
                hp_recovery_bonus = 0
                if llm_hp_change > 0:
                    # HP가 낮을수록 회복 보너스 증가
                    if req.currentHp <= 30:
                        hp_recovery_bonus = 3  # 매우 낮을 때 큰 보너스
                    elif req.currentHp <= 50:
                        hp_recovery_bonus = 2  # 낮을 때 보너스
                    elif req.currentHp <= 70:
                        hp_recovery_bonus = 1  # 중간일 때 작은 보너스
                    
                    if hp_recovery_bonus > 0:
                        llm_hp_change += hp_recovery_bonus
                        if llm_speech_bubble:
                            llm_speech_bubble = llm_speech_bubble.replace("감사해요", "정말 감사해요! 건강이 많이 좋아졌어요!")
                
                # 연속성에 따른 가중치 적용
                if llm_hp_change > 0 and consecutive_good > 0:
                    # 연속으로 좋은 판단 → 보너스 적용
                    bonus_multiplier = 1.0 + (consecutive_good * 0.3)  # 연속 1번: 1.3배, 2번: 1.6배, 3번: 1.9배
                    bonus_multiplier = min(2.0, bonus_multiplier)  # 최대 2배
                    llm_hp_change = int(llm_hp_change * bonus_multiplier)
                    if consecutive_good >= 2:
                        llm_feedback += f" (연속 좋은 관리 보너스! +{int((bonus_multiplier - 1.0) * 100)}%)"
                        if llm_speech_bubble:
                            llm_speech_bubble += f" 연속으로 잘 챙겨주셔서 정말 기뻐요! 🎉"
                elif llm_hp_change < 0 and consecutive_bad > 0:
                    # 연속으로 나쁜 판단 → 페널티 강화
                    penalty_multiplier = 1.0 + (consecutive_bad * 0.3)  # 연속 1번: 1.3배, 2번: 1.6배, 3번: 1.9배
                    penalty_multiplier = min(2.0, penalty_multiplier)  # 최대 2배
                    llm_hp_change = int(llm_hp_change * penalty_multiplier)
                    if consecutive_bad >= 2:
                        llm_feedback += f" (연속 부적절한 관리 페널티! {int((penalty_multiplier - 1.0) * 100)}% 추가 감소)"
                        if llm_speech_bubble:
                            llm_speech_bubble += f" 계속 이렇게 되면 힘들어요... 제발 날씨를 확인하고 관리해주세요! 😢"
        except Exception as e:
            # LLM 호출 실패 시 무시 (규칙 기반 평가 사용)
            print(f"❌ LLM 호출 오류: {e}")
            llm_hp_change = None
            llm_feedback = None
            llm_speech_bubble = None
        
        # 피드백 설정
        if llm_feedback:
            feedback_parts = [llm_feedback]
        elif not feedback_parts:
            feedback_parts = ["관리 중입니다."]
        
        # HP 변화는 규칙 기반 평가와 LLM 판단을 조합
        # 규칙 기반 평가가 양수면 최소한 그 값은 보장하고, LLM이 더 높은 값을 주면 그것을 사용
        # LLM이 실패하거나 None이면 규칙 기반 평가를 사용
        if llm_hp_change is None:
            # LLM 파싱 실패 시 규칙 기반 평가 사용
            hp_change = rule_based_hp_change
            print(f"⚠️ LLM 파싱 실패, 규칙 기반 평가 사용: hp_change={hp_change}")
        elif rule_based_hp_change > 0:
            # 규칙 기반 평가가 양수면, LLM 판단과 비교하여 더 큰 값을 사용
            # 단, LLM이 음수로 판단한 경우는 규칙 기반 평가를 우선
            if llm_hp_change < 0:
                # LLM이 음수로 판단했지만 규칙 기반 평가가 양수면 규칙 기반 평가 사용
                hp_change = rule_based_hp_change
                print(f"⚠️ LLM이 음수 판단했지만 규칙 기반 평가가 양수, 규칙 기반 사용: hp_change={hp_change}")
            elif llm_hp_change == 0:
                # LLM이 0을 반환했지만 규칙 기반 평가가 양수면 규칙 기반 평가 사용
                hp_change = rule_based_hp_change
                print(f"⚠️ LLM이 0 반환했지만 규칙 기반 평가가 양수, 규칙 기반 사용: hp_change={hp_change}")
            else:
                # 둘 다 양수면 더 큰 값 사용 (LLM 판단에 보너스가 적용되어 있을 수 있음)
                hp_change = max(rule_based_hp_change, llm_hp_change)
                print(f"✅ 둘 다 양수, 더 큰 값 사용: hp_change={hp_change} (규칙: {rule_based_hp_change}, LLM: {llm_hp_change})")
        elif rule_based_hp_change < 0:
            # 규칙 기반 평가가 음수면 (페널티), LLM 판단과 비교하여 더 나쁜 값 사용
            if llm_hp_change == 0 or llm_hp_change is None:
                hp_change = rule_based_hp_change
            else:
                hp_change = min(rule_based_hp_change, llm_hp_change)
        else:
            # 규칙 기반 평가가 0이면 LLM 판단 사용
            # 하지만 물주기/비료주기 같은 경우 기본적으로 좋은 행동이므로 최소한 +1은 보장
            if req.actionType in ["water", "fertilizer"] and llm_hp_change is None:
                # LLM이 실패했고 규칙 기반 평가도 0이면, 기본적으로 좋은 행동으로 간주
                # 날씨 페널티가 없고 하루에 한 번만 행동했다면 기본 보너스
                today_actions = [a for a in req.actions if a.get("day") == req.day and a.get("type") == req.actionType]
                if len(today_actions) == 1 and not weather_penalty_applied:
                    hp_change = 1  # 기본 보너스
                    print(f"✅ 규칙 기반 평가 0이고 LLM도 실패했지만, 적절한 행동으로 기본 보너스 +1")
                else:
                    hp_change = 0
                    print(f"⚠️ 규칙 기반 평가 0이고 LLM도 실패, hp_change=0")
            else:
                hp_change = llm_hp_change if llm_hp_change is not None else 0
                if llm_hp_change is None:
                    print(f"⚠️ 규칙 기반 평가 0이고 LLM도 실패, hp_change=0")
        
        # 말풍선 대사가 없으면 기본 메시지 생성 (HP 감소 시 구체적인 피드백)
        if not llm_speech_bubble:
            if hp_change > 0:
                llm_speech_bubble = f"좋은 관리 감사해요! 이렇게 계속 챙겨주시면 더 건강해질 거예요! 💚"
            elif hp_change < 0:
                # HP 감소 시 구체적인 필요사항 전달
                if req.actionType == "water" and weather_penalty_applied:
                    llm_speech_bubble = f"물이 너무 많아서 힘들어요... 비 오는 날에는 물을 주지 말아주세요! 맑은 날에만 주시면 좋을 것 같아요 😢"
                elif req.actionType == "water":
                    # 물주기 관련 문제
                    llm_speech_bubble = f"저 너무 목말라요... 적절한 시기에 물을 주시면 더 건강해질 수 있을 거예요! 💧"
                elif req.actionType == "fertilizer":
                    llm_speech_bubble = f"비료를 너무 많이 주셨어요... 적당한 양만 주시면 좋을 것 같아요! 🌿"
                else:
                    llm_speech_bubble = f"조금 힘들어요... 날씨를 확인하고 적절한 시기에 관리해주시면 좋겠어요! 🌱"
            else:
                llm_speech_bubble = f"괜찮아요! 조금만 더 신경 써주시면 더 좋을 것 같아요! ☀️"
        
        # 최종 피드백 조합
        feedback = " ".join(feedback_parts) if feedback_parts else "관리 중입니다."
        
        # 디버깅: HP 변화 로그
        print(f"🔍 HP 계산: currentHp={req.currentHp}, hp_change={hp_change}, rule_based={rule_based_hp_change}, llm={llm_hp_change}")
        
        # HP 계산
        new_hp = max(0, min(100, req.currentHp + hp_change))
        
        print(f"✅ 최종 HP: {new_hp} (변화: {hp_change})")
        
        # 말풍선 대사 (LLM이 생성한 것이 있으면 사용, 없으면 기본값)
        speech_bubble = llm_speech_bubble if 'llm_speech_bubble' in locals() else None
        if not speech_bubble:
            if hp_change > 0:
                speech_bubble = f"좋은 관리 감사해요! 이렇게 계속 챙겨주시면 더 건강해질 거예요! 💚"
            elif hp_change < 0:
                # HP 감소 시 구체적인 필요사항 전달
                if req.actionType == "water" and weather_penalty_applied:
                    speech_bubble = f"물이 너무 많아서 힘들어요... 비 오는 날에는 물을 주지 말아주세요! 맑은 날에만 주시면 좋을 것 같아요 😢"
                elif req.actionType == "water":
                    speech_bubble = f"저 너무 목말라요... 적절한 시기에 물을 주시면 더 건강해질 수 있을 거예요! 💧"
                elif req.actionType == "fertilizer":
                    speech_bubble = f"비료를 너무 많이 주셨어요... 적당한 양만 주시면 좋을 것 같아요! 🌿"
                else:
                    speech_bubble = f"조금 힘들어요... 날씨를 확인하고 적절한 시기에 관리해주시면 좋겠어요! 🌱"
            else:
                speech_bubble = f"괜찮아요! 조금만 더 신경 써주시면 더 좋을 것 같아요! ☀️"
        
        # 작물일기 저장은 다음날 평가 시에만 저장 (즉시 평가는 하지 않음)
        # 즉시 평가는 제거되었으므로 여기서는 저장하지 않음
        
        return GameEvaluateResponse(
            newHp=new_hp,
            hpChange=hp_change,
            feedback=feedback,
            speechBubble=speech_bubble
        )
        
    except Exception as e:
        print(f"게임 평가 오류: {e}")
        # 오류 시 기본값 반환
        return GameEvaluateResponse(
            newHp=req.currentHp,
            hpChange=0,
            feedback="관리 중입니다.",
            speechBubble="괜찮아요! 조금만 더 신경 써주시면 더 좋을 것 같아요! ☀️"
        )


# 한국어 조사 처리 함수
def get_josa(word: str, josa_type: str) -> str:
    """단어의 받침 유무에 따라 적절한 조사 반환
    josa_type: 'i_ga' (이/가), 'eul_reul' (을/를), 'eun_neun' (은/는)
    """
    if not word:
        return ""
    
    # 마지막 글자의 유니코드 값으로 받침 확인
    last_char = word[-1]
    if '가' <= last_char <= '힣':
        # 한글인 경우
        code = ord(last_char) - ord('가')
        has_batchim = code % 28 != 0  # 받침이 있으면 True
    else:
        # 한글이 아닌 경우 (숫자, 영어 등)
        has_batchim = False
    
    if josa_type == 'i_ga':
        return '이' if has_batchim else '가'
    elif josa_type == 'eul_reul':
        return '을' if has_batchim else '를'
    elif josa_type == 'eun_neun':
        return '은' if has_batchim else '는'
    return ""


# 작물일기 관련 함수
def convert_feedback_to_diary(crop_name: str, day: int, action_type: str, hp_change: int, 
                               feedback: str, speech_bubble: Optional[str] = None, 
                               weather: Optional[str] = None) -> Optional[str]:
    """피드백을 작물일기 형식(1인칭 독백)으로 변환"""
    try:
        # 행동 타입 한국어 변환
        action_kr = {
            "water": "물",
            "fertilizer": "비료",
            "pesticide": "농약",
            "daily_evaluation": "하루 평가",
            "auto_water": "자연 관수"  # 비/눈으로 인한 자동 물주기
        }.get(action_type, action_type)
        
        # 날씨 정보
        weather_text = ""
        weather_josa = ""
        if weather:
            weather_emoji = {
                "맑음": "☀️",
                "비": "🌧️",
                "눈": "❄️",
                "흐림": "☁️",
                "천둥": "⛈️",
                "바람": "💨"
            }.get(weather, "")
            weather_josa = get_josa(weather, 'i_ga')  # 비가, 눈이 등
            weather_text = f" 오늘은 {weather}{weather_emoji} 날씨였어요."
        
        # speech_bubble이 있으면 그것을 기반으로 작성 (더 자연스러움)
        if speech_bubble:
            # speech_bubble을 1인칭 독백 형식으로 변환
            # "~해주세요" 같은 표현을 "~해주셨으면 좋겠어요" 같은 독백 형식으로 변환
            diary_text = speech_bubble
            diary_text = diary_text.replace("주세요", "주셨으면 좋겠어요")
            diary_text = diary_text.replace("주시면", "주셨으면")
            diary_text = diary_text.replace("해주세요", "해주셨으면 좋겠어요")
            diary_text = diary_text.replace("해주시면", "해주셨으면")
            
            # 날짜와 날씨 정보 추가
            diary = f"{day}일차{weather_text}... {diary_text}"
            return diary
        
        # speech_bubble이 없으면 피드백 기반으로 작성
        # HP 변화에 따라 다른 톤으로 작성
        # 행동에 대한 조사 계산
        action_josa = get_josa(action_kr, 'eul_reul')  # 물을, 비료를 등
        
        if hp_change > 0:
            # HP 증가 - 기쁨과 감사
            if action_type == "auto_water":
                # 자연 관수 (비/눈)
                diary = f"{day}일차{weather_text} {weather}{weather_josa} 와서 자연스럽게 수분을 받았어요! 하늘에서 내려주는 물이라 더 시원하고 좋아요! 자연의 선물이에요 🌧️💚"
            elif "물" in action_kr:
                diary = f"{day}일차{weather_text} 오늘 {action_kr}{action_josa} 주셔서 정말 기뻐요! 건강이 많이 좋아진 것 같아요. 이렇게 계속 챙겨주시면 더 잘 자랄 수 있을 거예요 💚"
            elif "비료" in action_kr:
                diary = f"{day}일차{weather_text} 오늘 {action_kr}{action_josa} 주셔서 영양분을 충분히 받았어요! 이제 더 튼튼하게 자랄 수 있을 것 같아요 🌿"
            else:
                diary = f"{day}일차{weather_text} 오늘 {action_kr}{action_josa} 주셔서 안전하게 자랄 수 있어요! 감사해요 🛡️"
        elif hp_change < 0:
            # HP 감소 - 아픔과 기대
            if "과습" in feedback or "너무 많이" in feedback:
                diary = f"{day}일차{weather_text} 오늘 {action_kr}{action_josa} 너무 많이 주셔서 힘들어요. 뿌리가 숨을 쉬기 어려워요... 조금만 주시면 좋을 것 같아요 😢"
            elif "물" in action_kr or "관수" in feedback or "목말라" in feedback:
                diary = f"{day}일차{weather_text} 어제 물을 안 주셔서 너무 목말라요... 오늘은 물을 주시겠지? 기대하고 있을게요 💧"
            elif "비료" in action_kr or "비료" in feedback:
                diary = f"{day}일차{weather_text} 어제 비료를 안 주셔서 영양분이 부족해요... 배고파요... 오늘은 비료를 주시겠지? 🌿"
            else:
                diary = f"{day}일차{weather_text} 오늘 조금 힘들었어요. 하지만 내일은 더 나아질 거예요... 기대하고 있을게요 🌱"
        else:
            # HP 변화 없음 - 중립적
            if action_type == "daily_evaluation":
                diary = f"{day}일차{weather_text} 오늘 하루가 지났어요. 괜찮아요! 조금만 더 신경 써주시면 더 건강해질 수 있을 거예요 ☀️"
            else:
                diary = f"{day}일차{weather_text} 오늘 {action_kr}{action_josa} 주셨어요. 괜찮아요! 조금만 더 신경 써주시면 더 건강해질 수 있을 거예요 ☀️"
        
        return diary
    except Exception as e:
        print(f"작물일기 변환 오류: {e}")
        return None


# 작물일기 조회 요청 모델
class CropDiaryRequest(BaseModel):
    userId: str
    cropName: str


# 작물일기 응답 모델
class CropDiaryResponse(BaseModel):
    entries: List[dict]  # [{day: int, entry: str, hpChange: int, timestamp: str}, ...]


@app.get("/game/diary/{user_id}/{crop_name}", response_model=CropDiaryResponse)
def get_crop_diary(user_id: str, crop_name: str, game_start_time: Optional[str] = None):
    """작물일기 조회 - gameStartTime으로 세션 구분"""
    try:
        # 쿼리 조건 구성
        query = {"userId": user_id, "cropName": crop_name}
        
        # gameStartTime이 있으면 해당 세션의 일기만 조회
        if game_start_time:
            query["gameStartTime"] = game_start_time
        
        entries = list(crop_diary_collection.find(
            query,
            {"_id": False}
        ).sort("day", -1))  # 최신순 정렬 (최신 일기가 위에)
        
        return CropDiaryResponse(entries=entries)
    except Exception as e:
        print(f"작물일기 조회 오류: {e}")
        return CropDiaryResponse(entries=[])


# 전날 행동들을 일괄 평가하는 요청 모델
class EvaluatePreviousDayRequest(BaseModel):
    userId: str
    cropName: str
    day: int  # 평가할 날짜 (전날)
    currentHp: int
    actions: List[dict]  # 전날의 행동들
    previousActions: Optional[List[dict]] = None  # 그 이전 행동들
    gameStartTime: Optional[str] = None  # 게임 시작 시간 (세션 구분용)
    weatherOnThatDay: Optional[str] = None  # 그 날의 날씨


# 전날 행동 평가 응답 모델
class EvaluatePreviousDayResponse(BaseModel):
    newHp: int
    totalHpChange: int
    feedbacks: List[str]  # 각 행동에 대한 피드백들
    speechBubble: Optional[str] = None  # 작물 캐릭터의 말풍선 대사 (종합)


@app.post("/game/evaluate-previous-day", response_model=EvaluatePreviousDayResponse)
def evaluate_previous_day_actions(req: EvaluatePreviousDayRequest):
    """전날의 행동들을 일괄 평가하고 HP 변화를 계산"""
    try:
        # 디버깅: 받은 날씨 정보 출력
        print(f"📅 전날 평가 시작 - 날짜: {req.day}, 전달받은 날씨: {req.weatherOnThatDay}")
        
        # 전날의 행동들 필터링
        previous_day_actions = [a for a in req.actions if a.get("day") == req.day]
        print(f"📋 전날 행동 수: {len(previous_day_actions)}, 행동들: {[a.get('type') for a in previous_day_actions]}")
        
        if not previous_day_actions:
            # 전날 행동이 없을 때 날씨 확인
            # 비/눈 날씨에는 자동으로 물을 준 것으로 처리 (HP 회복)
            print(f"🌧️ 행동 없음 - 날씨 확인: {req.weatherOnThatDay}")
            if req.weatherOnThatDay and req.weatherOnThatDay in ["비", "눈"]:
                auto_water_hp = 2  # 자연 관수 효과
                new_hp = min(100, req.currentHp + auto_water_hp)
                print(f"✅ 자동 물주기 효과 적용: {req.weatherOnThatDay} 날씨로 HP +{auto_water_hp}")
                
                # 자동 물주기 효과를 작물일기에 기록
                try:
                    diary_entry = convert_feedback_to_diary(
                        crop_name=req.cropName,
                        day=req.day,
                        action_type="auto_water",
                        hp_change=auto_water_hp,
                        feedback=f"어제 {req.weatherOnThatDay}{get_josa(req.weatherOnThatDay, 'i_ga')} 와서 자연스럽게 수분을 받았어요!",
                        speech_bubble=f"어제 {req.weatherOnThatDay}{get_josa(req.weatherOnThatDay, 'i_ga')} 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚",
                        weather=req.weatherOnThatDay
                    )
                    if diary_entry:
                        crop_diary_collection.insert_one({
                            "userId": req.userId,
                            "cropName": req.cropName,
                            "day": req.day,
                            "entry": diary_entry,
                            "hpChange": auto_water_hp,
                            "actionType": "auto_water",
                            "weather": req.weatherOnThatDay,
                            "gameStartTime": req.gameStartTime,
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    print(f"자동 물주기 일기 저장 오류: {e}")
                
                return EvaluatePreviousDayResponse(
                    newHp=new_hp,
                    totalHpChange=auto_water_hp,
                    feedbacks=[f"어제 {req.weatherOnThatDay}{get_josa(req.weatherOnThatDay, 'i_ga')} 와서 자연스럽게 수분을 받았습니다! (+{auto_water_hp})"],
                    speechBubble=f"어제 {req.weatherOnThatDay}{get_josa(req.weatherOnThatDay, 'i_ga')} 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚"
                )
            
            # 맑은 날이나 날씨 정보가 없을 때: watering.txt 기반으로 관수 시기 확인
            watering_freq = get_watering_frequency(req.cropName, req.day)
            if watering_freq:
                # 마지막으로 물을 준 날짜 확인
                water_actions = [a for a in req.actions if a.get("type") == "water" and a.get("day") < req.day]
                days_since_last_water = req.day
                if water_actions:
                    last_water_day = max([a.get("day") for a in water_actions])
                    days_since_last_water = req.day - last_water_day
                else:
                    # 물을 한 번도 주지 않았다면 현재 날짜가 마지막 날짜
                    days_since_last_water = req.day
                
                # 권장 물주기 빈도에 따라 방치 여부 판단
                should_water = False
                if "매일" in watering_freq:
                    # 매일 물을 줘야 함
                    should_water = (days_since_last_water >= 1)
                elif "겉흙 마르면" in watering_freq:
                    # "겉흙 마르면"은 필요할 때만 주는 것이므로 방치 페널티 없음
                    # (겉흙이 마르지 않았을 수 있음)
                    should_water = False
                elif "주 2~3회" in watering_freq:
                    # 주 2~3회 = 3~4일마다 한 번
                    should_water = (days_since_last_water >= 4)
                elif "주 1~2회" in watering_freq or "주 1회" in watering_freq:
                    # 주 1~2회 = 3~7일마다 한 번
                    should_water = (days_since_last_water >= 7)
                elif "2~3일마다" in watering_freq:
                    # 2~3일마다
                    should_water = (days_since_last_water >= 3)
                elif "주2회" in watering_freq or "주 2회" in watering_freq:
                    # 주 2회 = 3~4일마다 한 번
                    should_water = (days_since_last_water >= 4)
                
                # 날씨가 비/눈이면 자동으로 물을 준 것으로 처리 (HP 회복)
                if should_water and req.weatherOnThatDay and req.weatherOnThatDay in ["비", "눈"]:
                    auto_water_hp = 2  # 자연 관수 효과
                    new_hp = min(100, req.currentHp + auto_water_hp)
                    
                    # 자동 물주기 효과를 작물일기에 기록
                    try:
                        diary_entry = convert_feedback_to_diary(
                            crop_name=req.cropName,
                            day=req.day,
                            action_type="auto_water",
                            hp_change=auto_water_hp,
                            feedback=f"어제 {req.weatherOnThatDay}이(가) 와서 자연스럽게 수분을 받았어요!",
                            speech_bubble=f"어제 {req.weatherOnThatDay}이(가) 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚",
                            weather=req.weatherOnThatDay
                        )
                        if diary_entry:
                            crop_diary_collection.insert_one({
                                "userId": req.userId,
                                "cropName": req.cropName,
                                "day": req.day,
                                "entry": diary_entry,
                                "hpChange": auto_water_hp,
                                "actionType": "auto_water",
                                "weather": req.weatherOnThatDay,
                                "timestamp": datetime.now().isoformat()
                            })
                    except Exception as e:
                        print(f"자동 물주기 일기 저장 오류: {e}")
                    
                    return EvaluatePreviousDayResponse(
                        newHp=new_hp,
                        totalHpChange=auto_water_hp,
                        feedbacks=[f"어제 {req.weatherOnThatDay}이(가) 와서 자연스럽게 수분을 받았습니다! (+{auto_water_hp})"],
                        speechBubble=f"어제 {req.weatherOnThatDay}이(가) 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚"
                    )
                
                if should_water:
                    # 물을 줘야 하는데 주지 않았으면 방치 페널티
                    return EvaluatePreviousDayResponse(
                        newHp=max(0, req.currentHp - 3),
                        totalHpChange=-3,
                        feedbacks=[f"권장 관수 시기({watering_freq})에 물을 주지 않아 건강도가 감소했습니다... (-3)"],
                        speechBubble="저 너무 목말라요... 물을 주시면 더 건강해질 수 있을 거예요! 맑은 날에 물을 주시면 좋겠어요 💧"
                    )
                else:
                    # 아직 관수 시기가 아니면 방치 페널티 없음
                    return EvaluatePreviousDayResponse(
                        newHp=req.currentHp,
                        totalHpChange=0,
                        feedbacks=[f"권장 관수 시기({watering_freq})에 맞게 관리되고 있습니다."],
                        speechBubble="괜찮아요! 적절한 시기에 물을 주시고 있어서 건강해요! 💚"
                    )
            else:
                # watering.txt에 정보가 없을 때도 날씨 확인
                if req.weatherOnThatDay and req.weatherOnThatDay in ["비", "눈"]:
                    auto_water_hp = 2  # 자연 관수 효과
                    new_hp = min(100, req.currentHp + auto_water_hp)
                    
                    # 자동 물주기 효과를 작물일기에 기록
                    try:
                        diary_entry = convert_feedback_to_diary(
                            crop_name=req.cropName,
                            day=req.day,
                            action_type="auto_water",
                            hp_change=auto_water_hp,
                            feedback=f"어제 {req.weatherOnThatDay}이(가) 와서 자연스럽게 수분을 받았어요!",
                            speech_bubble=f"어제 {req.weatherOnThatDay}이(가) 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚",
                            weather=req.weatherOnThatDay
                        )
                        if diary_entry:
                            crop_diary_collection.insert_one({
                                "userId": req.userId,
                                "cropName": req.cropName,
                                "day": req.day,
                                "entry": diary_entry,
                                "hpChange": auto_water_hp,
                                "actionType": "auto_water",
                                "weather": req.weatherOnThatDay,
                                "timestamp": datetime.now().isoformat()
                            })
                    except Exception as e:
                        print(f"자동 물주기 일기 저장 오류: {e}")
                    
                    return EvaluatePreviousDayResponse(
                        newHp=new_hp,
                        totalHpChange=auto_water_hp,
                        feedbacks=[f"어제 {req.weatherOnThatDay}이(가) 와서 자연스럽게 수분을 받았습니다! (+{auto_water_hp})"],
                        speechBubble=f"어제 {req.weatherOnThatDay}이(가) 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚"
                    )
                # watering.txt에 정보가 없으면 기본 방치 페널티 적용
                return EvaluatePreviousDayResponse(
                    newHp=max(0, req.currentHp - 3),
                    totalHpChange=-3,
                    feedbacks=["방치로 인해 작물 건강도가 약간 감소했습니다... (-3)"],
                    speechBubble="저 너무 목말라요... 물을 주시면 더 건강해질 수 있을 거예요! 관리가 필요해요 💧"
                )
        
        total_hp_change = 0
        all_feedbacks = []
        all_speech_bubbles = []  # 각 행동의 말풍선 대사 수집
        current_hp = req.currentHp
        
        # 각 행동을 개별적으로 평가
        for action in previous_day_actions:
            action_type = action.get("type")
            # 각 행동의 날씨 정보 사용 (없으면 요청의 날씨 사용)
            action_weather = action.get("weather") or req.weatherOnThatDay
            
            # 각 행동에 대해 평가 요청 (행동 시점의 날씨 사용)
            eval_req = GameActionRequest(
                userId=req.userId,
                cropName=req.cropName,
                actionType=action_type,
                day=req.day,
                currentHp=current_hp,
                actions=req.actions,
                previousActions=req.previousActions,
                currentWeather=action_weather  # 행동 시점의 날씨 사용
            )
            
            # 평가 수행
            eval_result = evaluate_game_action(eval_req)
            
            # HP 변화 누적
            total_hp_change += eval_result.hpChange
            current_hp = eval_result.newHp
            
            # 피드백 수집
            if eval_result.feedback:
                all_feedbacks.append(eval_result.feedback)
            
            # 말풍선 대사 수집
            if eval_result.speechBubble:
                all_speech_bubbles.append(eval_result.speechBubble)
            
            # 각 행동에 대한 작물일기 저장 (행동 시점의 날씨 사용)
            try:
                diary_entry = convert_feedback_to_diary(
                    crop_name=req.cropName,
                    day=req.day,
                    action_type=action_type,
                    hp_change=eval_result.hpChange,
                    feedback=eval_result.feedback,
                    speech_bubble=eval_result.speechBubble,
                    weather=action_weather  # 행동 시점의 날씨 사용
                )
                if diary_entry:
                    crop_diary_collection.insert_one({
                        "userId": req.userId,
                        "cropName": req.cropName,
                        "day": req.day,
                        "entry": diary_entry,
                        "hpChange": eval_result.hpChange,
                        "actionType": action_type,
                        "weather": action_weather,  # 행동 시점의 날씨 저장
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                print(f"작물일기 저장 오류 (행동별): {e}")
        
        # 비/눈 날씨에 물주기 행동이 없으면 자동 물주기 효과 적용
        water_given_today = any(a.get("type") == "water" for a in previous_day_actions)
        if not water_given_today and req.weatherOnThatDay and req.weatherOnThatDay in ["비", "눈"]:
            auto_water_hp = 2  # 자연 관수 효과
            total_hp_change += auto_water_hp
            current_hp = min(100, current_hp + auto_water_hp)
            all_feedbacks.append(f"어제 {req.weatherOnThatDay}{get_josa(req.weatherOnThatDay, 'i_ga')} 와서 자연스럽게 수분을 받았습니다! (+{auto_water_hp})")
            all_speech_bubbles.append(f"어제 {req.weatherOnThatDay}{get_josa(req.weatherOnThatDay, 'i_ga')} 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚")
            
            # 자동 물주기 효과를 작물일기에 기록
            try:
                diary_entry = convert_feedback_to_diary(
                    crop_name=req.cropName,
                    day=req.day,
                    action_type="auto_water",
                    hp_change=auto_water_hp,
                    feedback=f"어제 {req.weatherOnThatDay}이(가) 와서 자연스럽게 수분을 받았어요!",
                    speech_bubble=f"어제 {req.weatherOnThatDay}이(가) 와서 촉촉해졌어요! 자연의 선물이에요! 🌧️💚",
                    weather=req.weatherOnThatDay
                )
                if diary_entry:
                    crop_diary_collection.insert_one({
                        "userId": req.userId,
                        "cropName": req.cropName,
                        "day": req.day,
                        "entry": diary_entry,
                        "hpChange": auto_water_hp,
                        "actionType": "auto_water",
                        "weather": req.weatherOnThatDay,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                print(f"자동 물주기 일기 저장 오류: {e}")
        
        # 비료 미제공 페널티 체크
        fertilizing_period = get_fertilizing_period(req.cropName)
        if fertilizing_period:
            # 비료 주기 정보에서 숫자 추출
            period_match = re.search(r"(\d+)", fertilizing_period)
            if period_match:
                expected_days = int(period_match.group(1))
                # 해당 날짜에 비료를 주었는지 확인
                fertilizer_given_today = any(a.get("type") == "fertilizer" for a in previous_day_actions)
                
                # 마지막으로 비료를 준 날짜 확인
                fertilizer_actions = [a for a in req.actions if a.get("type") == "fertilizer" and a.get("day") < req.day]
                days_since_last_fertilizer = req.day
                if fertilizer_actions:
                    last_fertilizer_day = max([a.get("day") for a in fertilizer_actions])
                    days_since_last_fertilizer = req.day - last_fertilizer_day
                
                # 비료를 줘야 하는 시기인데 주지 않았으면 페널티
                if not fertilizer_given_today and days_since_last_fertilizer >= expected_days + 2:
                    # 비료를 줘야 하는데 주지 않음 (여유 2일 포함)
                    fertilizer_penalty = -2
                    total_hp_change += fertilizer_penalty
                    current_hp = max(0, min(100, current_hp + fertilizer_penalty))
                    all_feedbacks.append(f"비료를 주는 시기({expected_days}일 후)가 지났는데 비료를 주지 않아 건강도가 감소했습니다... (-2)")
                    # 비료 부족 시 말풍선 추가
                    if not all_speech_bubbles:
                        all_speech_bubbles.append("저 너무 배고파요... 비료를 주시면 더 잘 자랄 수 있을 거예요! 영양분이 필요해요 🌿")
        
        # 최종 HP 계산
        final_hp = max(0, min(100, req.currentHp + total_hp_change))
        
        # 종합 말풍선 대사 생성 (여러 행동이 있으면 가장 중요한 것 선택)
        final_speech_bubble = None
        if all_speech_bubbles:
            # HP 변화가 가장 큰 행동의 말풍선 사용, 또는 마지막 말풍선 사용
            final_speech_bubble = all_speech_bubbles[-1]  # 마지막 행동의 말풍선
        elif total_hp_change < 0:
            # HP가 감소했는데 말풍선이 없으면 기본 메시지 (구체적인 필요사항 전달)
            # 피드백을 기반으로 구체적인 필요사항 판단
            needs_water = any("물" in f or "관수" in f or "목말라" in f for f in all_feedbacks)
            needs_fertilizer = any("비료" in f for f in all_feedbacks)
            
            if needs_water:
                final_speech_bubble = f"저 너무 목말라요... 물을 주시면 더 건강해질 수 있을 거예요! 맑은 날에 물을 주시면 좋겠어요 💧"
            elif needs_fertilizer:
                final_speech_bubble = f"저 너무 배고파요... 비료를 주시면 더 잘 자랄 수 있을 거예요! 영양분이 필요해요 🌿"
            else:
                final_speech_bubble = f"조금 힘들어요... 날씨를 확인하고 적절한 시기에 관리해주시면 좋겠어요! 🌱"
        elif total_hp_change > 0:
            final_speech_bubble = f"좋은 관리 감사해요! 이렇게 계속 챙겨주시면 더 건강해질 거예요! 💚"
        
        # 작물일기 저장 (전날 평가 결과)
        try:
            combined_feedback = " ".join(all_feedbacks) if all_feedbacks else "관리 중입니다."
            diary_entry = convert_feedback_to_diary(
                crop_name=req.cropName,
                day=req.day,
                action_type="daily_evaluation",  # 전날 평가
                hp_change=total_hp_change,
                feedback=combined_feedback,
                speech_bubble=final_speech_bubble,
                weather=req.weatherOnThatDay
            )
            if diary_entry:
                crop_diary_collection.insert_one({
                    "userId": req.userId,
                    "cropName": req.cropName,
                    "day": req.day,
                    "entry": diary_entry,
                    "hpChange": total_hp_change,
                    "actionType": "daily_evaluation",
                    "weather": req.weatherOnThatDay,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"작물일기 저장 오류 (전날 평가): {e}")
        
        return EvaluatePreviousDayResponse(
            newHp=final_hp,
            totalHpChange=total_hp_change,
            feedbacks=all_feedbacks,
            speechBubble=final_speech_bubble
        )
        
    except Exception as e:
        print(f"전날 행동 평가 오류: {e}")
        return EvaluatePreviousDayResponse(
            newHp=req.currentHp,
            totalHpChange=0,
            feedbacks=["관리 중입니다."]
        )


# 게임 상태 저장/불러오기
class GameStateRequest(BaseModel):
    userId: str
    state: dict


@app.post("/game/state")
def save_game_state(req: GameStateRequest):
    """게임 상태 저장 (단일 작물 - 하위 호환성)"""
    from datetime import datetime
    games_collection.update_one(
        {"userId": req.userId},
        {"$set": {"userId": req.userId, "state": req.state, "updatedAt": datetime.now().isoformat()}},
        upsert=True
    )
    return {"ok": True}


class CropData(BaseModel):
    cropName: str
    hp: int = 100
    day: int = 0
    gameStartTime: Optional[str] = None
    lastUpdateTime: Optional[str] = None
    currentWeather: Optional[str] = None
    weatherDate: Optional[int] = None


class SaveCropRequest(BaseModel):
    userId: str
    crop: CropData


@app.post("/game/crop")
def save_crop(req: SaveCropRequest):
    """특정 작물 저장 (여러 작물 지원)"""
    from datetime import datetime
    
    # 사용자의 기존 작물 목록 가져오기
    game_doc = games_collection.find_one({"userId": req.userId})
    
    if game_doc and game_doc.get("crops"):
        crops = game_doc["crops"]
    else:
        crops = []
    
    # 동일한 작물이 있으면 업데이트, 없으면 추가
    crop_dict = req.crop.dict()
    crop_dict["lastUpdateTime"] = datetime.now().isoformat()
    
    existing_index = next((i for i, c in enumerate(crops) if c.get("cropName") == req.crop.cropName), None)
    
    if existing_index is not None:
        crops[existing_index] = crop_dict
    else:
        if len(crops) >= 2:
            return {"ok": False, "message": "최대 2개의 작물만 키울 수 있습니다."}
        crops.append(crop_dict)
    
    games_collection.update_one(
        {"userId": req.userId},
        {"$set": {"userId": req.userId, "crops": crops, "updatedAt": datetime.now().isoformat()}},
        upsert=True
    )
    return {"ok": True}


@app.delete("/game/crop/{user_id}/{crop_name}")
def delete_crop(user_id: str, crop_name: str):
    """작물 삭제"""
    from datetime import datetime
    
    game_doc = games_collection.find_one({"userId": user_id})
    
    if not game_doc:
        return {"ok": False, "message": "작물을 찾을 수 없습니다."}
    
    update_data = {"updatedAt": datetime.now().isoformat()}
    
    # crops 배열에서 해당 작물 제거
    if game_doc.get("crops"):
        crops = game_doc["crops"]
        crops = [c for c in crops if c.get("cropName") != crop_name]
        update_data["crops"] = crops
    
    # 기존 state에서도 해당 작물 제거 (하위 호환성)
    if game_doc.get("state") and game_doc["state"].get("cropName") == crop_name:
        update_data["state"] = None  # 기존 state 초기화
    
    games_collection.update_one(
        {"userId": user_id},
        {"$set": update_data}
    )
    
    return {"ok": True}


@app.get("/game/state/{user_id}")
def get_game_state(user_id: str):
    """게임 상태 불러오기 (단일 작물 - 하위 호환성)"""
    game_doc = games_collection.find_one({"userId": user_id}, {"_id": False})
    if game_doc and game_doc.get("state"):
        return {"state": game_doc["state"]}
    return {"state": None}


@app.get("/game/crop-guide/{crop_name}")
def get_crop_guide(crop_name: str):
    """작물 관리 가이드 가져오기 (물주기/비료 주기 정보 포함)"""
    try:
        guide_text = get_crop_guide_for_game(crop_name)
        
        # 물주기 정보 가져오기 (모든 구간)
        watering_info = {}
        # 각 구간의 물주기 정보를 가져오기 위해 임시로 day 값 사용
        freq_0_10 = get_watering_frequency(crop_name, 5)  # 0~10일 구간
        freq_10_35 = get_watering_frequency(crop_name, 20)  # 10~35일 구간
        freq_35_plus = get_watering_frequency(crop_name, 50)  # 35일 이후
        
        if freq_0_10:
            watering_info["0~10일"] = freq_0_10
        if freq_10_35:
            watering_info["10~35일"] = freq_10_35
        if freq_35_plus:
            watering_info["35+"] = freq_35_plus
        
        # 비료 주기 정보
        fertilizing_period = get_fertilizing_period(crop_name)
        
        return {
            "guide": guide_text,
            "watering_info": watering_info,
            "fertilizing_period": fertilizing_period
        }
    except Exception as e:
        print(f"작물 가이드 가져오기 오류: {e}")
        return {
            "guide": f"{crop_name} 작물의 가이드라인을 찾을 수 없습니다.",
            "watering_info": {},
            "fertilizing_period": None
        }


@app.get("/game/crops/{user_id}")
def get_user_crops(user_id: str):
    """사용자가 키우고 있는 모든 작물 목록 불러오기"""
    game_doc = games_collection.find_one({"userId": user_id}, {"_id": False})
    if not game_doc:
        return {"crops": []}
    
    # 새로운 구조 (crops 배열) 확인
    if game_doc.get("crops") and isinstance(game_doc["crops"], list):
        return {"crops": game_doc["crops"]}
    
    # 기존 구조 (단일 state)가 있으면 변환
    if game_doc.get("state") and game_doc["state"].get("cropName"):
        old_state = game_doc["state"]
        crop = {
            "cropName": old_state.get("cropName", ""),
            "hp": old_state.get("hp", 100),
            "day": old_state.get("day", 0),
            "gameStartTime": old_state.get("gameStartTime"),
            "lastUpdateTime": old_state.get("lastUpdateTime"),
            "currentWeather": old_state.get("currentWeather"),
            "weatherDate": old_state.get("weatherDate")
        }
        return {"crops": [crop]}
    
    return {"crops": []}


# 수확 피드백
harvest_system_template = """
당신은 농업 다마고치 게임의 수확 피드백 시스템입니다.

작물 가이드라인:
{crop_guide}

게임 결과:
- 최종 HP: {final_hp}/100
- 총 재배 일수: {total_days}일
- 수행한 행동 수: {action_count}개

작물을 키우는 과정을 평가하고, 수확 전날의 피드백을 작성하세요.

규칙:
1. 수확 등급(S, A, B, C, D)에 따라 성공/실패를 판단
2. 가이드라인을 얼마나 잘 따랐는지 평가
3. 친근하고 다마고치 캐릭터처럼 대답
4. 한 문단 정도의 피드백 작성

응답 형식:
{{
    "message": "수확 전날 피드백 메시지 (2-3문장)"
}}
"""

harvest_prompt = ChatPromptTemplate.from_messages([
    ("system", harvest_system_template),
    ("human", "수확 전날 피드백을 작성해주세요.")
])


class HarvestFeedbackRequest(BaseModel):
    userId: str
    cropName: str
    finalHp: int
    totalDays: int
    actions: List[dict]


class HarvestFeedbackResponse(BaseModel):
    message: str
    success: bool


@app.post("/game/harvest-feedback", response_model=HarvestFeedbackResponse)
def get_harvest_feedback(req: HarvestFeedbackRequest):
    """수확 전날 피드백 생성 (growing_period.txt 기반)"""
    try:
        # 수확 시기 확인
        harvest_period = get_growing_period(req.cropName)
        
        crop_guide = get_crop_guide_for_game(req.cropName)
        
        # 수확 시기 정보 추가
        period_info = ""
        if harvest_period:
            min_harvest_day, optimal_harvest_day = harvest_period
            period_info = f"\n수확 가능 시기: {min_harvest_day}일부터\n최적 수확 시기: {optimal_harvest_day}일"
            if req.totalDays < min_harvest_day:
                period_info += f"\n⚠️ 주의: 아직 수확 가능 시기가 아닙니다. (최소 {min_harvest_day}일 필요)"
            elif req.totalDays >= optimal_harvest_day:
                period_info += f"\n✅ 최적 수확 시기입니다!"
            else:
                remaining_days = optimal_harvest_day - req.totalDays
                period_info += f"\n💡 최적 수확 시기까지 약 {remaining_days}일 남았습니다."
        
        chain = harvest_prompt | llm
        result = chain.invoke({
            "crop_guide": crop_guide + period_info,
            "final_hp": req.finalHp,
            "total_days": req.totalDays,
            "action_count": len(req.actions)
        })
        
        # JSON 파싱 시도
        import json
        response_text = result.content if hasattr(result, "content") else str(result)
        json_match = re.search(r'\{[^{}]*"message"[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            eval_result = json.loads(json_match.group())
            message = eval_result.get("message", "수확하세요!")
        else:
            message = response_text[:200] if response_text else "수확하세요!"
        
        # 등급 기반 성공/실패 판단
        grade = calculate_grade(req.finalHp, req.totalDays, harvest_period)
        # C 등급 이상이면 성공, D, F 등급이면 실패
        success = grade not in ["D", "F"]
        
        if harvest_period and req.totalDays < harvest_period[0]:
            # 최소 수확일 미만이면 F등급
            message += f" (아직 수확 시기가 아닙니다. 최소 {harvest_period[0]}일 권장)"
        
        return HarvestFeedbackResponse(
            message=message,
            success=success
        )
        
    except Exception as e:
        print(f"수확 피드백 오류: {e}")
        # 예외 처리 시에도 등급 기반 판단
        harvest_period = get_growing_period(req.cropName) if 'req' in locals() else None
        grade = calculate_grade(req.finalHp, req.totalDays, harvest_period) if 'req' in locals() else "D"
        success = grade != "D"
        return HarvestFeedbackResponse(
            message=f"수확 준비가 되었습니다! 최종 건강도: {req.finalHp}/100",
            success=success
        )


# =========================================================
# 11. 작물 도감 관련 API
# =========================================================

class CollectionEntry(BaseModel):
    cropName: str
    finalHp: int
    totalDays: int
    harvestedAt: str
    grade: str  # S, A, B, C 등급


class AddToCollectionRequest(BaseModel):
    userId: str
    cropName: str
    finalHp: int
    totalDays: int


class AddToCollectionResponse(BaseModel):
    success: bool
    message: str
    grade: str
    collectionCount: int  # 해당 작물 도감 등록 횟수


class CollectionResponse(BaseModel):
    collection: List[dict]


def calculate_grade(final_hp: int, total_days: int, harvest_period: Optional[Tuple[int, int]]) -> str:
    """수확 결과에 따른 등급 계산
    Args:
        final_hp: 최종 HP (0-100)
        total_days: 총 재배 일수
        harvest_period: (최소 수확일, 최적 수확일) 튜플
    Returns:
        등급 (S, A, B, C, D, F)
    """
    # 최소 수확일 미만이면 무조건 F등급
    if harvest_period:
        min_harvest_day, optimal_harvest_day = harvest_period
        if total_days < min_harvest_day:
            return "F"
    
    # HP 기반 점수 (0-50점)
    hp_score = final_hp * 0.5
    
    # 수확 시기 기반 점수 (0-50점)
    period_score = 0
    if harvest_period:
        min_harvest_day, optimal_harvest_day = harvest_period
        
        # 최적 수확일에 가까울수록 높은 점수
        if total_days >= optimal_harvest_day:
            # 최적 수확일 이상이면 만점
            period_score = 50
        else:
            # 최소 수확일 ~ 최적 수확일 사이: 비율에 따라 점수 부여
            # 최소일에서 최적일까지의 비율 계산 (0.0 ~ 1.0)
            progress_ratio = (total_days - min_harvest_day) / (optimal_harvest_day - min_harvest_day)
            # 비율에 따라 0~50점 사이 점수 부여 (선형 보간)
            period_score = int(progress_ratio * 50)
    else:
        # 재배 기간 정보가 없으면 기본 점수
        period_score = 25
    
    total_score = hp_score + period_score
    
    # 등급 결정
    if total_score >= 90:
        return "S"
    elif total_score >= 80:
        return "A"
    elif total_score >= 70:
        return "B"
    elif total_score >= 60:
        return "C"
    else:
        return "D"


@app.post("/game/collection/add", response_model=AddToCollectionResponse)
def add_to_collection(req: AddToCollectionRequest):
    """수확한 작물을 도감에 추가"""
    try:
        # 수확 시기 확인
        harvest_period = get_growing_period(req.cropName)
        
        # 등급 계산
        grade = calculate_grade(req.finalHp, req.totalDays, harvest_period)
        
        # 도감에 추가
        entry = {
            "userId": req.userId,
            "cropName": req.cropName,
            "finalHp": req.finalHp,
            "totalDays": req.totalDays,
            "harvestedAt": datetime.now().isoformat(),
            "grade": grade,
            "harvestPeriod": harvest_period,  # (최소 수확일, 최적 수확일)
            "growingPeriod": harvest_period[1] if harvest_period else None  # 최적 수확일 (하위 호환성)
        }
        
        crop_collection_db.insert_one(entry)
        
        # 해당 작물의 도감 등록 횟수 조회
        collection_count = crop_collection_db.count_documents({
            "userId": req.userId,
            "cropName": req.cropName
        })
        
        # 등급별 메시지
        grade_messages = {
            "S": f"🏆 완벽한 수확이에요! {req.cropName}을(를) S등급으로 도감에 등록했습니다!",
            "A": f"🥇 훌륭해요! {req.cropName}을(를) A등급으로 도감에 등록했습니다!",
            "B": f"🥈 잘하셨어요! {req.cropName}을(를) B등급으로 도감에 등록했습니다!",
            "C": f"🥉 좋아요! {req.cropName}을(를) C등급으로 도감에 등록했습니다!",
            "D": f"📝 {req.cropName}을(를) D등급으로 도감에 등록했습니다. 다음엔 더 잘 키워보세요!",
            "F": f"⚠️ {req.cropName}을(를) F등급으로 도감에 등록했습니다. 아직 수확 시기가 아니었지만 기록으로 남겼습니다. 다음엔 더 오래 키워보세요!"
        }
        
        message = grade_messages.get(grade, f"{req.cropName}을(를) 도감에 등록했습니다!")
        
        print(f"✅ 도감 등록: {req.userId} - {req.cropName} (등급: {grade}, {collection_count}번째)")
        
        return AddToCollectionResponse(
            success=True,
            message=message,
            grade=grade,
            collectionCount=collection_count
        )
        
    except Exception as e:
        print(f"도감 등록 오류: {e}")
        return AddToCollectionResponse(
            success=False,
            message="도감 등록에 실패했습니다.",
            grade="",
            collectionCount=0
        )


@app.get("/game/collection/{user_id}", response_model=CollectionResponse)
def get_collection(user_id: str):
    """사용자의 작물 도감 조회"""
    try:
        entries = list(crop_collection_db.find(
            {"userId": user_id},
            {"_id": False}
        ).sort("harvestedAt", -1))  # 최신순 정렬
        
        return CollectionResponse(collection=entries)
    except Exception as e:
        print(f"도감 조회 오류: {e}")
        return CollectionResponse(collection=[])


@app.get("/game/collection/{user_id}/summary")
def get_collection_summary(user_id: str):
    """사용자의 도감 요약 정보 (작물별 통계)"""
    try:
        # 작물별 최고 등급 및 수확 횟수 집계
        pipeline = [
            {"$match": {"userId": user_id}},
            {"$group": {
                "_id": "$cropName",
                "count": {"$sum": 1},
                "bestGrade": {"$min": "$grade"},  # 등급이 알파벳순이므로 min이 최고
                "bestHp": {"$max": "$finalHp"},
                "latestHarvest": {"$max": "$harvestedAt"}
            }},
            {"$sort": {"latestHarvest": -1}}
        ]
        
        results = list(crop_collection_db.aggregate(pipeline))
        
        # 전체 통계
        total_count = crop_collection_db.count_documents({"userId": user_id})
        unique_crops = len(results)
        
        return {
            "totalHarvests": total_count,
            "uniqueCrops": unique_crops,
            "crops": [{
                "cropName": r["_id"],
                "harvestCount": r["count"],
                "bestGrade": r["bestGrade"],
                "bestHp": r["bestHp"],
                "latestHarvest": r["latestHarvest"]
            } for r in results]
        }
    except Exception as e:
        print(f"도감 요약 조회 오류: {e}")
        return {
            "totalHarvests": 0,
            "uniqueCrops": 0,
            "crops": []
        }


@app.post("/game/harvest-and-collect")
def harvest_and_add_to_collection(req: AddToCollectionRequest):
    """수확하고 도감에 추가한 후 작물 삭제"""
    try:
        # 1. 도감에 추가
        collection_result = add_to_collection(req)
        
        if not collection_result.success:
            return {
                "success": False,
                "message": "도감 등록에 실패했습니다."
            }
        
        # 2. 작물 삭제 (crops 배열에서)
        game_doc = games_collection.find_one({"userId": req.userId})
        
        update_data = {"updatedAt": datetime.now().isoformat()}
        
        if game_doc:
            # crops 배열에서 해당 작물 제거
            if game_doc.get("crops"):
                crops = game_doc["crops"]
                crops = [c for c in crops if c.get("cropName") != req.cropName]
                update_data["crops"] = crops
            
            # 기존 state에서도 해당 작물 제거 (하위 호환성)
            if game_doc.get("state") and game_doc["state"].get("cropName") == req.cropName:
                update_data["state"] = None  # 기존 state 초기화
            
            games_collection.update_one(
                {"userId": req.userId},
                {"$set": update_data}
            )
            
            print(f"✅ 작물 삭제 완료: {req.userId} - {req.cropName}")
        
        # 3. 작물일기도 삭제 (선택적 - 도감에 기록이 남으므로)
        # crop_diary_collection.delete_many({"userId": req.userId, "cropName": req.cropName})
        
        return {
            "success": True,
            "message": collection_result.message,
            "grade": collection_result.grade,
            "collectionCount": collection_result.collectionCount
        }
        
    except Exception as e:
        print(f"수확 및 도감 등록 오류: {e}")
        return {
            "success": False,
            "message": "수확 처리 중 오류가 발생했습니다."
        }
