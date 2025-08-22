"""Mock EmpathyAgent for deployment without Milvus"""
from typing import List, Dict, Any
import random

class EmpathyAgent:
    def __init__(self):
        self.model_name = "gemini-2.0-flash-exp"
    
    async def process(self, tag_ids: List[int], user_id: int = None) -> List[Dict[str, Any]]:
        """Mock empathy card generation without Milvus"""
        mock_cards = []
        
        for i in range(3):
            card = {
                "card_type": "empathy",
                "title": f"공감 카드 {i+1}",
                "content": "청년들이 겪는 어려움에 대한 공감 메시지입니다. 현재 데이터베이스 연결 없이 임시 메시지를 표시합니다.",
                "metadata": {
                    "tag_id": tag_ids[0] if tag_ids else 1,
                    "source": "mock",
                    "quotes": []
                }
            }
            mock_cards.append(card)
        
        return mock_cards