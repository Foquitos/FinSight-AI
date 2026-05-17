from pydantic import BaseModel, Field
from typing import List, Dict, Optional


class AgentChatRequest(BaseModel):
    query: str = Field(..., min_length=1, example="Is a $1,250 electronics purchase at 3am international fraud?")
    user_id: int = Field(default=1)


class AgentChatResponse(BaseModel):
    response: str


class ChatbotRequest(BaseModel):
    query: str = Field(..., min_length=1)
    user_id: int = Field(default=1)
    task_id: Optional[str] = Field(default=None)


class HistoryMessage(BaseModel):
    role: str
    content: str


class HistoryResponse(BaseModel):
    history: List[HistoryMessage]
