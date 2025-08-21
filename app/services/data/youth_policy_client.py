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
        
        self.base_url = "https://www.youthcenter.go.kr/opi"  # XML API용
        self.web_url = "https://www.youthcenter.go.kr/go/ythip"  # JSON API용
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
        """정책 목록 조회 - JSON API 사용"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.web_url}/getPlcy"
        params = {
            "apiKeyNm": self.api_key,  # 필수 파라미터
            "pageNum": page_index,     # pageIndex -> pageNum
            "pageSize": page_size,
            "rtnType": "json"          # JSON 응답 요청
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    text = await response.text()
                    
                    # JSON 파싱
                    import json
                    json_data = json.loads(text)
                    
                    # 실제 응답 구조: result 안에 youthPolicyList와 pagging이 있음
                    result = json_data.get("result", {})
                    policies = result.get("youthPolicyList", [])
                    
                    # 페이징 정보에서 전체 개수 가져오기
                    paging = result.get("pagging", {})
                    total_count = paging.get("totCount", len(policies))
                    
                    return {
                        "total_count": total_count,
                        "policies": policies
                    }
                else:
                    text = await response.text()
                    raise Exception(f"API 요청 실패: {response.status} - {text}")
        except Exception as e:
            print(f"API 요청 중 오류: {e}")
            raise
    
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
        """원시 정책 데이터를 DB 모델에 맞게 가공 - JSON 응답용"""
        
        # API 문서 기준 필드명 매핑
        policy_id = raw_policy.get("plcyNo", "")
        policy_name = raw_policy.get("plcyNm", "")
        
        # 신청 URL 처리
        application_url = raw_policy.get("aplyUrlAddr", "")
        if not application_url:
            application_url = f"https://www.youthcenter.go.kr/youngPlcyUnif/youngPlcyUnifDtl.do?plcyNo={policy_id}"
        
        # 연령 정보
        age_min = raw_policy.get("sprtTrgtMinAge", "")
        age_max = raw_policy.get("sprtTrgtMaxAge", "")
        target_age = f"{age_min}세~{age_max}세" if age_min and age_max else ""
        
        # 대상 설명 - 추가 신청자격 조건
        target_desc = raw_policy.get("addAplyQlfcCndCn", "")
        
        # 지원 내용 - 정책설명 + 정책지원내용
        support_content = raw_policy.get("plcyExplnCn", "")
        if raw_policy.get("plcySprtCn"):
            support_content = f"{support_content}\n\n{raw_policy['plcySprtCn']}"
        
        # 신청 기간
        application_period = raw_policy.get("aplyYmd", "")
        
        return {
            "policy_id": str(policy_id),
            "policy_name": policy_name,
            "support_content": support_content,
            "application_url": application_url,
            "organization": raw_policy.get("operInstCdNm", ""),  # 운영기관코드명
            "target_age": target_age,
            "target_desc": target_desc,
            "support_scale": raw_policy.get("sprtSclCnt", ""),  # 지원규모수
            "application_period": application_period,
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
            print(f"- ID: {first_policy.get('plcyNo')}")
            print(f"- 정책명: {first_policy.get('plcyNm')}")
            print(f"- 기관: {first_policy.get('operInstCdNm')}")
            print(f"- 신청URL: {first_policy.get('aplyUrlAddr', '없음')}")
            
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