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

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "documents"

    # Comma-separated API keys. Empty = auth disabled (local dev only --
    # must be set before this is reachable outside localhost).
    API_KEYS: str = ""


settings = Settings()
