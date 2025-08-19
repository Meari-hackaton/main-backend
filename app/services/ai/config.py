import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class AIConfig(BaseModel):
    """AI 서비스 설정"""
    
    # Gemini API 설정
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = "gemini-2.5-flash-lite"
    
    # 모델 파라미터
    temperature: float = 0.7
    max_output_tokens: int = 2048
    top_p: float = 0.95
    top_k: int = 40
    
    # LangChain 설정 (선택적)
    langchain_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("LANGCHAIN_API_KEY"))
    langchain_tracing: bool = Field(default_factory=lambda: os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true")
    langchain_project: str = "meari-backend"
    
    # 재시도 설정
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 응답 시간 제한
    request_timeout: int = 30
    
    def validate_keys(self) -> bool:
        """API 키 유효성 검증"""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        return True
    
    class Config:
        validate_assignment = True