import asyncio
from sqlalchemy import select
from app.core.database import engine, async_session
from app.models.tag import Tag

# 태그 데이터 정의 (3개 대분류, 9개 중분류)
TAG_DATA = {
    "진로/취업": [
        "직장 내 번아웃",
        "취업 불안/스트레스",
        "이직/커리어 전환"
    ],
    "마음/건강": [
        "우울감/무기력",
        "건강염려증",
        "수면장애"
    ],
    "인간관계": [
        "사회적 고립감",
        "세대 갈등",
        "관계 스트레스"
    ]
}


async def seed_tags():
    """태그 데이터 초기화"""
    async with async_session() as session:
        # 기존 태그 확인
        result = await session.execute(select(Tag))
        existing_tags = result.scalars().all()
        
        if existing_tags:
            print("태그가 이미 존재합니다. 초기화를 건너뜁니다.")
            return
        
        order_index = 0
        
        # 대분류 태그 생성
        for major_name, minor_names in TAG_DATA.items():
            order_index += 1
            major_tag = Tag(
                name=major_name,
                category="major",
                parent_id=None,
                order_index=order_index
            )
            session.add(major_tag)
            await session.flush()  # ID 생성을 위해 flush
            
            # 중분류 태그 생성
            for minor_name in minor_names:
                order_index += 1
                minor_tag = Tag(
                    name=minor_name,
                    category="minor",
                    parent_id=major_tag.id,
                    order_index=order_index
                )
                session.add(minor_tag)
        
        await session.commit()
        print("태그 초기화 완료!")
        
        # 생성된 태그 확인
        result = await session.execute(
            select(Tag).order_by(Tag.order_index)
        )
        all_tags = result.scalars().all()
        
        print("\n생성된 태그 목록:")
        for tag in all_tags:
            if tag.category == "major":
                print(f"\n[{tag.name}]")
            else:
                print(f"  - {tag.name}")


if __name__ == "__main__":
    asyncio.run(seed_tags())