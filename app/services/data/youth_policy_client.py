"""
청년정책 API 클라이언트
온라인청년센터 Open API를 통한 청년정책 데이터 수집
"""
import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET


class YouthPolicyClient:
    """청년정책 API 클라이언트"""
    
    def __init__(self):
        self.api_key = os.getenv("YOUTH_POLICY_API_KEY")
        if not self.api_key:
            raise ValueError("YOUTH_POLICY_API_KEY 환경변수가 설정되지 않았습니다")
        
        self.base_url = "https://www.youthcenter.go.kr/opi"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        if self.session:
            await self.session.close()
    
    async def _request(self, endpoint: str, params: Dict) -> str:
        """API 요청 실행"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # API 키 추가
        params["openApiVlak"] = self.api_key
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"API 요청 실패: {response.status}")
        except Exception as e:
            print(f"API 요청 중 오류: {e}")
            raise
    
    def _parse_xml_response(self, xml_text: str) -> Dict:
        """XML 응답 파싱"""
        try:
            root = ET.fromstring(xml_text)
            
            # 전체 개수 추출
            total_cnt = root.find(".//totalCnt")
            total_count = int(total_cnt.text) if total_cnt is not None else 0
            
            # 정책 리스트 추출
            policies = []
            for emp in root.findall(".//emp"):
                policy = {}
                
                # 필요한 필드 추출
                fields = [
                    "bizId",      # 정책 ID
                    "polyBizSjnm", # 정책명
                    "polyItcnCn",  # 정책 소개
                    "sporCn",      # 지원 내용
                    "rqutPrdCn",   # 신청 기간
                    "ageInfo",     # 연령 정보
                    "majrRqisCn",  # 전공 요건
                    "empmSttsCn",  # 취업 상태
                    "splzRlmRqisCn", # 특화 분야
                    "cnsgNmor",    # 운영 기관
                    "rqutUrla",    # 신청 URL
                    "rfcSiteUrla1", # 참고 사이트 URL1
                    "rfcSiteUrla2"  # 참고 사이트 URL2
                ]
                
                for field in fields:
                    elem = emp.find(field)
                    if elem is not None and elem.text:
                        policy[field] = elem.text.strip()
                    else:
                        policy[field] = ""
                
                if policy.get("bizId"):  # 정책 ID가 있는 경우만 추가
                    policies.append(policy)
            
            return {
                "total_count": total_count,
                "policies": policies
            }
            
        except Exception as e:
            print(f"XML 파싱 오류: {e}")
            return {"total_count": 0, "policies": []}
    
    async def get_policy_list(self, page_index: int = 1, page_size: int = 100) -> Dict:
        """정책 목록 조회"""
        params = {
            "pageIndex": page_index,
            "display": page_size
        }
        
        xml_response = await self._request("empList.do", params)
        return self._parse_xml_response(xml_response)
    
    async def get_policy_detail(self, policy_id: str) -> Optional[Dict]:
        """정책 상세 조회"""
        params = {
            "bizId": policy_id
        }
        
        try:
            xml_response = await self._request("empDtls.do", params)
            result = self._parse_xml_response(xml_response)
            
            if result["policies"]:
                return result["policies"][0]
            return None
            
        except Exception as e:
            print(f"정책 상세 조회 실패 ({policy_id}): {e}")
            return None
    
    async def collect_all_policies(self) -> List[Dict]:
        """모든 정책 수집"""
        all_policies = []
        page_index = 1
        page_size = 100
        
        print("청년정책 수집 시작...")
        
        # 첫 페이지로 전체 개수 확인
        first_result = await self.get_policy_list(page_index, page_size)
        total_count = first_result["total_count"]
        all_policies.extend(first_result["policies"])
        
        print(f"전체 정책 수: {total_count}개")
        
        if total_count == 0:
            return []
        
        # 전체 페이지 수 계산
        total_pages = (total_count + page_size - 1) // page_size
        
        # 나머지 페이지 수집
        for page in range(2, total_pages + 1):
            print(f"페이지 {page}/{total_pages} 수집 중...")
            
            result = await self.get_policy_list(page, page_size)
            all_policies.extend(result["policies"])
            
            # API 부하 방지를 위한 대기
            await asyncio.sleep(0.5)
        
        print(f"수집 완료: {len(all_policies)}개 정책")
        return all_policies
    
    def process_policy_data(self, raw_policy: Dict) -> Dict:
        """원시 정책 데이터를 DB 모델에 맞게 가공"""
        
        # 신청 URL 생성 (없으면 온라인청년센터 상세페이지 링크)
        application_url = raw_policy.get("rqutUrla", "")
        if not application_url:
            policy_id = raw_policy.get("bizId", "")
            application_url = f"https://www.youthcenter.go.kr/youngPlcyUnif/youngPlcyUnifDtl.do?bizId={policy_id}"
        
        # 연령 정보 처리
        age_info = raw_policy.get("ageInfo", "")
        
        # 대상 설명 생성
        target_desc_parts = []
        if raw_policy.get("majrRqisCn"):
            target_desc_parts.append(f"전공: {raw_policy['majrRqisCn']}")
        if raw_policy.get("empmSttsCn"):
            target_desc_parts.append(f"취업상태: {raw_policy['empmSttsCn']}")
        if raw_policy.get("splzRlmRqisCn"):
            target_desc_parts.append(f"특화분야: {raw_policy['splzRlmRqisCn']}")
        
        target_desc = " / ".join(target_desc_parts) if target_desc_parts else ""
        
        # 지원 내용 (정책 소개 + 지원 내용 결합)
        support_content_parts = []
        if raw_policy.get("polyItcnCn"):
            support_content_parts.append(raw_policy["polyItcnCn"])
        if raw_policy.get("sporCn"):
            support_content_parts.append(raw_policy["sporCn"])
        
        support_content = "\n\n".join(support_content_parts) if support_content_parts else ""
        
        return {
            "policy_id": raw_policy.get("bizId", ""),
            "policy_name": raw_policy.get("polyBizSjnm", ""),
            "support_content": support_content,
            "application_url": application_url,
            "organization": raw_policy.get("cnsgNmor", ""),
            "target_age": age_info,
            "target_desc": target_desc,
            "support_scale": "",  # API에서 제공하지 않음
            "application_period": raw_policy.get("rqutPrdCn", ""),
            "tags": []  # 태그 매핑 제거 (벡터 검색 사용)
        }


async def test_client():
    """클라이언트 테스트"""
    async with YouthPolicyClient() as client:
        # 첫 페이지 테스트
        result = await client.get_policy_list(1, 10)
        print(f"테스트 결과: {result['total_count']}개 중 {len(result['policies'])}개 수집")
        
        if result["policies"]:
            # 첫 번째 정책 상세 확인
            first_policy = result["policies"][0]
            print(f"\n첫 번째 정책:")
            print(f"- ID: {first_policy.get('bizId')}")
            print(f"- 정책명: {first_policy.get('polyBizSjnm')}")
            
            # 가공 테스트
            processed = client.process_policy_data(first_policy)
            print(f"\n가공된 데이터:")
            for key, value in processed.items():
                if value and key != "support_content":  # support_content는 너무 길어서 제외
                    print(f"- {key}: {value[:100] if isinstance(value, str) else value}")


if __name__ == "__main__":
    # 환경변수 로드
    from dotenv import load_dotenv
    load_dotenv()
    
    # 테스트 실행
    asyncio.run(test_client())