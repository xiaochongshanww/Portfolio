from pydantic import BaseModel, Field

from ..core.config import settings


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(default_factory=lambda: settings.mimo_model)
    messages: list[ChatMessage]
    stream: bool | None = False
    temperature: float | None = 0.7
    max_tokens: int | None = None
    top_p: float | None = 1.0
    include_rag_trace: bool = False
