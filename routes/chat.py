from fastapi import APIRouter

from models.schemas import ChatRequest
from services.chat_service import (
    clear_chat_messages,
    generate_chat_reply,
    init_db,
    list_chat_messages,
)


router = APIRouter(tags=["chat"])


@router.on_event("startup")
async def startup() -> None:
    init_db()


@router.get("/chat-history/{conversation_id}")
async def chat_history(conversation_id: str):
    return {"conversation_id": conversation_id, "messages": list_chat_messages(conversation_id)}


@router.delete("/chat-history/{conversation_id}")
async def delete_chat_history(conversation_id: str):
    clear_chat_messages(conversation_id)
    return {"status": "ok", "conversation_id": conversation_id}


@router.post("/chat")
async def chat(request: ChatRequest):
    message = request.message.strip()
    conversation_id = request.conversation_id.strip() or "default"
    if not message:
        from utils.errors import ServiceError

        raise ServiceError("Message is required", status_code=400, code="empty_message")
    return await generate_chat_reply(message, conversation_id, request.history)

