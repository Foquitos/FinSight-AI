import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.schemas import ChatbotRequest, HistoryResponse, HistoryMessage

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post("/chat")
async def chatbot_stream(body: ChatbotRequest, request: Request):
    """Streams the RAG chatbot response token by token."""
    chatbot = request.app.state.chatbot
    task_id = body.task_id or str(uuid.uuid4())

    async def generate():
        async for token in chatbot.stream_query(body.query, body.user_id, task_id):
            yield token

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@router.get("/history/{user_id}", response_model=HistoryResponse)
def get_history(user_id: int, request: Request):
    chatbot = request.app.state.chatbot
    raw = chatbot.get_history(user_id)
    return HistoryResponse(history=[HistoryMessage(**m) for m in raw])


@router.post("/clear-history/{user_id}")
def clear_history(user_id: int, request: Request):
    chatbot = request.app.state.chatbot
    chatbot.clear_history(user_id)
    return {"status": "ok"}
