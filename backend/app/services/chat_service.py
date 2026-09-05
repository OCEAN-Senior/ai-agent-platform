from backend.app.services.llm.factory import get_llm_provider


async def get_chat_response(message: str, model: str | None = None) -> str:
    provider = get_llm_provider(model=model)
    return await provider.chat(message)
