from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Agent Platform"
    VERSION: str = "0.1.0"


settings = Settings()