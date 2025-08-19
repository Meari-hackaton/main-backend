from fastapi import APIRouter
from app.api.v1 import meari

api_router = APIRouter()

# 메아리 API 라우터 등록
api_router.include_router(meari.router)