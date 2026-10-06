from backend.app.core.config import settings
from backend.app.services.llm.base import LLMProvider
from backend.app.services.llm.ollama_provider import OllamaProvider
from backend.app.services.llm.openai_compatible_provider import OpenAICompatibleProvider


def get_llm_provider(model: str | None = None) -> LLMProvider:
    if settings.LLM_PROVIDER == "ollama":
        return OllamaProvider(model=model)
    if settings.LLM_PROVIDER == "openai_compatible":
        return OpenAICompatibleProvider(model=model)
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")
