"""
메뉴 및 옵션 데이터베이스
"""

# 메뉴 데이터베이스
MENU_DB = {
    "americano": {"name": "아메리카노", "price": 4000, "default_options": ["hot", "grande"]},
    "latte": {"name": "카페라떼", "price": 5000, "default_options": ["hot", "grande"]},
    "vanilla_latte": {"name": "바닐라라떼", "price": 5000, "default_options": ["hot", "grande"]},
    "caramel_latte": {"name": "카라멜 라떼", "price": 5000, "default_options": ["hot", "grande"]},
    "choco_latte": {"name": "초코 라떼", "price": 5000, "default_options": ["cold", "grande"]},
    "straw_latte": {"name": "딸기 라떼", "price": 6000, "default_options": ["cold", "grande"]},
    "salted_caramell_latte": {"name": "솔티드 카라멜 라떼", "price": 6000, "default_options": ["cold", "grande"]},
    "esspresso": {"name": "에스프레소", "price": 4000, "default_options": ["hot", "grande"]},
    "affogato": {"name": "아포카토", "price": 4500, "default_options": []},
    "peach_icetea": {"name": "복숭아 아이스티", "price": 4000, "default_options": ["cold", "grande"]},
    "chamomile": {"name": "캐모마일 티", "price": 3000, "default_options": ["hot", "grande"]},
    "peppermint": {"name": "페퍼민트 티", "price": 3000, "default_options": ["hot", "grande"]},
    "choco_cake": {"name": "초코 케이크", "price": 5500, "default_options": []},
    "rainbow_cake": {"name": "레인보우 케이크", "price": 6500, "default_options": []},
    "cheesecake": {"name": "치즈 케이크", "price": 6000, "default_options": []},
    "salt_bread": {"name": "소금빵", "price": 3500, "default_options": []},
    "last_item": {"name": "마지막 메뉴", "price": 0, "default_options": []}
}

# 옵션 데이터베이스
OPTION_DB = {
    "hot": {"name": "따뜻하게", "price": 0},
    "cold": {"name": "아이스", "price": 0},
    "tall": {"name": "톨 사이즈", "price": -500},
    "grande": {"name": "그란데 사이즈", "price": 0},
    "venti": {"name": "벤티 사이즈", "price": 500},
    "less_ice": {"name": "얼음 적게", "price": 0},
    "normal_ice": {"name": "얼음 보통", "price": 0},
    "more_ice": {"name": "얼음 많이", "price": 0},
    "shot": {"name": "샷 추가", "price": 500},
    "whip": {"name": "휘핑크림", "price": 0},
    "weak": {"name": "연하게", "price": 0}
}


def get_menu_info(menu_id: str):
    """메뉴 정보 조회"""
    return MENU_DB.get(menu_id)


def get_option_info(option_id: str):
    """옵션 정보 조회"""
    return OPTION_DB.get(option_id)


def get_all_menu_ids():
    """모든 메뉴 ID 반환"""
    return list(MENU_DB.keys())


def get_all_option_ids():
    """모든 옵션 ID 반환"""
    return list(OPTION_DB.keys())