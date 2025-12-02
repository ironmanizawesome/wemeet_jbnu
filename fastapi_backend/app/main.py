# app/main.py
import os
import re
import hashlib
import json
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from .recommendation import CropRecommendationService
from .game_service import get_crop_guide_for_game
from .game_service import get_crop_guide_for_game


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
games_collection = db["games"]  # 게임 상태 저장
chat_responses_collection = db["chat_responses"]  # 챗봇 응답 캐시

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
# 10. 게임 관련 API
# =========================================================

# 게임 판단을 위한 시스템 프롬프트
game_system_template = """
당신은 농업 다마고치 게임의 판단 시스템입니다.

작물 가이드라인:
{crop_guide}

사용자가 수행한 행동:
- 행동 유형: {action_type}
- 현재 재배 일수: {day}일
- 현재 HP: {current_hp}/100
- 최근 행동 이력: {recent_actions}

작물 가이드라인을 기준으로 사용자의 행동을 평가하세요.

규칙:
1. 가이드라인에 맞는 행동이면 HP가 증가 (최대 +5)
2. 가이드라인과 약간 다르면 HP 유지 또는 소폭 감소 (-1~-3)
3. 가이드라인과 많이 다르면 HP 감소 (-5~-10)
4. 과도한 행동(예: 하루에 여러 번 물주기)이면 HP 감소
5. 작물에 맞지 않는 행동이면 HP 감소

응답 형식 (JSON):
{{
    "hp_change": 숫자 (-10 ~ +5),
    "feedback": "한 문장 피드백 메시지 (친근하고 다마고치처럼)"
}}

예시:
- 좋은 경우: "적절한 물주기! 작물이 건강해졌어요! (+3)"
- 나쁜 경우: "물을 너무 많이 줬어요. 뿌리가 썩을 수 있어요! (-5)"
- 중간: "괜찮아요. 조금 더 관심을 기울여보세요! (0)"
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
    """날짜 진행 시 병해충 발생 여부를 확률 기반으로 체크"""
    import random
    
    try:
        # 기본 병해충 발생 확률 (5%)
        base_probability = 0.05
        
        # 관리 상태 평가 (최근 3일간의 행동)
        recent_actions = [a for a in req.actions if a.get("day", 0) >= req.day - 3]
        water_count = sum(1 for a in recent_actions if a.get("type") == "water")
        fertilizer_count = sum(1 for a in recent_actions if a.get("type") == "fertilizer")
        pesticide_count = sum(1 for a in recent_actions if a.get("type") == "pesticide")
        
        # 관리 상태에 따른 확률 조정
        management_score = 0
        if water_count > 0:
            management_score += 1
        if fertilizer_count > 0:
            management_score += 1
        if pesticide_count > 0:
            management_score += 1
        
        # 관리가 잘 되었으면 확률 감소, 못했으면 증가
        if management_score >= 2:
            # 잘 관리됨: 확률 50% 감소
            base_probability *= 0.5
        elif management_score == 0:
            # 관리 안됨: 확률 200% 증가
            base_probability *= 3.0
        elif management_score == 1:
            # 부분 관리: 확률 50% 증가
            base_probability *= 1.5
        
        # 기상 조건에 따른 확률 조정
        weather_multiplier = 1.0
        pest_type = None
        
        if req.currentWeather:
            if req.currentWeather in ["비", "천둥"]:
                # 습도 관련 병해충 확률 증가 (흰가루병, 역병 등)
                weather_multiplier = 2.0
                pest_type = random.choice(["흰가루병", "역병", "노균병"])
            elif req.currentWeather == "맑음" and random.random() < 0.3:
                # 건조 관련 병해충 (진딧물, 응애 등)
                weather_multiplier = 1.5
                pest_type = random.choice(["진딧물", "응애", "총채벌레"])
            elif req.currentWeather == "흐림":
                # 습도가 높은 경우
                weather_multiplier = 1.3
                pest_type = random.choice(["흰가루병", "잎마름병"])
        
        # 최종 확률 계산
        final_probability = min(0.5, base_probability * weather_multiplier)  # 최대 50%
        
        # 병해충 발생 여부 결정
        pest_occurred = random.random() < final_probability
        
        if pest_occurred:
            # 병해충 종류 결정
            if not pest_type:
                pest_type = random.choice([
                    "진딧물", "응애", "배추흰나비 애벌레", "좀나방 애벌레",
                    "흰가루병", "역병", "노균병", "탄저병", "잎마름병"
                ])
            
            # HP 감소량 결정 (관리 상태에 따라)
            if management_score >= 2:
                hp_loss = random.randint(3, 5)  # 잘 관리됨: 적은 피해
            elif management_score == 1:
                hp_loss = random.randint(5, 8)  # 부분 관리: 중간 피해
            else:
                hp_loss = random.randint(8, 15)  # 관리 안됨: 큰 피해
            
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
    """작물 관리 행동을 평가하고 HP를 계산"""
    try:
        # 날씨 조건 체크: 습한 날씨(비, 눈)에 물을 주면 과습으로 판단
        weather_penalty = 0
        weather_feedback = ""
        
        if req.actionType == "water" and req.currentWeather:
            # 습한 날씨에 물을 주는 경우
            if req.currentWeather in ["비", "눈", "천둥"]:
                weather_penalty = -8  # 과습으로 인한 HP 감소
                weather_feedback = f"⚠️ {req.currentWeather} 날씨에 물을 주면 과습이 될 수 있어요! 뿌리가 썩을 수 있습니다. (-8)"
            elif req.currentWeather == "흐림":
                # 흐린 날씨에도 약간의 페널티
                weather_penalty = -3
                weather_feedback = f"흐린 날씨에 물을 주는 것은 조금 위험할 수 있어요. (-3)"
        
        # 작물 가이드라인 가져오기
        crop_guide = get_crop_guide_for_game(req.cropName)
        
        # 최근 행동 요약
        recent_summary = ""
        if req.previousActions:
            water_count = sum(1 for a in req.previousActions if a.get("type") == "water")
            fert_count = sum(1 for a in req.previousActions if a.get("type") == "fertilizer")
            pest_count = sum(1 for a in req.previousActions if a.get("type") == "pesticide")
            recent_summary = f"최근 {len(req.previousActions)}일간 - 물주기: {water_count}회, 비료: {fert_count}회, 농약살포: {pest_count}회"
        else:
            recent_summary = "첫 관리입니다."
        
        # 날씨 정보를 가이드라인에 추가
        weather_info = ""
        if req.currentWeather:
            weather_info = f"\n현재 날씨: {req.currentWeather}"
            if req.actionType == "water" and req.currentWeather in ["비", "눈", "천둥"]:
                weather_info += "\n⚠️ 주의: 습한 날씨에 물을 주면 과습이 될 수 있습니다."
        
        # 행동 유형 한국어 변환
        action_kr = {
            "water": "물주기",
            "fertilizer": "비료주기",
            "pesticide": "농약살포"
        }.get(req.actionType, req.actionType)
        
        # AI 판단
        chain = game_prompt | llm
        result = chain.invoke({
            "crop_guide": crop_guide + weather_info,
            "action_type": action_kr,
            "day": req.day,
            "current_hp": req.currentHp,
            "recent_actions": recent_summary
        })
        
        # JSON 응답 파싱 시도
        import json
        try:
            # JSON 형식으로 응답이 오는 경우
            response_text = result.content if hasattr(result, "content") else str(result)
            # JSON 블록 찾기
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                eval_result = json.loads(json_match.group())
                hp_change = int(eval_result.get("hp_change", 0))
                feedback = eval_result.get("feedback", "관리 중입니다.")
            else:
                # JSON이 아니면 기본값
                hp_change = 0
                feedback = response_text[:100] if response_text else "관리 중입니다."
        except:
            # 파싱 실패 시 기본값
            hp_change = 0
            feedback = "관리 중입니다."
        
        # 날씨 페널티 적용
        if weather_penalty != 0:
            hp_change += weather_penalty
            # 날씨 피드백이 있으면 우선 표시
            if weather_feedback:
                feedback = weather_feedback
        
        # HP 계산
        new_hp = max(0, min(100, req.currentHp + hp_change))
        
        return GameEvaluateResponse(
            newHp=new_hp,
            hpChange=hp_change,
            feedback=feedback
        )
        
    except Exception as e:
        print(f"게임 평가 오류: {e}")
        # 오류 시 기본값 반환
        return GameEvaluateResponse(
            newHp=req.currentHp,
            hpChange=0,
            feedback="관리 중입니다."
        )


# 전날 행동들을 일괄 평가하는 요청 모델
class EvaluatePreviousDayRequest(BaseModel):
    userId: str
    cropName: str
    day: int  # 평가할 날짜 (전날)
    currentHp: int
    actions: List[dict]  # 전날의 행동들
    previousActions: Optional[List[dict]] = None  # 그 이전 행동들
    weatherOnThatDay: Optional[str] = None  # 그 날의 날씨


# 전날 행동 평가 응답 모델
class EvaluatePreviousDayResponse(BaseModel):
    newHp: int
    totalHpChange: int
    feedbacks: List[str]  # 각 행동에 대한 피드백들


@app.post("/game/evaluate-previous-day", response_model=EvaluatePreviousDayResponse)
def evaluate_previous_day_actions(req: EvaluatePreviousDayRequest):
    """전날의 행동들을 일괄 평가하고 HP 변화를 계산"""
    try:
        # 전날의 행동들 필터링
        previous_day_actions = [a for a in req.actions if a.get("day") == req.day]
        
        if not previous_day_actions:
            # 전날 행동이 없으면 방치 페널티만 적용
            return EvaluatePreviousDayResponse(
                newHp=max(0, req.currentHp - 3),
                totalHpChange=-3,
                feedbacks=["방치로 인해 작물 건강도가 약간 감소했습니다... (-3)"]
            )
        
        total_hp_change = 0
        all_feedbacks = []
        current_hp = req.currentHp
        
        # 각 행동을 개별적으로 평가
        for action in previous_day_actions:
            action_type = action.get("type")
            # 각 행동의 날씨 정보 사용 (없으면 요청의 날씨 사용)
            action_weather = action.get("weather") or req.weatherOnThatDay
            
            # 각 행동에 대해 평가 요청
            eval_req = GameActionRequest(
                userId=req.userId,
                cropName=req.cropName,
                actionType=action_type,
                day=req.day,
                currentHp=current_hp,
                actions=req.actions,
                previousActions=req.previousActions,
                currentWeather=action_weather
            )
            
            # 평가 수행
            eval_result = evaluate_game_action(eval_req)
            
            # HP 변화 누적
            total_hp_change += eval_result.hpChange
            current_hp = eval_result.newHp
            
            # 피드백 수집
            if eval_result.feedback:
                all_feedbacks.append(eval_result.feedback)
        
        # 최종 HP 계산
        final_hp = max(0, min(100, req.currentHp + total_hp_change))
        
        return EvaluatePreviousDayResponse(
            newHp=final_hp,
            totalHpChange=total_hp_change,
            feedbacks=all_feedbacks
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
    
    if not game_doc or not game_doc.get("crops"):
        return {"ok": False, "message": "작물을 찾을 수 없습니다."}
    
    crops = game_doc["crops"]
    crops = [c for c in crops if c.get("cropName") != crop_name]
    
    games_collection.update_one(
        {"userId": user_id},
        {"$set": {"crops": crops, "updatedAt": datetime.now().isoformat()}}
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
    """작물 관리 가이드 가져오기"""
    try:
        guide_text = get_crop_guide_for_game(crop_name)
        return {"guide": guide_text}
    except Exception as e:
        print(f"작물 가이드 가져오기 오류: {e}")
        return {"guide": f"{crop_name} 작물의 가이드라인을 찾을 수 없습니다."}


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
1. HP가 70 이상이면 성공적으로 키운 것으로 판단
2. HP가 70 미만이면 실패로 판단
3. 가이드라인을 얼마나 잘 따랐는지 평가
4. 친근하고 다마고치 캐릭터처럼 대답
5. 한 문단 정도의 피드백 작성

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
    """수확 전날 피드백 생성"""
    try:
        crop_guide = get_crop_guide_for_game(req.cropName)
        
        chain = harvest_prompt | llm
        result = chain.invoke({
            "crop_guide": crop_guide,
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
        
        success = req.finalHp >= 70
        
        return HarvestFeedbackResponse(
            message=message,
            success=success
        )
        
    except Exception as e:
        print(f"수확 피드백 오류: {e}")
        return HarvestFeedbackResponse(
            message=f"수확 준비가 되었습니다! 최종 건강도: {req.finalHp}/100",
            success=req.finalHp >= 70
        )
