from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "rrv_db"
    POSTGRES_DSN: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/oficial_db"

    model_config = {"env_file": ".env"}


settings = Settings()
