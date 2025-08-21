"""
테스트 사용자 생성 스크립트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
import uuid

async def create_test_user():
    """테스트 사용자 생성"""
    async with AsyncSessionLocal() as db:
        # 테스트 사용자 생성
        test_user = User(
            id=uuid.uuid4(),
            email="test@meari.com",
            nickname="테스트 사용자",
            social_provider="google",
            social_id="test_google_id_123"
        )
        
        db.add(test_user)
        await db.commit()
        
        print(f"✅ 테스트 사용자 생성 완료!")
        print(f"   Email: {test_user.email}")
        print(f"   닉네임: {test_user.nickname}")
        print(f"   ID: {test_user.id}")
        
        return test_user

if __name__ == "__main__":
    asyncio.run(create_test_user())