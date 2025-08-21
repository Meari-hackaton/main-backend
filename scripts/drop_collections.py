"""
Milvus 컬렉션 삭제 스크립트
"""
from pymilvus import connections, utility
import os
from dotenv import load_dotenv

load_dotenv()

# Milvus 연결
connections.connect(
    alias="default",
    uri=os.getenv("MILVUS_URI"),
    token=os.getenv("MILVUS_TOKEN"),
    secure=True
)

# 컬렉션 삭제
collections_to_drop = ["meari_quotes", "meari_policies"]

for collection_name in collections_to_drop:
    if utility.has_collection(collection_name):
        utility.drop_collection(collection_name)
        print(f"✅ {collection_name} 컬렉션 삭제 완료")
    else:
        print(f"ℹ️ {collection_name} 컬렉션이 존재하지 않습니다")

print("\n모든 컬렉션 삭제 완료")