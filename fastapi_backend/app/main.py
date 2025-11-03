# app/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI(title="Profile-Aware Chatbot (Base Server)")

@app.get("/health")
def health():
    """서버 상태 확인용"""
    return {"status": "ok"}

async def fake_stream_llm():
    """가짜 토큰 스트리밍 (테스트용)"""
    for token in ["안녕하세요. ", "스트리밍 ", "테스트 ", "중입니다."]:
        yield token
        await asyncio.sleep(0.03)

@app.post("/chat/stream")
async def chat_stream(req: Request):
    body = await req.json()
    user_msg = (body.get("message") or "").strip()
    if not user_msg:
        raise HTTPException(400, "message is required")

    async def gen():
        async for token in fake_stream_llm():
            yield f"data: {token}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
