"""
초보자용: "도구 호출(툴 콜)"을 사용하는 예제

무엇을 하나요?
- 에이전트가 파이썬 함수(툴)를 직접 호출해서 정보를 얻거나 계산을 합니다.
- 여기서는 두 가지 툴을 제공합니다:
  1) cafe_info(name): 카페 정보 조회
  2) multiply(a, b): 두 수를 곱하기

또한 InMemorySaver로 대화를 이어서 할 수 있습니다.

주의(보안): API 키는 코드에 하드코딩하지 말고 환경변수를 이용하세요.
"""

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
import os

# Expect API key to be provided via environment; do not hardcode secrets
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Set OPENAI_API_KEY in your environment before running this example.")


# 1) 에이전트가 사용할 "도구(파이썬 함수)" 정의
def cafe_info(name: str) -> str:
    """카페 이름으로 간단한 정보를 반환합니다."""
    cafe_info_dict = {
        "오스스퀘어": "오스스퀘어는 전북대학교 삼성문화회관에 위치한 카페입니다. 영업시간은 08:00~220:00입니다. 아메리카노는 5천원입니다.",
        "FA": "FA는 덕진구 들사평1길 44에 위치한 카페 겸 레스토랑입니다. 영업시간은 11:00~20:30 이며, 일요일은 쉽니다."
    }

    if name in cafe_info_dict:
        return cafe_info_dict[name]
    else:
        return f"{name}에 대한 정보가 없습니다."


def multiply(a: int, b: int) -> str:
    """두 수를 곱한 결과를 문자열로 반환합니다."""
    return f"The result of {a} multiplied by {b} is {a * b}."


# 2) 도구를 에이전트에 연결하고, 메모리(체크포인터)도 켭니다.
agent = create_agent(
    model="gpt-4.1",
    tools=[cafe_info, multiply],   # 에이전트가 호출할 수 있는 함수 목록
    system_prompt="너는 전북대학교 캠퍼스 주변 맛집을 알려주는 가이드야.",
    checkpointer=InMemorySaver()
)

thread_id = "1"  # 같은 스레드로 대화를 이어갑니다.

# 3) 간단한 인사
response = agent.invoke(
    {"messages": [{"role": "user", "content": "안녕하세요. 이성용입니다. "}]},
    {"configurable": {"thread_id": thread_id}},
)
print(response['messages'][-1].content)

###############################################

# 4) 이전 내용을 기억하는지 물어보기(메모리 작동 확인)
second_message = "제 이름 기억하시나요?"
print("me:", second_message)

response = agent.invoke(
    {"messages": [{"role": "user", "content": second_message}]},
    {"configurable": {"thread_id": thread_id}},
)
print(response['messages'][-1].content)

print("###############################################")

# 5) 툴 사용 예시(1): 카페 정보 조회
third_message = "오스스퀘어에 대해 알려줘"
print("me:", third_message)

response = agent.invoke(
    {"messages": [{"role": "user", "content": third_message}]},
    {"configurable": {"thread_id": thread_id}},
)
print(response['messages'][-1].content)


################################################
print("###############################################")

# 6) 툴 사용 예시(2): 간단한 계산을 시켜 보기
fourth_message = "오스스퀘어에 가서 7명이 아메리카노 먹으면 얼마야?"
print("me:", fourth_message)

response = agent.invoke(
    {"messages": [{"role": "user", "content": fourth_message}]},
    {"configurable": {"thread_id": thread_id}},
)

# LangChain은 내부적으로 필요한 경우, 위에서 제공한 multiply() 같은 함수를
# 호출하여 답을 계산할 수 있습니다. 아래는 전체 메시지 로그를 보기 좋게 출력합니다.
for msg in response['messages']:
    msg.pretty_print()