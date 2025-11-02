from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver  
import os
os.environ["OPENAI_API_KEY"] = "OPENAI_API_KEY_PLACEHOLDER"


def cafe_info(name: str) -> str:
    """Get cafe information by name."""
    cafe_info_dict = {
        "오스스퀘어": "오스스퀘어는 전북대학교 삼성문화회관에 위치한 카페입니다. 영업시간은 08:00~220:00입니다. 아메리카노는 5천원입니다.",
        "FA": "FA는 덕진구 들사평1길 44에 위치한 카페 겸 레스토랑입니다. 영업시간은 11:00~20:30 이며, 일요일은 쉽니다."
    }

    if name in cafe_info_dict:
        return cafe_info_dict[name]
    else:
        return f"{name}에 대한 정보가 없습니다."

def multiply(a: int, b: int) -> str:
    """Multiply two numbers."""
    return f"The result of {a} multiplied by {b} is {a * b}."

agent = create_agent(
    model="gpt-4.1",
    tools=[cafe_info, multiply],
    system_prompt="너는 전북대학교 캠퍼스 주변 맛집을 알려주는 가이드야.",
    checkpointer=InMemorySaver()
)



def langchain_basic_agent_example(thread_id: str, user_message: str) -> str:
    response = agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        {"configurable": {"thread_id": thread_id}},
    )

    for msg in response['messages']:
        msg.pretty_print()

    final_answer = response['messages'][-1].content
    return final_answer

