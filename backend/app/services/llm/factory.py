from backend.app.core.config import settings
from backend.app.services.llm.base import LLMProvider
from backend.app.services.llm.ollama_provider import OllamaProvider


def get_llm_provider(model: str | None = None) -> LLMProvider:
    if settings.LLM_PROVIDER == "ollama":
        return OllamaProvider(model=model)
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}")
