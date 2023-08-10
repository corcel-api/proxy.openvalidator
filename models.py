from typing import List, Literal
from pydantic import BaseModel


class ConversationItem(BaseModel):
    role: Literal["user", "system", "assistant"]
    content: str


class ProxyRequestModel(BaseModel):
    uid: int
    roles: List[str]
    messages: List[str]


class ProxyResponseModel(BaseModel):
    uid: int
    incentive: float
    is_available: bool
    hotkey: str
    coldkey: str
    message: ConversationItem
    response_time: int
