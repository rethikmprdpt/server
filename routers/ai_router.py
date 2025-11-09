from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import all necessary components
from db.database import get_db
from db.models import User
from routers.auth_router import get_current_user
from schemas.chat import ChatRequest
from services.ai import get_gemini_response

ai_router = APIRouter(
    prefix="/api/v1/chat",  # Using a prefix
    tags=["AI Assistant"],
)


class ChatResponse(BaseModel):
    text: str


@ai_router.post(
    "/",
    response_model=ChatResponse,
    summary="Proxy for the AI Chatbot",
)
async def handle_chat(
    chat_request: ChatRequest,
    db: Annotated[Session, Depends(get_db)],  # noqa: ARG001
    current_user: Annotated[User, Depends(get_current_user)],  # noqa: ARG001
):
    # The get_current_user dependency already secures this.
    # We can now trust the request is from a valid, logged-in user.
    try:
        response_text = await get_gemini_response(chat_request)
        return ChatResponse(text=response_text)
    except HTTPException as e:
        raise e  # noqa: TRY201
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))  # noqa: B904
