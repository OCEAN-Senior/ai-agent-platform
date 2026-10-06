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

    # Where persistent data lives (SQLite conversation memory). In Docker this is
    # the app_data volume mounted at /app/data.
    DATA_DIR: str = "data"
    # System prompt for /chat (Telegram bot, /ui). Empty = none.
    CHAT_SYSTEM_PROMPT: str = (
        "You are a helpful, concise work assistant for a small team. "
        "Always reply in Uzbek (o'zbek tili, Latin script) unless the user explicitly "
        "asks for another language. Don't mix in English sentences."
    )
    # How many recent messages are sent to the model as context per session.
    MEMORY_MAX_MESSAGES: int = 20

    # Telegram bot (separate process: python -m backend.app.telegram.bot).
    TELEGRAM_BOT_TOKEN: str = ""
    # Comma-separated numeric Telegram user IDs allowed to use the bot.
    TELEGRAM_ALLOWED_USER_IDS: str = ""
    # How the bot reaches this platform's API, and the key if API_KEYS is enabled.
    PLATFORM_URL: str = "http://127.0.0.1:8000"
    PLATFORM_API_KEY: str = ""


settings = Settings()
