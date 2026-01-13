"""
비접촉 터치 독립 실행 스크립트
test_gesture_visual.py

화면 표시와 함께 제스처 인식을 테스트합니다.
FastAPI 서버 없이 독립적으로 실행됩니다.
✅ 클릭 및 스크롤 기능 포함
"""

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import subprocess

# PyAutoGUI 설정
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# 화면 크기
screen_w, screen_h = pyautogui.size()

# ==================== 인식 거리 설정 ====================
# 값을 낮추면 멀리서도 인식 (0.3~0.7 권장)
# 값을 높이면 가까이서만 인식 (0.7~0.9)
MIN_DETECTION_CONFIDENCE = 0.7  # 기본: 0.7, 멀리서 인식하려면 0.5
MIN_TRACKING_CONFIDENCE = 0.5   # 기본: 0.5
# ========================================================

# MediaPipe Hands 초기화
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=MIN_DETECTION_CONFIDENCE,  # ← 인식 거리 설정
    min_tracking_confidence=MIN_TRACKING_CONFIDENCE
)

# 카메라 초기화
CAMERA_INDEX = 0  # 작동하는 카메라 인덱스
cap = cv2.VideoCapture(CAMERA_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print(f"❌ 카메라 {CAMERA_INDEX}를 열 수 없습니다.")
    print("다른 인덱스를 시도해보세요: 0, 1, 2")
    exit(1)

print(f"✅ 카메라 {CAMERA_INDEX} 열림")
print(f"🎯 인식 거리 설정: {MIN_DETECTION_CONFIDENCE}")
print("💡 손바닥을 2초간 보여주면 활성화")
print("💡 활성화 후:")
print("   - 검지 손가락: 마우스 이동")
print("   - 엄지+검지 핀치: 클릭")
print("   - 주먹 위아래: 스크롤")
print("💡 ESC 키로 종료\n")

# 상태 변수
system_active = False
prev_x = screen_w // 2
prev_y = screen_h // 2
palm_show_start_time = None
last_hand_detected_time = None

# 제스처 상태
fist_mode = False
fist_start_y = None
pinch_down = False
last_click_time = 0

# 설정
PALM_HOLD_DURATION = 2.0
NO_HAND_TIMEOUT = 2.0
SMOOTHING = 2
PINCH_THRESHOLD = 40
SCROLL_THRESHOLD = 25
SCROLL_SENSITIVITY = 120
CLICK_COOLDOWN = 0.2

# 커서 숨기기/표시 (macOS)
def hide_cursor():
    try:
        subprocess.run(['python3', '-c', 'import Quartz; Quartz.CGDisplayHideCursor(0)'],
                      capture_output=True, timeout=0.5)
    except:
        pass

def show_cursor():
    try:
        subprocess.run(['python3', '-c', 'import Quartz; Quartz.CGDisplayShowCursor(0)'],
                      capture_output=True, timeout=0.5)
    except:
        pass

# 손바닥 인식
def is_palm_open(landmarks):
    fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_open = abs(thumb_tip.x - thumb_ip.x) > 0.04
    fingers_open = sum(1 for tip_id, pip_id in fingers 
                      if landmarks[tip_id].y < landmarks[pip_id].y)
    return thumb_open and fingers_open >= 3

# 주먹 인식
def is_fist(landmarks):
    finger_tip_ids = [8, 12, 16, 20]
    finger_dip_ids = [5, 9, 13, 17]
    folded_count = sum(1 for tip_id, dip_id in zip(finger_tip_ids, finger_dip_ids)
                      if landmarks[tip_id].y > landmarks[dip_id].y)
    return folded_count >= 3

# 커서 이동
def move_cursor(landmarks):
    global prev_x, prev_y
    index_tip = landmarks[5]
    
    # 80% 영역 매핑
    mapped_x = (index_tip.x - 0.1) / 0.8
    mapped_y = (index_tip.y - 0.1) / 0.8
    mapped_x = max(0.0, min(1.0, mapped_x))
    mapped_y = max(0.0, min(1.0, mapped_y))
    
    x = int(mapped_x * screen_w)
    y = int(mapped_y * screen_h)
    
    # 스무딩
    cur_x = prev_x + (x - prev_x) / SMOOTHING
    cur_y = prev_y + (y - prev_y) / SMOOTHING
    
    pyautogui.moveTo(cur_x, cur_y)
    prev_x, prev_y = cur_x, cur_y

# 핀치 클릭
def handle_pinch_click(landmarks):
    global pinch_down, last_click_time
    
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    
    # 80% 영역 매핑
    thumb_x = (thumb_tip.x - 0.1) / 0.8
    thumb_y = (thumb_tip.y - 0.1) / 0.8
    index_x = (index_tip.x - 0.1) / 0.8
    index_y = (index_tip.y - 0.1) / 0.8
    
    tx = int(thumb_x * screen_w)
    ty = int(thumb_y * screen_h)
    ix = int(index_x * screen_w)
    iy = int(index_y * screen_h)
    
    dist = np.hypot(ix - tx, iy - ty)
    now = time.time()
    
    if dist < PINCH_THRESHOLD and not pinch_down:
        if now - last_click_time > CLICK_COOLDOWN:
            pinch_down = True
            last_click_time = now
            pyautogui.click()
            print("🖱️  클릭!")
    elif dist >= PINCH_THRESHOLD and pinch_down:
        pinch_down = False

# 스크롤
def handle_scroll(landmarks):
    global fist_start_y
    
    base_point = landmarks[0]
    mapped_y = (base_point.y - 0.1) / 0.8
    cy = int(mapped_y * screen_h)
    
    if fist_start_y is None:
        fist_start_y = cy
        return
    
    dy = cy - fist_start_y
    
    if abs(dy) > SCROLL_THRESHOLD:
        scroll_amount = int(dy / SCROLL_SENSITIVITY * 10)
        pyautogui.scroll(scroll_amount)
        print(f"🔄 스크롤: {scroll_amount}")
        fist_start_y = cy

# 화면 표시
def draw_debug_info(frame, results):
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    display = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    h, w, _ = display.shape
    
    # 80% 인식 영역 표시
    margin_x = int(w * 0.1)
    margin_y = int(h * 0.1)
    cv2.rectangle(display, (margin_x, margin_y), (w - margin_x, h - margin_y), 
                (100, 100, 100), 1)
    
    # 상태바
    overlay = display.copy()
    cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)
    
    # 손 랜드마크
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            if system_active:
                landmark_color = (0, 255, 0)
                connection_color = (255, 255, 0)
            else:
                landmark_color = (150, 150, 150)
                connection_color = (100, 100, 100)
            
            mp_drawing.draw_landmarks(
                display, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=landmark_color, thickness=2, circle_radius=2),
                mp_drawing.DrawingSpec(color=connection_color, thickness=2)
            )
            
            # 커서 기준점 (빨간 점)
            if system_active:
                index_mcp = hand_landmarks.landmark[5]
                cx = int(index_mcp.x * w)
                cy = int(index_mcp.y * h)
                cv2.circle(display, (cx, cy), 8, (0, 0, 255), -1)
                cv2.circle(display, (cx, cy), 10, (0, 0, 255), 2)
    
    # 텍스트
    font = cv2.FONT_HERSHEY_SIMPLEX
    status_color = (0, 255, 0) if system_active else (0, 0, 255)
    status_text = "ACTIVE" if system_active else "INACTIVE"
    cv2.putText(display, f"Status: {status_text}", (10, 30), 
               font, 0.7, status_color, 2)
    
    if palm_show_start_time and not system_active:
        elapsed = time.time() - palm_show_start_time
        remaining = max(0, PALM_HOLD_DURATION - elapsed)
        cv2.putText(display, f"Activating... {remaining:.1f}s", (10, 60),
                   font, 0.6, (0, 255, 255), 2)
    
    # 모드 표시
    if system_active:
        y_offset = 60
        if fist_mode:
            cv2.putText(display, "Mode: FIST (Scroll)", (10, y_offset),
                       font, 0.6, (255, 165, 0), 2)
        elif pinch_down:
            cv2.putText(display, "Mode: PINCH (Clicking)", (10, y_offset),
                       font, 0.6, (255, 0, 255), 2)
        else:
            cv2.putText(display, "Mode: MOVE", (10, y_offset),
                       font, 0.6, (255, 255, 255), 2)
    
    if results.multi_hand_landmarks:
        cv2.putText(display, f"Hands: {len(results.multi_hand_landmarks)}", (10, 90),
                   font, 0.6, (0, 255, 0), 2)
    else:
        if system_active and last_hand_detected_time:
            time_since = time.time() - last_hand_detected_time
            remaining = max(0, NO_HAND_TIMEOUT - time_since)
            cv2.putText(display, f"No hand: {remaining:.1f}s", (10, 90),
                       font, 0.6, (0, 165, 255), 2)
    
    help_text = "ESC: Quit | Palm 2s: Activate | Pinch: Click | Fist: Scroll"
    cv2.putText(display, help_text, (10, h - 20), font, 0.5, (200, 200, 200), 1)
    
    return display

# 초기 커서 숨김
hide_cursor()

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # 프레임 처리
        frame_flip = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame_flip, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)
        
        hand_detected = False
        
        if results.multi_hand_landmarks:
            hand_detected = True
            last_hand_detected_time = time.time()
            
            primary_hand = results.multi_hand_landmarks[0]
            lm = primary_hand.landmark
            
            # 활성화 체크
            if is_palm_open(lm) and not system_active:
                if palm_show_start_time is None:
                    palm_show_start_time = time.time()
                    print("✋ 손바닥 감지 시작")
                else:
                    elapsed = time.time() - palm_show_start_time
                    if elapsed >= PALM_HOLD_DURATION:
                        system_active = True
                        show_cursor()
                        print("✅ 시스템 활성화!")
                        palm_show_start_time = None
            else:
                palm_show_start_time = None
            
            # 활성화 상태에서 제어
            if system_active and not is_palm_open(lm):
                # 커서 이동
                move_cursor(lm)
                
                # 주먹 모드 체크
                fist_now = is_fist(lm)
                
                if fist_now and not fist_mode:
                    fist_mode = True
                    print("👊 주먹 모드 (스크롤)")
                elif not fist_now and fist_mode:
                    fist_mode = False
                    fist_start_y = None
                    print("👆 일반 모드 (마우스/클릭)")
                
                # 제스처 처리
                if fist_mode:
                    handle_scroll(lm)
                else:
                    handle_pinch_click(lm)
        
        # 자동 비활성화
        if not hand_detected and system_active and last_hand_detected_time:
            if time.time() - last_hand_detected_time >= NO_HAND_TIMEOUT:
                system_active = False
                hide_cursor()
                fist_mode = False
                print("⏱️  자동 비활성화")
                last_hand_detected_time = None
        
        # 화면 표시
        display_frame = draw_debug_info(frame, results)
        cv2.imshow('Non-Touch Control Test', display_frame)
        
        # ESC 키로 종료
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            print("ESC 키로 종료")
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    show_cursor()
    print("종료 완료")