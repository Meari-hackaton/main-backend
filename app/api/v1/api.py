from fastapi import APIRouter
from app.api.v1 import meari, dashboard, history, calendar, midi

api_router = APIRouter()

# 메아리 API 라우터 등록
api_router.include_router(meari.router)
api_router.include_router(dashboard.router)
api_router.include_router(history.router)
api_router.include_router(calendar.router)
api_router.include_router(midi.router)