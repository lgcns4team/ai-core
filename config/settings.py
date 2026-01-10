import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# OpenAI API 키
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Whisper 모델 설정
WHISPER_MODEL_SIZE = "small"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# 오디오 설정
AUDIO_SAMPLE_RATE = 16000  # Whisper 권장 샘플링 레이트
NOISE_REDUCTION_PROP = 0.75  # 노이즈 감소 비율 (0.0~1.0)

# 메뉴 키워드 힌트
MENU_KEYWORDS = "카페 주문. 아메리카노, 라떼, 바닐라라떼, 프라푸치노, 스무디, 샷추가, 휘핑, 얼음적게, 많이, 따뜻하게, 아이스로."

# 임시 파일 저장 경로
TEMP_FILE_DIR = "temp"

GESTURE_USE_REALSENSE = os.getenv("GESTURE_USE_REALSENSE", "true").lower() == "true"
GESTURE_CAMERA_INDEX = 0  # RealSense 사용 시 무시됨
GESTURE_PALM_DURATION = 2.0
GESTURE_TIMEOUT = 2.0
GESTURE_SMOOTHING = 3
GESTURE_PINCH_THRESHOLD = 40
GESTURE_SWIPE_THRESHOLD = 100
GESTURE_SCROLL_THRESHOLD = 25
GESTURE_SCROLL_SENSITIVITY = 100

# ===== 비접촉 터치 설정 (Gesture) =====
GESTURE_CONFIG = {
        # 카메라 설정
    'use_realsense': GESTURE_USE_REALSENSE,
    'camera_index': int(GESTURE_CAMERA_INDEX),
    
    # 활성화 설정
    'palm_hold_duration': float(GESTURE_PALM_DURATION),
    'no_hand_timeout': float(GESTURE_TIMEOUT),
    
    # 마우스 제어
    'smoothing': int(GESTURE_SMOOTHING),
    
    # 제스처 임계값
    'pinch_threshold': int(GESTURE_PINCH_THRESHOLD),
    'swipe_threshold': int(GESTURE_SWIPE_THRESHOLD),
    'scroll_threshold': int(GESTURE_SCROLL_THRESHOLD),
    'scroll_sensitivity': int(GESTURE_SCROLL_SENSITIVITY),
}