"""
메뉴 및 옵션 API 클라이언트
기존 더미 데이터를 실제 API 호출로 교체
"""

import os
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MenuAPIClient:
    """백엔드 API 클라이언트 - AI 시작시 1회 호출, 종료시까지 사용"""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            base_url = os.getenv("BACKEND_API_URL", "http://localhost:8080/nok-nok")
        self.base_url = base_url
        self.cache = {}
        self.cache_loaded = False  # 캐시 로드 완료 플래그
        self.session = requests.Session()
        
    def _get_api_data(self) -> Optional[Dict]:
        """API에서 전체 데이터 조회 (AI 시작시 1회만, 성공할 때까지 재시도)"""
        # 이미 로드되었으면 캐시 반환
        if self.cache_loaded and self.cache:
            return self.cache
        
        # 최초 호출시에만 API 요청 (성공할 때까지 재시도)
        if not self.cache_loaded:
            max_retries = 10  # 최대 10회 시도
            retry_delay = 3   # 3초 간격
            
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"🔄 메뉴 데이터 로드 시도 {attempt}/{max_retries}...")
                    url = f"{self.base_url}/api/ai/complete-data"
                    response = self.session.get(url, timeout=15)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # 데이터 유효성 검증
                    if not data or not data.get('menus') or data.get('totalMenus', 0) == 0:
                        raise ValueError("API 응답 데이터가 비어있음")
                    
                    # 캐시 저장
                    self.cache = data
                    self.cache_loaded = True
                    
                    
                    
                    logger.info(f"✅ 메뉴 데이터 로드 성공! - 메뉴: {data.get('totalMenus', 0)}개")
                    logger.info("📋 AI 종료시까지 이 데이터 사용")
                    return data
                    
                except Exception as e:
                    logger.warning(f"❌ API 호출 실패 ({attempt}/{max_retries}): {str(e)}")
                    
                    if attempt < max_retries:
                        logger.info(f"⏳ {retry_delay}초 후 재시도...")
                        import time
                        time.sleep(retry_delay)
                    else:
                        logger.error("💀 모든 재시도 실패! AI 음성인식을 시작할 수 없습니다.")
                        logger.error("🔧 해결방법:")
                        logger.error("   1. 백엔드 서버가 실행중인지 확인: docker-compose ps")
                        logger.error("   2. API 엔드포인트 확인: curl http://localhost:8080/api/ai/complete-data")
                        logger.error("   3. 네트워크 연결 상태 확인")
                        logger.error("   4. 백엔드 로그 확인: docker-compose logs backend")
                        raise RuntimeError(f"API 연결 실패 - {max_retries}회 재시도 후 포기")
        
        # 이미 로드된 캐시 반환
        return self.cache
    
    def get_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 정보 반환"""
        return {
            "cache_loaded": self.cache_loaded,
            "menu_count": len(self.cache.get('menus', [])) if self.cache else 0,
            "option_groups": self.cache.get('totalOptionGroups', 0) if self.cache else 0,
            "data_source": "API" if self.cache_loaded else "NOT_LOADED"
        }

# 전역 API 클라이언트 인스턴스
_api_client = MenuAPIClient()

# 음성 키워드 매핑 (실제 DB 구조 기준)
VOICE_KEYWORD_MAPPING = {
    # 메뉴명 매핑 (실제 DB 메뉴명 → 음성 키워드들)
    "아메리카노": ["americano", "아메", "아메리카노"],
    "카페라떼": ["latte", "라떼", "카페라떼"],
    "카푸치노": ["cappuccino", "카푸치노", "카푸"],
    "카라멜 마키아또": ["caramel_macchiato", "카라멜", "마키아또", "카라멜마키아또"],
    "바닐라 라떼": ["vanilla_latte", "바닐라", "바닐라라떼", "바닐라라떼"],
    "카페모카": ["mocha", "모카", "카페모카"],
    "에스프레소": ["espresso", "에스프레소", "esspresso"],
    "콜드브루": ["coldbrew", "콜드브루", "콜드"],
    "플랫화이트": ["flatwhite", "플랫화이트", "플랫"],
    "아인슈페너": ["einspanner", "아인슈페너"],
    "헤이즐넛 라떼": ["hazelnut_latte", "헤이즐넛", "헤이즐넛라떼"],
    "연유 라떼": ["condensed_latte", "연유", "연유라떼"],
    "디카페인 아메리카노": ["decaf_americano", "디카페인", "디카페인아메리카노"],
    "디카페인 라떼": ["decaf_latte", "디카페인라떼"],
    "더치커피": ["dutch_coffee", "더치", "더치커피"],
    "레몬에이드": ["lemonade", "레몬", "레몬에이드"],
    "자몽에이드": ["grapefruit_ade", "자몽", "자몽에이드"],
    "청포도에이드": ["grape_ade", "청포도", "청포도에이드"],
    "딸기라떼": ["strawberry_latte", "딸기", "딸기라떼", "straw_latte"],
    "초코라떼": ["chocolate_latte", "초코", "초코라떼", "choco_latte"],
    "녹차라떼": ["greentea_latte", "녹차", "녹차라떼"],
    "흑당라떼": ["brown_sugar_latte", "흑당", "흑당라떼"],
    "밀크티": ["milk_tea", "밀크티"],
    "유자차": ["yuzu_tea", "유자", "유자차", "citron_tea"],
    "페퍼민트": ["peppermint", "페퍼민트", "페퍼민트티"],
    # 디저트
    "치즈케이크": ["cheesecake", "치즈케이크", "치즈", "choco_cake"],
    "티라미수": ["tiramisu", "티라미수"],
    "초코 브라우니": ["choco_brownie", "초코브라우니", "브라우니", "초코"],
    "마카롱 세트": ["macaron_set", "마카롱", "마카롱세트", "rainbow_cake"],
    "쿠키 세트": ["cookie_set", "쿠키", "쿠키세트", "salt_bread"],
    
    # ✅ 실제 DB 옵션명 매핑 (정확한 옵션명 사용)
    "HOT": ["hot", "따뜻하게", "뜨겁게", "핫"],
    "ICE": ["cold", "아이스", "차갑게", "아아", "냉"],
    
    # 사이즈 (실제 DB: 톨(Tall), 그란데(Grande), 벤티(Venti))
    "톨(Tall)": ["tall", "톨", "작은거", "스몰", "스몰사이즈"],
    "그란데(Grande)": ["grande", "그란데", "중간사이즈", "미디엄", "보통"],
    "벤티(Venti)": ["venti", "벤티", "큰거", "라지", "라지사이즈", "라지 사이즈"],
    
    # 얼음량 (실제 DB: 적게, 보통, 많이)
    "적게": ["less_ice", "얼음적게", "얼음조금", "얼음 적게"],
    "보통": ["normal_ice", "얼음보통", "얼음 보통"],
    "많이": ["more_ice", "얼음많이", "얼음추가", "얼음 많이"],
    
    # 샷 추가
    "샷 추가": ["shot", "샷추가", "샷"],
    
    # 휘핑 크림 (DB에 새로 추가됨)
    "휘핑 크림 없음": ["whip_none", "휘핑없음", "휘핑크림없음"],
    "휘핑 크림 추가": ["whip", "휘핑", "휘핑크림", "힙", "휩", "휘핑크림추가"]
}

def get_menu_info(menu_id: str) -> Optional[Dict]:
    """
    메뉴 정보 조회 (기존 인터페이스 호환)
    
    Args:
        menu_id: 음성 키워드 또는 메뉴명
        
    Returns:
        메뉴 정보 딕셔너리 (기존 형식과 호환)
    """
    try:
        api_data = _api_client._get_api_data()
        if not api_data:
            return None
        
        # 1. 직접 메뉴명 매칭
        for menu in api_data["menus"]:
            if menu["name"] == menu_id:
                return {
                    "name": menu["name"],
                    "price": menu["price"],
                    "default_options": _get_default_options_for_menu(menu["menuId"], api_data)
                }
        
        # 2. 음성 키워드 매칭
        for menu_name, keywords in VOICE_KEYWORD_MAPPING.items():
            if menu_id in keywords:
                # API 데이터에서 해당 메뉴 찾기
                for menu in api_data["menus"]:
                    if menu["name"] == menu_name:
                        return {
                            "name": menu["name"],
                            "price": menu["price"],
                            "default_options": _get_default_options_for_menu(menu["menuId"], api_data)
                        }
        
        return None
        
    except Exception as e:
        logger.error(f"메뉴 정보 조회 실패: {str(e)}")
        return None

def _get_default_options_for_menu(menu_id: int, api_data: Dict) -> List[str]:
    """메뉴의 기본 옵션들 추출 (기존 형식으로 변환)"""
    try:
        menu_options = api_data.get("menuOptions", {}).get(str(menu_id))
        if not menu_options:
            return []
        
        defaults = []
        for group in menu_options.get("optionGroups", []):
            if group.get("isRequired", False):
                # 필수 그룹의 첫 번째 옵션을 기본값으로 사용
                options = group.get("options", [])
                if options:
                    option_name = options[0]["name"]
                    # API 옵션명을 기존 시스템 키워드로 변환
                    mapped_keyword = _map_option_to_keyword(option_name)
                    if mapped_keyword:
                        defaults.append(mapped_keyword)
        
        return defaults
        
    except Exception as e:
        logger.error(f"기본 옵션 추출 실패: {str(e)}")
        return []

def _map_option_to_keyword(option_name: str) -> Optional[str]:
    """API 옵션명을 기존 시스템 키워드로 매핑 (실제 DB 구조 기반)"""
    mapping = {
        "HOT": "hot",
        "ICE": "cold", 
        "톨(Tall)": "tall",           # 실제 DB 옵션명
        "그란데(Grande)": "grande",    # 실제 DB 옵션명 
        "벤티(Venti)": "venti",       # 실제 DB 옵션명
        "적게": "less_ice",           # 실제 DB 옵션명
        "보통": "normal_ice",         # 실제 DB 옵션명  
        "많이": "more_ice",           # 실제 DB 옵션명
        "샷 추가": "shot",
        "휘핑 크림 없음": "whip_none", # 새로 추가됨
        "휘핑 크림 추가": "whip"       # 새로 추가됨
    }
    return mapping.get(option_name)

def get_option_info(option_id: str) -> Optional[Dict]:
    """
    옵션 정보 조회 (기존 인터페이스 호환)
    실제 DB 구조 기반으로 수정
    
    Args:
        option_id: 옵션 키워드
        
    Returns:
        옵션 정보 딕셔너리 (기존 형식과 호환)
    """
    try:
        # 실제 DB 구조와 호환성을 위한 매핑
        option_mapping = {
            "hot": {"name": "따뜻하게", "price": 0},
            "cold": {"name": "아이스", "price": 0},
            "tall": {"name": "톨 사이즈", "price": 0},          # 실제 DB: 톨(Tall) 
            "grande": {"name": "그란데 사이즈", "price": 500},    # 실제 DB: 그란데(Grande)
            "venti": {"name": "벤티 사이즈", "price": 1000},     # 실제 DB: 벤티(Venti)
            "less_ice": {"name": "얼음 적게", "price": 0},      # 실제 DB: 적게
            "normal_ice": {"name": "얼음 보통", "price": 0},     # 실제 DB: 보통
            "more_ice": {"name": "얼음 많이", "price": 0},       # 실제 DB: 많이
            "shot": {"name": "샷 추가", "price": 500},
            "whip_none": {"name": "휘핑 크림 없음", "price": 0}, # 새로 추가됨
            "whip": {"name": "휘핑 크림", "price": 500},         # 새로 추가됨
            "weak": {"name": "연하게", "price": 0}              # DB에 없음 (폴백)
        }
        
        return option_mapping.get(option_id)
        
    except Exception as e:
        logger.error(f"옵션 정보 조회 실패: {str(e)}")
        return None

def get_all_menu_ids() -> List[str]:
    """
    모든 메뉴 ID 반환 (LLM 프롬프트용)
    API 데이터를 기반으로 음성 키워드 생성
    """
    try:
        api_data = _api_client._get_api_data()
        if not api_data:
            raise RuntimeError("API 데이터 로드 실패 - AI를 재시작해주세요")
        
        # API 메뉴명 + 음성 키워드 조합
        all_keywords = []
        
        for menu in api_data["menus"]:
            menu_name = menu["name"]
            all_keywords.append(menu_name)  # 실제 메뉴명
            
            # 매핑된 키워드들 추가
            keywords = VOICE_KEYWORD_MAPPING.get(menu_name, [])
            all_keywords.extend(keywords)
        
        # 중복 제거
        unique_keywords = list(set(all_keywords))
        
        logger.info(f"LLM 프롬프트용 메뉴 키워드 {len(unique_keywords)}개 생성")
        return unique_keywords
        
    except Exception as e:
        logger.error(f"메뉴 ID 목록 생성 실패: {str(e)}")
        raise RuntimeError("메뉴 데이터가 로드되지 않았습니다. AI를 재시작해주세요.")

def get_all_option_ids() -> List[str]:
    """
    모든 옵션 ID 반환 (LLM 프롬프트용)
    API 데이터를 기반으로 음성 키워드 생성
    """
    try:
        api_data = _api_client._get_api_data()
        if not api_data:
            raise RuntimeError("API 데이터 로드 실패 - AI를 재시작해주세요")
        
        # API 옵션명 + 음성 키워드 조합
        all_keywords = []
        
        for menu_options in api_data["menuOptions"].values():
            for group in menu_options.get("optionGroups", []):
                for option in group.get("options", []):
                    option_name = option["name"]
                    all_keywords.append(option_name)  # 실제 옵션명
                    
                    # 매핑된 키워드들 추가
                    keywords = VOICE_KEYWORD_MAPPING.get(option_name, [])
                    all_keywords.extend(keywords)
        
        # 기존 시스템 호환 키워드도 추가
        legacy_options = ["hot", "cold", "tall", "grande", "venti", "less_ice", 
                         "normal_ice", "more_ice", "shot", "whip", "weak"]
        all_keywords.extend(legacy_options)
        
        # 중복 제거
        unique_keywords = list(set(all_keywords))
        
        logger.info(f"LLM 프롬프트용 옵션 키워드 {len(unique_keywords)}개 생성")
        return unique_keywords
        
    except Exception as e:
        logger.error(f"옵션 ID 목록 생성 실패: {str(e)}")
        raise RuntimeError("옵션 데이터가 로드되지 않았습니다. AI를 재시작해주세요.")

def test_api_connection() -> bool:
    """API 연결 테스트 및 캐시 상태 확인"""
    try:
        # API 데이터 확인
        data = _api_client._get_api_data()
        cache_status = _api_client.get_cache_status()
        
        logger.info(f"📊 캐시 상태: {cache_status}")
        
        if data and data.get("totalMenus", 0) > 0:
            logger.info("✅ API 연결 및 데이터 로드 성공")
            logger.info(f"📋 메뉴: {data.get('totalMenus')}개, 옵션 그룹: {data.get('totalOptionGroups')}개")
            return True
        else:
            logger.warning("❌ API 연결 실패 또는 데이터 없음")
            return False
            
    except Exception as e:
        logger.error(f"❌ API 연결 테스트 실패: {str(e)}")
        return False

def get_cache_info() -> Dict[str, Any]:
    """캐시 정보 조회 (디버깅용)"""
    return _api_client.get_cache_status()

# 기존 더미 데이터 (참조용, 사용하지 않음)
MENU_DB = {}  # 비워둠
OPTION_DB = {}  # 비워둠