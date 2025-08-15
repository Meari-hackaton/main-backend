from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Meari Backend"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: PostgresDsn
    
    # Security
    SECRET_KEY: str
    
    # BigKinds API
    BIGKINDS_ACCESS_KEY: str
    
    class Config:
        env_file = ".env"

settings = Settings()