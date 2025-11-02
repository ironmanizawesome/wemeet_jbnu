"""
초보자용: "대화 기록(메모리)"을 사용하는 예제

무엇이 다른가요?
- s00 예제와 달리, 여기서는 InMemorySaver(임시 메모리 저장소)를 사용합니다.
- 같은 thread_id로 요청을 보내면, 이전에 했던 대화가 이어집니다(기억 기능).

주의(보안): API 키는 코드에 직접 쓰지 말고 환경변수로 설정하는 것이 안전합니다.
"""

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver  
import os

# 학습 편의를 위해 코드에서 설정했지만, 실제로는 환경변수를 사용하세요.
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY_PLACEHOLDER"


# 1) 메모리를 가진 에이전트 만들기
agent = create_agent(
    model="gpt-4.1",
    system_prompt="너는 전북대학교 캠퍼스 주변 맛집을 알려주는 가이드야.",
    checkpointer=InMemorySaver()  # 대화 내용을 메모리에 저장/불러오기
)

# 같은 스레드 ID로 요청을 보내면 이전 대화가 이어집니다.
thread_id = "1"

# 2) 첫 메시지: 자기소개
response = agent.invoke(
    {"messages": [{"role": "user", "content": "안녕하세요. 이성용입니다. "}]},
    {"configurable": {"thread_id": thread_id}},  # 스레드 ID 지정
)

print(response['messages'][-1].content)

###############################################

# 3) 두 번째 메시지: 이름을 기억하는지 물어보기
second_message = "제 이름 기억하시나요?"
print("me:", second_message)

response = agent.invoke(
    {"messages": [{"role": "user", "content": second_message}]},
    {"configurable": {"thread_id": thread_id}},  # 같은 스레드 ID 유지 → 기억 효과
)

print(response['messages'][-1].content)