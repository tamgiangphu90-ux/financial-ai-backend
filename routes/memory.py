from fastapi import APIRouter

from memory.memory_manager import MemoryManager


router = APIRouter(tags=["memory"])


@router.get("/memory/user/{user_id}")
async def user_memory(user_id: str):
    return MemoryManager().build_prompt_context(user_id=user_id)
