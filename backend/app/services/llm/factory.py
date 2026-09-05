from backend.app.core.config import settings
from backend.app.services.llm.base import LLMProvider
from backend.app.services.llm.ollama_provider import OllamaProvider


def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")
