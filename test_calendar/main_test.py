from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date, timedelta
import uuid

app = FastAPI(title="귀농 청년 일정 API", version="0.1.0")

# CORS (프론트와 같은 호스트면 기본값으로도 충분하지만, 개발 편의상 와일드카드)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# ====== 모델 ======
class Task(BaseModel):
    name: str
    stage: str
    due_date: date
    checklist: List[str] = []
    notes: Optional[str] = None

class PlanCreate(BaseModel):
    crop: str
    start_date: date
    method: str = Field(pattern="^(seed|transplant|grafting)$")
    environment: str = Field(pattern="^(open|greenhouse|hydroponic)$")
    area: Optional[float] = None
    variety: Optional[str] = None
    notes: Optional[str] = None

class Plan(PlanCreate):
    id: str
    tasks: List[Task]

class Observation(BaseModel):
    date: date
    task_name: str
    symptom: str = ""
    severity: int = Field(2, ge=1, le=3)
    note: Optional[str] = None

class ObservationResult(BaseModel):
    ok: bool
    feedback: str

# ====== 저장(데모: 인메모리) ======
DB: Dict[str, Plan] = {}

# ====== 규칙: 일정 생성 ======
def env_factor(environment: str) -> float:
    return {"open": 1.0, "greenhouse": 0.9, "hydroponic": 0.8}.get(environment, 1.0)

def make_plan(p: PlanCreate) -> Plan:
    ef = env_factor(p.environment)

    def dd(days: int) -> date:
        return p.start_date + timedelta(days=round(days * ef))

    tasks: List[Task] = []

    # 공통 선행
    tasks.append(Task(
        name="정식 준비/점검", stage="transplant", due_date=dd(-2),
        checklist=["토양/배지 수분", "관수라인 EC/pH", "도구 소독"]
    ))
    # 정식/파종
    tasks.append(Task(
        name=("파종" if p.method == "seed" else "정식"),
        stage="transplant", due_date=dd(0),
        checklist=["식재밀도 준수", "묘 활력 확인"]
    ))
    # 단계별 주요 관리
    tasks.append(Task(name="활착 관리", stage="establish", due_date=dd(5),
                      checklist=["고온/건조 시 차광", "토양수분 유지", "초기 병해 관찰"]))
    tasks.append(Task(name="추가 유인/적심", stage="veg", due_date=dd(24),
                      checklist=["주지 유인", "곁순 정리"]))
    tasks.append(Task(name="추비/관주", stage="veg", due_date=dd(28),
                      checklist=["EC/pH 점검", "질소 과다 주의"]))
    tasks.append(Task(name="개화/수분 관리", stage="flower", due_date=dd(42),
                      checklist=["수분 보조(필요시)", "개화기 방제"]))
    tasks.append(Task(name="병해충 방제", stage="flower", due_date=dd(48),
                      checklist=["총채/진딧물 예찰", "끈끈이트랩 교체"]))
    tasks.append(Task(name="예상 첫 수확", stage="harvest", due_date=dd(70),
                      checklist=["표준 수확 지표 확인", "품질 관리"]))

    # 환경별 보정 작업 예시
    if p.environment == "greenhouse":
        tasks.append(Task(name="환기/습도 관리", stage="veg", due_date=dd(20),
                          checklist=["야간 결로 방지", "차광커튼 점검"]))
    if p.environment == "hydroponic":
        tasks.append(Task(name="배양액 점검", stage="veg", due_date=dd(18),
                          checklist=["EC/pH/온도 확인", "배액률 모니터링"]))

    return Plan(id=str(uuid.uuid4())[:8], **p.dict(), tasks=sorted(tasks, key=lambda t: t.due_date))

# ====== 규칙: 관찰 → 피드백 ======
def feedback_rule(plan: Plan, obs: Observation) -> str:
    s = (obs.symptom or "").lower()
    env = plan.environment

    if any(k in s for k in ["총채", "진딧", "응애", "가루이", "해충", "벌레"]):
        if env == "greenhouse":
            return "시설 해충 예찰 강화: 끈끈이트랩 밀도↑, 출입구 이중문/방충망 점검, 생물적 방제(포식성 곤충) 검토."
        return "해충 잔재물 제거·주변 잡초 관리, 방충망 점검. 필요 시 등록약제 국소 처리."
    if any(k in s for k in ["흰가루", "곰팡", "잎곰팡", "균핵"]):
        return "고습성 병 징후: 환기 주기 조정, 밀식 완화, 유황계/동제 또는 등록약제 예방 살포 고려."
    if any(k in s for k in ["황화", "엽황", "잎 노랗", "yellow"]):
        return "영양 불균형 가능: EC/pH·배액률 점검 후 관주 비율 재설정. 철·질소 결핍 여부 확인."
    if obs.severity >= 3:
        return "심각 단계: 해당 구역 격리·도구 소독·전파 차단 우선. SOP에 따라 즉시 조치 및 재관찰 24~48h 내 수행."
    return "관찰 저장됨. 2~3일 후 재관찰하여 추세 확인 권장."

# ====== 엔드포인트 ======
@app.post("/api/plans", response_model=Plan)
def create_plan(p: PlanCreate):
  plan = make_plan(p)
  DB[plan.id] = plan
  return plan

@app.get("/api/plans/{plan_id}", response_model=Plan)
def get_plan(plan_id: str):
  return DB[plan_id]

@app.post("/api/plans/{plan_id}/observations", response_model=ObservationResult)
def add_observation(plan_id: str, obs: Observation):
  plan = DB.get(plan_id)
  if not plan:
    return ObservationResult(ok=False, feedback="플랜을 찾을 수 없습니다.")
  fb = feedback_rule(plan, obs)
  # (데모) 여기서 관찰을 DB에 저장하거나, 위험 점수 업데이트 등을 수행 가능
  return ObservationResult(ok=True, feedback=fb)

# ---- 개발 편의용 루트 ----
@app.get("/")
def root():
  return {"ok": True, "msg": "농사일정 관리 API"}
