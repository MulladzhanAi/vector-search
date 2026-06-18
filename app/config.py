from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, читаются из .env (или переменных окружения)."""

    es_url: str = "http://localhost:9201"
    index_name: str = "products"
    model_name: str = "intfloat/multilingual-e5-base"
    embed_dim: int = 768
    models_dir: str = "models"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # model_name иначе конфликтует с защищённым namespace pydantic "model_"
        protected_namespaces=(),
    )


settings = Settings()
