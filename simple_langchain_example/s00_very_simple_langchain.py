"""
초보자용: 아주 단순한 LangChain 에이전트 예제

무엇을 하나요?
- GPT 모델을 사용하는 "에이전트"를 하나 만들고
- 사용자 메시지를 한 번 보내서 답을 받고,
- 다시 한 번 메시지를 보내서 답을 받습니다.

중요 포인트(기억에 관해):
- 여기서는 대화 기록 저장 기능(메모리)을 쓰지 않습니다.
- 따라서 두 번째 질문은 첫 번째 질문의 내용을 자동으로 "기억"하지 않을 수 있습니다.

주의(보안): 실제 프로젝트에서는 API 키를 코드에 직접 적지 말고,
환경변수(예: export OPENAI_API_KEY=...)로 외부에서 주입하세요.
"""

from langchain.agents import create_agent
import os

# (학습용) API 키를 코드에서 설정하고 있습니다.
# 실제로는 아래와 같이 환경변수에서 읽는 방식을 쓰세요.
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY_PLACEHOLDER"

# 참고 자료: https://docs.langchain.com/oss/python/langchain/quickstart

# 1) 에이전트 만들기
# - model: 사용할 모델 이름
# - system_prompt: 모델에게 줄 역할/지침(Assistant의 성격 같은 것)
agent = create_agent(
    model="gpt-4.1",
    system_prompt="너는 전북대학교 캠퍼스 주변 맛집을 알려주는 가이드야.",
)

# 2) 첫 번째 메시지 보내기
response = agent.invoke(
    {"messages": [{"role": "user", "content": "안녕하세요. 이성용입니다. "}]},
)

# 응답은 딕셔너리 형태이며, 'messages' 리스트의 마지막 요소가 보통 모델의 최신 답변입니다.
print(response['messages'][-1].content)

# 3) 두 번째 메시지 보내기 (이전 내용을 기억하지 않을 수 있음)
second_message = "제 이름 기억하시나요?"
print("me:", second_message)

response = agent.invoke(
    {"messages": [{"role": "user", "content": second_message}]},
)

print(response['messages'][-1].content)