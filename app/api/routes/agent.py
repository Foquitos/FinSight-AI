from fastapi import APIRouter, Request
from app.schemas import AgentChatRequest, AgentChatResponse, HistoryResponse, HistoryMessage

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(body: AgentChatRequest, request: Request):
    agent = request.app.state.agent
    response = await agent.achat(body.query, body.user_id)
    return AgentChatResponse(response=response)


@router.get("/history/{user_id}", response_model=HistoryResponse)
async def agent_history(user_id: int, request: Request):
    raw = await request.app.state.agent.get_history(user_id)
    return HistoryResponse(history=[HistoryMessage(**m) for m in raw])


@router.post("/clear-history/{user_id}", tags=["Agent"])
def agent_clear_history(user_id: int, request: Request):
    request.app.state.agent.clear_history(user_id)
    return {"status": "ok"}
