from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend_fastapi.basic_agent import langchain_basic_agent_example

app = FastAPI()

# CORS(교차 출처 리소스 공유) 설정
# - 개발 단계에서는 간단히 모두 허용("*")으로 해두면
#   다른 포트/도메인의 프론트엔드 페이지에서도 이 API를 호출할 수 있습니다.
# - 쿠키/세션(자격 증명)을 쓰는 경우엔 allow_credentials=True로 바꾸고,
#   allow_origins에 구체적인 주소 목록(예: "http://localhost:5500")을 넣어주세요.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 개발용: 모든 출처 허용
    allow_credentials=False,    # 자격 증명(쿠키 등) 미사용
    allow_methods=["*"],       # 모든 HTTP 메서드 허용 (GET, POST 등)
    allow_headers=["*"],       # 모든 헤더 허용
)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "query": q}


@app.get("/langchain_basic_agent/{thread_id}/{user_message}")
def get_langchain_basic_agent_example(thread_id: str, user_message: str):
    return {"response": langchain_basic_agent_example(thread_id, user_message)}