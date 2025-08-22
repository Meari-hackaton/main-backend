from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, Field
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Meari Backend"
    DEBUG: bool = True
    
    # Database - Render가 제공하는 DATABASE_URL 사용
    DATABASE_URL: Optional[str] = Field(default=os.getenv("DATABASE_URL"))
    
    # Security
    SECRET_KEY: str = Field(default=os.getenv("SECRET_KEY", "dev-secret-key"))
    
    # BigKinds API
    BIGKINDS_ACCESS_KEY: Optional[str] = Field(default=os.getenv("BIGKINDS_ACCESS_KEY"))
    
    # Frontend URLs
    FRONTEND_URL: str = "http://localhost:3000"
    DOMAIN: str = "https://mearihearo.com"
    
    # CORS Settings
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        origins = [
            "https://frontend-weld-pi-52.vercel.app",
            "https://frontend-git-main-kimdonghyeon-s-projects.vercel.app",
            "https://frontend-fb3qfazcp-kimdonghyeon-s-projects.vercel.app",
            "https://mearihearo.com",
            "http://localhost:3000"
        ]
        if self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # 추가 환경변수 무시

settings = Settings()