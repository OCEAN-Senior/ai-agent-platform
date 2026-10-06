from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "AI Agent Platform"
    VERSION: str = "0.1.0"
    APP_ENV: str = "development"

    LLM_PROVIDER: str = "ollama"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_CODER_MODEL: str = "qwen2.5-coder:7b"
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # LLM_PROVIDER=openai_compatible: any OpenAI-compatible /v1 gateway, e.g. a
    # self-hosted OmniRoute in front of Ollama. Model names are still taken from
    # OLLAMA_MODEL / OLLAMA_CODER_MODEL, with the gateway's routing prefix added.
    OPENAI_COMPAT_BASE_URL: str = "http://127.0.0.1:20128/v1"
    OPENAI_COMPAT_API_KEY: str = ""
    OPENAI_COMPAT_MODEL_PREFIX: str = "ollama/"

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "documents"

    # Self-hosted SearXNG instance for the web_search tool -- no API key,
    # no third-party account, queries never leave our own infrastructure.
    SEARXNG_URL: str = "http://localhost:8080"

    # Comma-separated API keys. Empty = auth disabled (local dev only --
    # must be set before this is reachable outside localhost).
    API_KEYS: str = ""


settings = Settings()
