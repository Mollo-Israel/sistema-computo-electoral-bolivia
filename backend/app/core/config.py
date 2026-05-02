"""
Application configuration loaded from environment variables.
TODO (Escobar): add cluster-specific settings (replica set names, timeouts, etc.).
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    backend_port: int = 8000
    mongo_rrv_uri: str = "mongodb://localhost:27017/rrv_db"
    postgres_oficial_host: str = "localhost"
    postgres_oficial_port: int = 5432
    postgres_oficial_db: str = "computo_oficial_db"
    postgres_oficial_user: str = "postgres"
    postgres_oficial_password: str = "postgres"
    uploads_dir: str = "backend/uploads"
    storage_dir: str = "backend/storage"
    dashboard_dir: str = "dashboard"
    sms_pin_default: str = "1234"

    class Config:
        env_file = ".env"


settings = Settings()
