"""
Milvus 벡터 데이터베이스 클라이언트
Zilliz Cloud 연동 및 벡터 검색 기능
"""
import os
import asyncio
from typing import List, Dict, Optional, Any
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv
import logging
import threading

os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

load_dotenv()
logger = logging.getLogger(__name__)

# 스레드 로컬 스토리지
thread_local = threading.local()


class VectorStore:
    """Milvus 벡터 스토어 관리"""
    
    def __init__(self):
        self.uri = os.getenv("MILVUS_URI")
        self.token = os.getenv("MILVUS_TOKEN")
        self.model_name = os.getenv("EMBEDDING_MODEL_NAME", "nlpai-lab/KURE-v1")
        
        if not self.uri or not self.token:
            raise ValueError("MILVUS_URI와 MILVUS_TOKEN이 설정되지 않았습니다")
        
        # Milvus 연결
        self._connect()
        
        logger.info(f"임베딩 모델 로드 중: {self.model_name}")
        self.encoder = SentenceTransformer(self.model_name, device='cpu')
        self.dimension = self.encoder.get_sentence_embedding_dimension()
        logger.info(f"임베딩 차원: {self.dimension}")
    
    def _connect(self):
        """Milvus 서버에 연결"""
        try:
            connections.connect(
                alias="default",
                uri=self.uri,
                token=self.token,
                secure=True
            )
            logger.info("Milvus 연결 성공")
        except Exception as e:
            logger.error(f"Milvus 연결 실패: {e}")
            raise
    
    def create_collection(
        self,
        collection_name: str,
        fields: List[Dict[str, Any]],
        description: str = ""
    ) -> Collection:
        """
        컬렉션 생성
        
        Args:
            collection_name: 컬렉션 이름
            fields: 필드 정의 리스트
            description: 컬렉션 설명
        
        Returns:
            생성된 컬렉션 객체
        """
        # 이미 존재하는지 확인
        if utility.has_collection(collection_name):
            logger.info(f"컬렉션 '{collection_name}'이 이미 존재합니다")
            return Collection(collection_name)
        
        # 스키마 생성
        schema_fields = []
        for field in fields:
            field_schema_args = {
                "name": field["name"],
                "dtype": field["dtype"],
                "is_primary": field.get("is_primary", False),
                "auto_id": field.get("auto_id", False)
            }
            
            # VARCHAR 타입인 경우 max_length 추가
            if field["dtype"] == DataType.VARCHAR:
                field_schema_args["max_length"] = field.get("max_length", 512)
            
            # 벡터 타입인 경우 dim 추가
            if "dim" in field:
                field_schema_args["dim"] = field["dim"]
            
            schema_fields.append(FieldSchema(**field_schema_args))
        
        schema = CollectionSchema(
            fields=schema_fields,
            description=description
        )
        
        # 컬렉션 생성
        collection = Collection(
            name=collection_name,
            schema=schema,
            consistency_level="Strong"
        )
        
        logger.info(f"컬렉션 '{collection_name}' 생성 완료")
        return collection
    
    def create_quotes_collection(self) -> Collection:
        """인용문 컬렉션 생성"""
        fields = [
            {"name": "id", "dtype": DataType.INT64, "is_primary": True, "auto_id": True},
            {"name": "quote_id", "dtype": DataType.INT64},
            {"name": "news_id", "dtype": DataType.VARCHAR, "max_length": 100},
            {"name": "quote_text", "dtype": DataType.VARCHAR, "max_length": 65535},
            {"name": "speaker", "dtype": DataType.VARCHAR, "max_length": 200},
            {"name": "tag_id", "dtype": DataType.INT64},
            {"name": "embedding", "dtype": DataType.FLOAT_VECTOR, "dim": self.dimension}
        ]
        
        collection = self.create_collection(
            collection_name="meari_quotes",
            fields=fields,
            description="메아리 프로젝트 뉴스 인용문 벡터"
        )
        
        # 인덱스 생성
        self._create_index(collection, "embedding")
        return collection
    
    def create_policies_collection(self) -> Collection:
        """정책 컬렉션 생성"""
        fields = [
            {"name": "id", "dtype": DataType.INT64, "is_primary": True, "auto_id": True},
            {"name": "policy_id", "dtype": DataType.VARCHAR, "max_length": 100},
            {"name": "policy_name", "dtype": DataType.VARCHAR, "max_length": 500},
            {"name": "support_content", "dtype": DataType.VARCHAR, "max_length": 65535},
            {"name": "application_url", "dtype": DataType.VARCHAR, "max_length": 500},
            {"name": "organization", "dtype": DataType.VARCHAR, "max_length": 200},
            {"name": "embedding", "dtype": DataType.FLOAT_VECTOR, "dim": self.dimension}
        ]
        
        collection = self.create_collection(
            collection_name="meari_policies",
            fields=fields,
            description="메아리 프로젝트 청년정책 벡터"
        )
        
        # 인덱스 생성
        self._create_index(collection, "embedding")
        return collection
    
    def _create_index(self, collection: Collection, field_name: str):
        """벡터 필드에 인덱스 생성"""
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        
        collection.create_index(
            field_name=field_name,
            index_params=index_params
        )
        logger.info(f"인덱스 생성 완료: {collection.name}.{field_name}")
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        텍스트를 벡터로 변환
        
        Args:
            texts: 텍스트 리스트
        
        Returns:
            임베딩 벡터 배열
        """
        embeddings = self.encoder.encode(
            texts, 
            show_progress_bar=True,
            batch_size=8,
            convert_to_numpy=True
        )
        return embeddings
    
    async def insert_quotes(
        self,
        quotes: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        인용문 벡터 삽입
        
        Args:
            quotes: 인용문 데이터 리스트
            batch_size: 배치 크기
        
        Returns:
            삽입된 개수
        """
        collection = Collection("meari_quotes")
        collection.load()
        
        total_inserted = 0
        
        for i in range(0, len(quotes), batch_size):
            batch = quotes[i:i+batch_size]
            
            # 텍스트 추출 및 임베딩
            texts = [q["quote_text"] for q in batch]
            embeddings = self.embed_texts(texts)
            
            # 데이터 준비
            data = [
                [q["id"] for q in batch],  # quote_id
                [q["news_id"][:100] for q in batch],  # news_id (100자 제한)
                texts,  # quote_text (이미 2000자로 제한됨)
                [(q.get("speaker") or "")[:200] for q in batch],  # speaker (200자 제한)
                [q.get("tag_id", 0) for q in batch],  # tag_id
                embeddings.tolist()  # embedding
            ]
            
            # 삽입
            result = collection.insert(data)
            total_inserted += len(result.primary_keys)
            
            logger.info(f"진행: {min(i+batch_size, len(quotes))}/{len(quotes)}")
            await asyncio.sleep(0.5)
        
        # 플러시
        collection.flush()
        logger.info(f"총 {total_inserted}개 인용문 벡터 삽입 완료")
        
        return total_inserted
    
    async def insert_policies(
        self,
        policies: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        정책 벡터 삽입
        
        Args:
            policies: 정책 데이터 리스트
            batch_size: 배치 크기
        
        Returns:
            삽입된 개수
        """
        collection = Collection("meari_policies")
        collection.load()
        
        total_inserted = 0
        
        for i in range(0, len(policies), batch_size):
            batch = policies[i:i+batch_size]
            
            # 텍스트 추출 및 임베딩 (이름 + 내용 결합)
            texts = [
                f"{p['policy_name']} {p['support_content']}"
                for p in batch
            ]
            embeddings = self.embed_texts(texts)
            
            # 데이터 준비
            data = [
                [p["policy_id"][:100] for p in batch],  # policy_id (100자 제한)
                [p["policy_name"][:500] for p in batch],  # policy_name (500자 제한)
                [p["support_content"][:2000] for p in batch],  # support_content (2000자 제한)
                [p.get("application_url", "")[:500] for p in batch],  # application_url (500자 제한)
                [p.get("organization", "")[:200] for p in batch],  # organization (200자 제한)
                embeddings.tolist()  # embedding
            ]
            
            # 삽입
            result = collection.insert(data)
            total_inserted += len(result.primary_keys)
            
            logger.info(f"진행: {min(i+batch_size, len(policies))}/{len(policies)}")
            await asyncio.sleep(0.5)
        
        # 플러시
        collection.flush()
        logger.info(f"총 {total_inserted}개 정책 벡터 삽입 완료")
        
        return total_inserted
    
    async def search_quotes(
        self,
        query_text: str,
        top_k: int = 5,
        tag_id: Optional[int] = None
    ) -> List[Dict]:
        """
        유사한 인용문 검색
        
        Args:
            query_text: 검색 쿼리
            top_k: 반환할 결과 수
            tag_id: 특정 태그로 필터링
        
        Returns:
            검색 결과
        """
        collection = Collection("meari_quotes")
        collection.load()
        
        # 쿼리 임베딩
        query_embedding = self.embed_texts([query_text])[0]
        
        # 검색 파라미터
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        # 필터 표현식
        expr = f"tag_id == {tag_id}" if tag_id else None
        
        # 검색 실행
        results = collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["quote_id", "quote_text", "speaker", "tag_id", "news_id"]
        )
        
        # 결과 포맷팅
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "score": hit.score,
                "quote_id": hit.entity.get("quote_id"),
                "quote_text": hit.entity.get("quote_text"),
                "speaker": hit.entity.get("speaker"),
                "tag_id": hit.entity.get("tag_id"),
                "news_id": hit.entity.get("news_id")
            })
        
        return formatted_results


def get_quotes_collection() -> Collection:
    """인용문 컬렉션 가져오기 (스레드 세이프)"""
    try:
        # 스레드별로 독립적인 컬렉션 객체 유지
        if not hasattr(thread_local, 'quotes_collection'):
            # 연결 확인
            if not connections.has_connection("default"):
                uri = os.getenv("MILVUS_URI")
                token = os.getenv("MILVUS_TOKEN")
                connections.connect(
                    alias="default",
                    uri=uri,
                    token=token,
                    secure=True
                )
            
            # 컬렉션 로드 (스레드당 한 번만)
            thread_local.quotes_collection = Collection("meari_quotes")
            thread_local.quotes_collection.load()
            logger.info(f"Thread {threading.current_thread().name}: 인용문 컬렉션 로드")
        
        return thread_local.quotes_collection
    except Exception as e:
        logger.error(f"인용문 컬렉션 가져오기 실패: {e}")
        raise


def get_policies_collection() -> Collection:
    """정책 컬렉션 가져오기 (스레드 세이프)"""
    try:
        # 매번 연결 상태 확인 및 재연결
        try:
            # 기존 연결이 있으면 제거
            if connections.has_connection("default"):
                connections.remove_connection("default")
        except:
            pass
        
        # 새로운 연결 생성
        uri = os.getenv("MILVUS_URI")
        token = os.getenv("MILVUS_TOKEN")
        connections.connect(
            alias="default",
            uri=uri,
            token=token,
            secure=True,
            timeout=30
        )
        
        # 컬렉션 로드
        collection = Collection("meari_policies")
        collection.load()
        logger.info(f"Thread {threading.current_thread().name}: 정책 컬렉션 재연결 및 로드")
        
        return collection
    except Exception as e:
        logger.error(f"정책 컬렉션 가져오기 실패: {e}")
        raise
    
    async def search_policies(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        유사한 정책 검색
        
        Args:
            query_text: 검색 쿼리
            top_k: 반환할 결과 수
        
        Returns:
            검색 결과
        """
        collection = Collection("meari_policies")
        collection.load()
        
        # 쿼리 임베딩
        query_embedding = self.embed_texts([query_text])[0]
        
        # 검색 파라미터
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        # 검색 실행
        results = collection.search(
            data=[query_embedding.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["policy_id", "policy_name", "support_content", "application_url", "organization"]
        )
        
        # 결과 포맷팅
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "score": hit.score,
                "policy_id": hit.entity.get("policy_id"),
                "policy_name": hit.entity.get("policy_name"),
                "support_content": hit.entity.get("support_content"),
                "application_url": hit.entity.get("application_url"),
                "organization": hit.entity.get("organization")
            })
        
        return formatted_results


def get_quotes_collection() -> Collection:
    """인용문 컬렉션 가져오기 (스레드 세이프)"""
    try:
        # 스레드별로 독립적인 컬렉션 객체 유지
        if not hasattr(thread_local, 'quotes_collection'):
            # 연결 확인
            if not connections.has_connection("default"):
                uri = os.getenv("MILVUS_URI")
                token = os.getenv("MILVUS_TOKEN")
                connections.connect(
                    alias="default",
                    uri=uri,
                    token=token,
                    secure=True
                )
            
            # 컬렉션 로드 (스레드당 한 번만)
            thread_local.quotes_collection = Collection("meari_quotes")
            thread_local.quotes_collection.load()
            logger.info(f"Thread {threading.current_thread().name}: 인용문 컬렉션 로드")
        
        return thread_local.quotes_collection
    except Exception as e:
        logger.error(f"인용문 컬렉션 가져오기 실패: {e}")
        raise


def get_policies_collection() -> Collection:
    """정책 컬렉션 가져오기 (스레드 세이프)"""
    try:
        # 스레드별로 독립적인 컬렉션 객체 유지
        if not hasattr(thread_local, 'policies_collection'):
            # 연결 확인
            if not connections.has_connection("default"):
                uri = os.getenv("MILVUS_URI")
                token = os.getenv("MILVUS_TOKEN")
                connections.connect(
                    alias="default",
                    uri=uri,
                    token=token,
                    secure=True
                )
            
            # 컬렉션 로드 (스레드당 한 번만)
            thread_local.policies_collection = Collection("meari_policies")
            thread_local.policies_collection.load()
            logger.info(f"Thread {threading.current_thread().name}: 정책 컬렉션 로드")
        
        return thread_local.policies_collection
    except Exception as e:
        logger.error(f"정책 컬렉션 가져오기 실패: {e}")
        raise