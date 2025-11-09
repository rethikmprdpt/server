from pydantic import BaseModel


class ChatHistoryPart(BaseModel):
    role: str
    parts: list[dict]


class ChatRequest(BaseModel):
    task_context: dict
    chat_history: list[ChatHistoryPart]
    new_question: str
