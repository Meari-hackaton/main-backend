"""
임베딩 서비스 - 싱글톤 패턴으로 메모리 효율 관리
"""
import os
from sentence_transformers import SentenceTransformer
import logging

# MPS 메모리 설정
os.environ['PYTORCH_MPS_HIGH_WATERMARK_RATIO'] = '0.0'
os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

logger = logging.getLogger(__name__)

# 싱글톤 임베딩 모델 인스턴스
_embedding_model = None

def get_embedding_model():
    """싱글톤 임베딩 모델 가져오기"""
    global _embedding_model
    if _embedding_model is None:
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "nlpai-lab/KURE-v1")
        logger.info(f"임베딩 모델 로드: {model_name}")
        _embedding_model = SentenceTransformer(model_name, device='cpu')
        logger.info(f"임베딩 차원: {_embedding_model.get_sentence_embedding_dimension()}")
    return _embedding_model

def embed_text(text: str):
    """단일 텍스트 임베딩"""
    model = get_embedding_model()
    return model.encode(text)

def embed_texts(texts: list):
    """복수 텍스트 임베딩"""
    model = get_embedding_model()
    return model.encode(texts)