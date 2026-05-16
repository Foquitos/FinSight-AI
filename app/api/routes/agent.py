from fastapi import APIRouter, Request, HTTPException
from app.schemas import AgentChatRequest, AgentChatResponse

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(body: AgentChatRequest, request: Request):
    agent = request.app.state.agent
    response = await agent.achat(body.query)
    return AgentChatResponse(response=response)
