"""
청년정책 데이터 저장 Repository
"""
from typing import List, Dict, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.core.database import get_db
from app.models.policy import YouthPolicy
from datetime import datetime


class PolicyRepository:
    """청년정책 데이터 저장 관리"""
    
    @staticmethod
    async def save_policy(policy_data: Dict) -> bool:
        """단일 정책 저장"""
        async for db in get_db():
            try:
                # upsert 처리 (중복 시 업데이트)
                stmt = insert(YouthPolicy).values(
                    policy_id=policy_data["policy_id"],
                    policy_name=policy_data["policy_name"],
                    support_content=policy_data["support_content"],
                    application_url=policy_data["application_url"],
                    organization=policy_data["organization"],
                    target_age=policy_data.get("target_age", ""),
                    target_desc=policy_data.get("target_desc", ""),
                    support_scale=policy_data.get("support_scale", ""),
                    application_period=policy_data.get("application_period", ""),
                    tags=policy_data.get("tags", []),
                    updated_at=datetime.utcnow()
                )
                
                stmt = stmt.on_conflict_do_update(
                    index_elements=["policy_id"],
                    set_={
                        "policy_name": stmt.excluded.policy_name,
                        "support_content": stmt.excluded.support_content,
                        "application_url": stmt.excluded.application_url,
                        "organization": stmt.excluded.organization,
                        "target_age": stmt.excluded.target_age,
                        "target_desc": stmt.excluded.target_desc,
                        "support_scale": stmt.excluded.support_scale,
                        "application_period": stmt.excluded.application_period,
                        "updated_at": datetime.utcnow()
                    }
                )
                
                await db.execute(stmt)
                await db.commit()
                return True
                
            except Exception as e:
                print(f"정책 저장 실패 ({policy_data.get('policy_id')}): {e}")
                await db.rollback()
                return False
    
    @staticmethod
    async def bulk_save_policies(policies: List[Dict]) -> Dict:
        """여러 정책 일괄 저장"""
        stats = {
            "success": 0,
            "duplicate_updated": 0,
            "failed": 0
        }
        
        if not policies:
            return stats
        
        async for db in get_db():
            try:
                # 기존 정책 ID 조회
                existing_ids_result = await db.execute(
                    select(YouthPolicy.policy_id)
                )
                existing_ids = {row[0] for row in existing_ids_result}
                
                # 새로운 정책과 업데이트할 정책 분리
                new_policies = []
                update_policies = []
                
                for policy in policies:
                    if policy["policy_id"] in existing_ids:
                        update_policies.append(policy)
                    else:
                        new_policies.append(policy)
                
                # 새로운 정책 일괄 삽입
                if new_policies:
                    await db.execute(
                        insert(YouthPolicy),
                        [
                            {
                                "policy_id": p["policy_id"],
                                "policy_name": p["policy_name"],
                                "support_content": p["support_content"],
                                "application_url": p["application_url"],
                                "organization": p["organization"],
                                "target_age": p.get("target_age", ""),
                                "target_desc": p.get("target_desc", ""),
                                "support_scale": p.get("support_scale", ""),
                                "application_period": p.get("application_period", ""),
                                "tags": p.get("tags", [])
                            }
                            for p in new_policies
                        ]
                    )
                    stats["success"] = len(new_policies)
                
                # 기존 정책 업데이트
                for policy in update_policies:
                    stmt = insert(YouthPolicy).values(
                        policy_id=policy["policy_id"],
                        policy_name=policy["policy_name"],
                        support_content=policy["support_content"],
                        application_url=policy["application_url"],
                        organization=policy["organization"],
                        target_age=policy.get("target_age", ""),
                        target_desc=policy.get("target_desc", ""),
                        support_scale=policy.get("support_scale", ""),
                        application_period=policy.get("application_period", ""),
                        tags=policy.get("tags", []),
                        updated_at=datetime.utcnow()
                    )
                    
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["policy_id"],
                        set_={
                            "policy_name": stmt.excluded.policy_name,
                            "support_content": stmt.excluded.support_content,
                            "application_url": stmt.excluded.application_url,
                            "organization": stmt.excluded.organization,
                            "target_age": stmt.excluded.target_age,
                            "target_desc": stmt.excluded.target_desc,
                            "support_scale": stmt.excluded.support_scale,
                            "application_period": stmt.excluded.application_period,
                            "updated_at": datetime.utcnow()
                        }
                    )
                    
                    await db.execute(stmt)
                
                stats["duplicate_updated"] = len(update_policies)
                
                await db.commit()
                
            except Exception as e:
                print(f"정책 일괄 저장 실패: {e}")
                await db.rollback()
                stats["failed"] = len(policies)
        
        return stats
    
    @staticmethod
    async def get_policy_count() -> int:
        """저장된 정책 총 개수 조회"""
        async for db in get_db():
            result = await db.execute(
                select(func.count(YouthPolicy.policy_id))
            )
            return result.scalar() or 0
    
    @staticmethod
    async def get_all_policies() -> List[YouthPolicy]:
        """모든 정책 조회"""
        async for db in get_db():
            result = await db.execute(
                select(YouthPolicy).order_by(YouthPolicy.created_at.desc())
            )
            return result.scalars().all()
    
    @staticmethod
    async def get_policy_by_id(policy_id: str) -> Optional[YouthPolicy]:
        """특정 정책 조회"""
        async for db in get_db():
            result = await db.execute(
                select(YouthPolicy).where(YouthPolicy.policy_id == policy_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_policies_for_embedding() -> List[Dict]:
        """임베딩을 위한 정책 데이터 조회"""
        async for db in get_db():
            result = await db.execute(
                select(
                    YouthPolicy.policy_id,
                    YouthPolicy.policy_name,
                    YouthPolicy.support_content,
                    YouthPolicy.organization,
                    YouthPolicy.application_url
                )
            )
            
            policies = []
            for row in result:
                policies.append({
                    "policy_id": row[0],
                    "policy_name": row[1],
                    "support_content": row[2],
                    "organization": row[3],
                    "application_url": row[4],
                    # 임베딩할 텍스트: 정책명 + 지원내용
                    "text_for_embedding": f"{row[1]}\n\n{row[2]}"
                })
            
            return policies