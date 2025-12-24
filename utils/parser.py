import re
from typing import List, Dict, Any
from models.voice import MENU_DB, OPTION_DB, get_menu_info, get_option_info


def process_commands(llm_output: str) -> List[Dict[str, Any]]:
    """
    LLM 출력을 파싱하여 주문 액션 리스트로 변환
    
    Args:
        llm_output: LLM이 반환한 명령어 문자열
        
    Returns:
        주문 액션 리스트
    """
    actions = []
    if not llm_output:
        return actions

    lines = llm_output.strip().split('\n')
    for line in lines:
        try:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 1:
                continue
            
            command = parts[0].upper()
            
            # CLEAR 명령어 처리
            if command == "CLEAR":
                actions.append({"type": "CLEAR"})
                continue

            # REMOVE 명령어 처리
            if command == "REMOVE":
                if len(parts) < 2:
                    continue
                    
                qty_str = parts[2] if len(parts) > 2 else "1"
                match = re.search(r'\d+', qty_str)
                qty = int(match.group()) if match else 1

                target_mode = "last"
                if len(parts) > 3 and "first" in parts[3].lower():
                    target_mode = "first"
                
                actions.append({
                    "type": "REMOVE",
                    "id": parts[1],
                    "data": {"quantity": qty, "mode": target_mode}
                })
                continue

            # ADD / UPDATE 명령어 처리
            if command in ["ADD", "UPDATE"]:
                if len(parts) < 2:
                    continue
                
                target_id = parts[1]
                new_menu_id = parts[2] if command == "UPDATE" else parts[1]
                qty_idx = 3 if command == "UPDATE" else 2
                opt_idx = 4 if command == "UPDATE" else 3
                
                # 수량 파싱
                qty_str = parts[qty_idx] if len(parts) > qty_idx else "1"
                match = re.search(r'\d+', qty_str)
                qty = int(match.group()) if match else 1

                # 메뉴 검증
                if new_menu_id not in MENU_DB:
                    continue
                menu_info = get_menu_info(new_menu_id)

                # 옵션 파싱
                if len(parts) > opt_idx:
                    option_str = parts[opt_idx]
                    raw_options = [o.strip() for o in option_str.split(',') if o.strip()]
                else:
                    raw_options = []
                
                valid_option_ids = [o for o in raw_options if o in OPTION_DB]

                # ADD의 경우 기본 옵션 추가
                if command == "ADD":
                    has_temp = any(o in ['ice', 'cold', 'hot'] for o in valid_option_ids)
                    has_size = any(o in ['tall', 'grande', 'venti'] for o in valid_option_ids)
                    
                    for def_opt in menu_info.get("default_options", []):
                        if def_opt in ['hot', 'cold'] and has_temp:
                            continue
                        if def_opt in ['tall', 'grande', 'venti'] and has_size:
                            continue
                        if def_opt not in valid_option_ids:
                            valid_option_ids.append(def_opt)

                # 가격 계산
                total_price = menu_info["price"]
                option_names = []
                for opt_id in valid_option_ids:
                    opt_info = get_option_info(opt_id)
                    total_price += opt_info["price"]
                    option_names.append(opt_info["name"])
                
                total_price *= qty
                
                # 액션 데이터 구성
                action_data = {
                    "id": new_menu_id,
                    "name": menu_info["name"],
                    "options": option_names,
                    "option_ids": valid_option_ids,
                    "price": total_price,
                    "quantity": qty
                }

                if command == "UPDATE":
                    actions.append({
                        "type": "UPDATE",
                        "targetId": target_id,
                        "data": action_data
                    })
                else:
                    actions.append({
                        "type": "ADD",
                        "data": action_data
                    })

        except Exception as e:
            print(f"⚠️ 파싱 에러: {e}")
            continue
            
    return actions


def extract_quantity(text: str) -> int:
    """
    텍스트에서 수량 추출
    
    Args:
        text: 수량이 포함된 텍스트
        
    Returns:
        추출된 수량 (기본값 1)
    """
    match = re.search(r'\d+', text)
    return int(match.group()) if match else 1