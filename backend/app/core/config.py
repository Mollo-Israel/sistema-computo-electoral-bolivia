"""
Application configuration loaded from environment variables.
Cluster defaults are tuned for Docker Compose deployment.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    backend_port: int = 8000
    mongo_rrv_uri: str = "mongodb://mongo-rrv-primary:27017,mongo-rrv-secondary-1:27017,mongo-rrv-secondary-2:27017/rrv_db?replicaSet=rs0"
    postgres_oficial_host: str = "postgres-oficial-primary"
    postgres_oficial_port: int = 5432
    postgres_oficial_db: str = "computo_oficial_db"
    postgres_oficial_user: str = "postgres"
    postgres_oficial_password: str = "postgres"
    uploads_dir: str = "backend/uploads"
    sms_pin_default: str = "1234"

    class Config:
        env_file = ".env"


settings = Settings()
