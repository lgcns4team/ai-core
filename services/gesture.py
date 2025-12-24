"""
비접촉 터치 제스처 인식 서비스
services/gesture.py
"""

import cv2
import mediapipe as mp
import pyautogui
import numpy as np
import time
import threading
import subprocess
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class HandGestureService:
    """손 제스처 인식 및 제어 서비스"""
    
    def __init__(self, config: dict):
        """
        초기화
        
        Args:
            config: 설정 딕셔너리
                - camera_index: 카메라 인덱스 (기본: 0)
                - palm_hold_duration: 활성화 손바닥 유지 시간 (기본: 2.0초)
                - no_hand_timeout: 비활성화 타임아웃 (기본: 2.0초)
                - smoothing: 마우스 스무딩 (기본: 2)
                - pinch_threshold: 핀치 임계값 (기본: 40)
                - swipe_threshold: 스와이프 임계값 (기본: 100)
                - scroll_threshold: 스크롤 임계값 (기본: 25)
                - scroll_sensitivity: 스크롤 민감도 (기본: 120)
        """
        self.config = config
        
        # PyAutoGUI 설정
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        
        # 화면 크기
        self.screen_w, self.screen_h = pyautogui.size()
        
        # MediaPipe Hands 초기화
        self.mp_hands = mp.solutions.hands
        
        # 인식 거리 설정
        min_detection = config.get('min_detection_confidence', 0.5)  # 기본 0.5 (멀리서도 인식)
        min_tracking = config.get('min_tracking_confidence', 0.5)
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=min_detection,  # 낮을수록 멀리서도 인식 (0.3~0.7)
            min_tracking_confidence=min_tracking     # 추적 안정성
        )
        
        logger.info(f"손 인식 거리 설정 - detection: {min_detection}, tracking: {min_tracking}")
        
        # 카메라
        self.cap = None
        
        # 상태 변수
        self.system_active = False
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.cursor_hidden = False
        
        # 마우스 위치
        self.prev_x = self.screen_w // 2
        self.prev_y = self.screen_h // 2
        
        # 제스처 상태
        self.fist_mode = False
        self.fist_start_x, self.fist_start_y = None, None
        self.pinch_down = False
        self.last_click_time = 0
        self.last_swipe_time = 0
        
        # 활성화 관련
        self.palm_show_start_time = None
        self.last_hand_detected_time = None
        
        # 설정값
        self.PALM_HOLD_DURATION = config.get('palm_hold_duration', 2.0)
        self.NO_HAND_TIMEOUT = config.get('no_hand_timeout', 2.0)
        self.SMOOTHING = config.get('smoothing', 2)
        self.PINCH_THRESHOLD = config.get('pinch_threshold', 40)
        self.SWIPE_THRESHOLD = config.get('swipe_threshold', 100)
        self.SCROLL_THRESHOLD = config.get('scroll_threshold', 25)
        self.SCROLL_SENS = config.get('scroll_sensitivity', 120)
        self.CLICK_COOLDOWN = 0.2
        self.SWIPE_COOLDOWN = 0.5
        
        logger.info(f"HandGestureService 초기화 (화면: {self.screen_w}x{self.screen_h})")
    
    # ===== 유틸리티 함수 =====
    
    def calculate_hand_size(self, landmarks) -> float:
        """손 크기 계산 (카메라에 가까울수록 큼)"""
        wrist = landmarks[0]
        middle_tip = landmarks[12]
        
        size = np.sqrt(
            (middle_tip.x - wrist.x)**2 + 
            (middle_tip.y - wrist.y)**2 + 
            (middle_tip.z - wrist.z)**2
        )
        return size
    
    def get_largest_hand(self, hand_landmarks_list):
        """여러 손 중 가장 큰 손 반환"""
        if len(hand_landmarks_list) == 0:
            return None
        if len(hand_landmarks_list) == 1:
            return hand_landmarks_list[0]
        
        sizes = [self.calculate_hand_size(hand.landmark) for hand in hand_landmarks_list]
        max_idx = np.argmax(sizes)
        return hand_landmarks_list[max_idx]
    
    # ===== 제스처 인식 =====
    
    def is_palm_open(self, landmarks) -> bool:
        """손바닥이 펴져 있는지 확인"""
        fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]
        
        # 엄지
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        thumb_open = abs(thumb_tip.x - thumb_ip.x) > 0.04
        
        # 나머지 손가락
        fingers_open = sum(
            1 for tip_id, pip_id in fingers 
            if landmarks[tip_id].y < landmarks[pip_id].y
        )
        
        return thumb_open and fingers_open >= 3
    
    def is_fist(self, landmarks) -> bool:
        """주먹 인식"""
        finger_tip_ids = [8, 12, 16, 20]
        finger_dip_ids = [5, 9, 13, 17]
        
        folded_count = sum(
            1 for tip_id, dip_id in zip(finger_tip_ids, finger_dip_ids)
            if landmarks[tip_id].y > landmarks[dip_id].y
        )
        
        return folded_count >= 3
    
    # ===== 마우스 제어 =====
    
    def move_cursor(self, landmarks):
        """커서 이동 (80% 카메라 영역을 화면 전체로 매핑)"""
        index_tip = landmarks[5]
        
        # 0.1 ~ 0.9 범위를 0.0 ~ 1.0으로 리매핑
        mapped_x = (index_tip.x - 0.1) / 0.8
        mapped_y = (index_tip.y - 0.1) / 0.8
        
        # 범위를 0.0 ~ 1.0으로 클램핑
        mapped_x = max(0.0, min(1.0, mapped_x))
        mapped_y = max(0.0, min(1.0, mapped_y))
        
        # 화면 좌표로 변환
        x = int(mapped_x * self.screen_w)
        y = int(mapped_y * self.screen_h)
        
        # 화면 범위 내로 제한
        x = max(0, min(x, self.screen_w - 1))
        y = max(0, min(y, self.screen_h - 1))
        
        # 스무딩
        cur_x = self.prev_x + (x - self.prev_x) / self.SMOOTHING
        cur_y = self.prev_y + (y - self.prev_y) / self.SMOOTHING
        
        cur_x = max(0, min(cur_x, self.screen_w - 1))
        cur_y = max(0, min(cur_y, self.screen_h - 1))
        
        pyautogui.moveTo(cur_x, cur_y)
        self.prev_x, self.prev_y = cur_x, cur_y
    
    def handle_pinch_click(self, landmarks):
        """핀치 클릭 처리 (80% 카메라 영역 기준)"""
        if self.fist_mode:
            self.pinch_down = False
            return
        
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        
        # 80% 영역으로 리매핑
        thumb_x = (thumb_tip.x - 0.1) / 0.8
        thumb_y = (thumb_tip.y - 0.1) / 0.8
        index_x = (index_tip.x - 0.1) / 0.8
        index_y = (index_tip.y - 0.1) / 0.8
        
        # 화면 좌표로 변환
        tx = int(thumb_x * self.screen_w)
        ty = int(thumb_y * self.screen_h)
        ix = int(index_x * self.screen_w)
        iy = int(index_y * self.screen_h)
        
        dist = np.hypot(ix - tx, iy - ty)
        now = time.time()
        
        if dist < self.PINCH_THRESHOLD and not self.pinch_down:
            if now - self.last_click_time > self.CLICK_COOLDOWN:
                self.pinch_down = True
                self.last_click_time = now
                pyautogui.click()
                logger.debug("🖱️  클릭")
        
        elif dist >= self.PINCH_THRESHOLD and self.pinch_down:
            self.pinch_down = False
    
    def handle_fist_gesture(self, landmarks):
        """주먹 제스처 처리 (스와이프, 스크롤) - 80% 카메라 영역 기준"""
        base_point = landmarks[0]
        
        # 80% 영역으로 리매핑
        mapped_x = (base_point.x - 0.1) / 0.8
        mapped_y = (base_point.y - 0.1) / 0.8
        
        # 화면 좌표로 변환
        cx = int(mapped_x * self.screen_w)
        cy = int(mapped_y * self.screen_h)
        
        if self.fist_start_x is None or self.fist_start_y is None:
            self.fist_start_x, self.fist_start_y = cx, cy
            return
        
        dx = cx - self.fist_start_x
        dy = cy - self.fist_start_y
        now = time.time()
        
        # 좌우 스와이프
        if abs(dx) > self.SWIPE_THRESHOLD and abs(dx) > abs(dy):
            if now - self.last_swipe_time > self.SWIPE_COOLDOWN:
                if dx > 0:
                    pyautogui.hotkey('command', '[')
                    logger.debug("⬅️  앞으로")
                else:
                    pyautogui.hotkey('command', ']')
                    logger.debug("➡️  뒤로")
                self.last_swipe_time = now
                self.fist_start_x, self.fist_start_y = cx, cy
        
        # 상하 스크롤
        elif abs(dy) > self.SCROLL_THRESHOLD and abs(dy) > abs(dx):
            scroll_amount = int(dy / self.SCROLL_SENS * 20)
            pyautogui.scroll(scroll_amount)
            logger.debug(f"🔄 스크롤: {scroll_amount}")
            self.fist_start_x, self.fist_start_y = cx, cy
    
    # ===== 커서 숨김/표시 =====
    
    def hide_cursor(self):
        """커서 숨기기 (맥)"""
        if not self.cursor_hidden:
            try:
                subprocess.run(
                    ['python3', '-c', 'import Quartz; Quartz.CGDisplayHideCursor(0)'],
                    capture_output=True, timeout=0.5
                )
                self.cursor_hidden = True
                logger.info("🙈 커서 숨김")
            except:
                pass
    
    def show_cursor(self):
        """커서 표시 (맥)"""
        if self.cursor_hidden:
            try:
                subprocess.run(
                    ['python3', '-c', 'import Quartz; Quartz.CGDisplayShowCursor(0)'],
                    capture_output=True, timeout=0.5
                )
                self.cursor_hidden = False
                logger.info("👁️  커서 표시")
            except:
                pass
    
    # ===== 프레임 처리 =====
    
    def process_frame(self, frame):
        """프레임 처리 및 제스처 인식"""
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        
        hand_detected = False
        
        if results.multi_hand_landmarks:
            hand_detected = True
            self.last_hand_detected_time = time.time()
            
            primary_hand = self.get_largest_hand(results.multi_hand_landmarks)
            
            if primary_hand is not None:
                lm = primary_hand.landmark
                
                # 활성화 체크 (손바닥 2초 유지)
                if self.is_palm_open(lm) and not self.system_active:
                    if self.palm_show_start_time is None:
                        self.palm_show_start_time = time.time()
                        logger.info("✋ 손바닥 감지 시작")
                    else:
                        elapsed = time.time() - self.palm_show_start_time
                        remaining = self.PALM_HOLD_DURATION - elapsed
                        if remaining > 0:
                            logger.debug(f"⏱️  활성화 대기 중... {remaining:.1f}초 남음")
                        if elapsed >= self.PALM_HOLD_DURATION:
                            self.system_active = True
                            self.show_cursor()
                            logger.info("✅ 시스템 활성화!")
                            self.palm_show_start_time = None
                else:
                    self.palm_show_start_time = None
                
                # 활성화 상태에서만 제어
                if self.system_active and not self.is_palm_open(lm):
                    # 마우스 이동
                    self.move_cursor(lm)
                    
                    # 주먹 모드 전환
                    fist_now = self.is_fist(lm)
                    
                    if fist_now and not self.fist_mode:
                        self.fist_mode = True
                        logger.info("👊 주먹 모드 (스와이프/스크롤)")
                    elif not fist_now and self.fist_mode:
                        self.fist_mode = False
                        self.fist_start_x, self.fist_start_y = None, None
                        logger.info("👆 일반 모드 (마우스 이동/클릭)")
                    
                    # 제스처 처리
                    if self.fist_mode:
                        self.handle_fist_gesture(lm)
                    else:
                        self.handle_pinch_click(lm)
        
        # 자동 비활성화 (손 2초 미감지)
        if not hand_detected and self.system_active and self.last_hand_detected_time:
            time_since = time.time() - self.last_hand_detected_time
            if time_since >= self.NO_HAND_TIMEOUT:
                self.system_active = False
                self.hide_cursor()
                logger.info("⏱️  자동 비활성화 (손 미감지)")
                self.last_hand_detected_time = None
                self.fist_mode = False
            else:
                remaining = self.NO_HAND_TIMEOUT - time_since
                if int(remaining * 10) % 10 == 0:  # 0.1초마다 로그
                    logger.debug(f"⚠️  손 미감지: {remaining:.1f}초 후 비활성화")
        
        return self.system_active
    
    # ===== 메인 루프 =====
    
    def run(self):
        """메인 실행 루프"""
        camera_index = self.config.get('camera_index', 0)
        logger.info(f"📹 카메라 {camera_index} 열기 시도 중...")
        
        self.cap = cv2.VideoCapture(camera_index)
        
        # 카메라 열기 실패 체크
        if not self.cap.isOpened():
            logger.error(f"❌ 카메라 {camera_index}를 열 수 없습니다.")
            logger.error("해결 방법:")
            logger.error("  1. python test_gesture_visual.py로 카메라 테스트")
            logger.error("  2. .env 파일의 GESTURE_CAMERA_INDEX 수정")
            logger.error("  3. 다른 프로그램에서 카메라 사용 중인지 확인")
            self.running = False
            return
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 첫 프레임 읽기 테스트
        ret, _ = self.cap.read()
        if not ret:
            logger.error(f"❌ 카메라 {camera_index}에서 프레임을 읽을 수 없습니다.")
            self.cap.release()
            self.running = False
            return
        
        logger.info(f"✅ 카메라 {camera_index} 정상 작동")
        logger.info("🎥 비접촉 터치 시스템 시작")
        logger.info(f"💡 손바닥을 {self.PALM_HOLD_DURATION}초간 보여주면 활성화됩니다")
        
        # 초기 커서 숨김
        self.hide_cursor()
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue
                
                # 프레임 처리
                self.process_frame(frame)
                
                # 작은 딜레이
                time.sleep(0.01)
        
        finally:
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            self.show_cursor()
            logger.info("🛑 비접촉 터치 시스템 종료")
    
    # ===== 서비스 제어 =====
    
    def start(self):
        """서비스 시작"""
        if self.running:
            logger.warning("⚠️  이미 실행 중입니다")
            return False
        
        camera_index = self.config.get('camera_index', 0)
        logger.info(f"🚀 HandGestureService 시작 중... (카메라: {camera_index})")
        
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        
        # 카메라 초기화 대기 (최대 2초)
        for i in range(20):
            time.sleep(0.1)
            if not self.running:  # run()에서 실패로 running=False 설정됨
                logger.error("❌ HandGestureService 시작 실패 - 카메라를 열 수 없습니다")
                return False
            if self.cap is not None and self.cap.isOpened():
                logger.info("✅ HandGestureService 시작 완료")
                return True
        
        logger.info("✅ HandGestureService 시작됨")
        return True
    
    def stop(self):
        """서비스 중지"""
        logger.info("🛑 HandGestureService 중지 중...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.show_cursor()
        logger.info("✅ HandGestureService 중지됨")
    
    def get_status(self) -> dict:
        """현재 상태 반환"""
        status = {
            "running": self.running,
            "active": self.system_active,
            "fist_mode": self.fist_mode,
            "pinch_down": self.pinch_down,
            "cursor_hidden": self.cursor_hidden,
        }
        
        # 상태 로그
        if self.running:
            if self.system_active:
                mode = "주먹 모드" if self.fist_mode else "일반 모드"
                logger.debug(f"📊 상태: 실행 중 | 활성화됨 | {mode}")
            else:
                logger.debug("📊 상태: 실행 중 | 비활성화됨")
        else:
            logger.debug("📊 상태: 중지됨")
        
        return status