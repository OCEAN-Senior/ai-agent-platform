from backend.app.services.llm.factory import get_llm_provider


async def get_chat_response(message: str) -> str:
    provider = get_llm_provider()
    return await provider.chat(message)
