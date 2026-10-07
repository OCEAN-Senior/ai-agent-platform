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
    # Model for tool calling (ToolAgent). Kept separate because a language-tuned chat
    # model (e.g. the Uzbek one) may answer in prose instead of calling tools.
    OLLAMA_TOOL_MODEL: str = "llama3.1:8b"
    # Reasoning model for chat questions about numbers, tables or logic (picked automatically by
    # services/llm/model_router.py). Empty = every chat message uses OLLAMA_MODEL.
    REASONING_MODEL: str = ""
    # Output cap for the reasoning model -- R1-style models can otherwise loop while thinking.
    REASONING_MAX_TOKENS: int = 3072
    EMBEDDING_MODEL: str = "nomic-embed-text"

    # LLM_PROVIDER=openai_compatible: any OpenAI-compatible /v1 gateway, e.g. a
    # self-hosted OmniRoute in front of Ollama. Model names are still taken from
    # OLLAMA_MODEL / OLLAMA_CODER_MODEL, with the gateway's routing prefix added.
    OPENAI_COMPAT_BASE_URL: str = "http://127.0.0.1:20128/v1"
    OPENAI_COMPAT_API_KEY: str = ""
    OPENAI_COMPAT_MODEL_PREFIX: str = "ollama/"

    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "documents"
    # Per-user document search in chat: how many excerpts, and the minimum cosine
    # similarity for an excerpt to be included at all.
    RAG_TOP_K: int = 3
    RAG_MIN_SCORE: float = 0.6

    # Self-hosted SearXNG instance for the web_search tool -- no API key,
    # no third-party account, queries never leave our own infrastructure.
    SEARXNG_URL: str = "http://localhost:8080"

    # Comma-separated API keys. Empty = auth disabled (local dev only --
    # must be set before this is reachable outside localhost).
    API_KEYS: str = ""

    # Password for the /admin panel (all conversations). Empty = panel disabled.
    ADMIN_PASSWORD: str = ""

    # Where persistent data lives (SQLite conversation memory). In Docker this is
    # the app_data volume mounted at /app/data.
    DATA_DIR: str = "data"
    # System prompt for /chat (Telegram bot, /ui). Empty = none.
    CHAT_SYSTEM_PROMPT: str = (
        "You are a helpful, concise work assistant for a small team. "
        "Always reply in Uzbek (o'zbek tili, Latin script) unless the user explicitly "
        "asks for another language. Don't mix in English sentences."
    )
    # Cloud fallback: full OpenAI-compatible gateway model id (e.g. an official API model
    # added to OmniRoute). Empty = disabled -- nothing is ever sent to a cloud model.
    CLOUD_MODEL: str = ""
    # How many recent messages (masked) go to the cloud model as context.
    CLOUD_CONTEXT_MESSAGES: int = 6
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
