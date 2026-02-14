from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ocean:ocean@localhost:5432/ocean"
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str = ""
    api_secret_key: str = "dev-secret-key"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    llm_model: str = "gemini-3-flash"  # Use gemini-3-pro for higher quality tasks

    # Crawler settings
    crawl_concurrency: int = 20
    crawl_timeout_seconds: int = 10
    crawl_interval_hours: int = 24

    # API settings
    api_rate_limit: int = 100  # requests per minute per key
    default_page_size: int = 20
    max_page_size: int = 100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
