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

# ===== 비접촉 터치 설정 (Gesture) =====
GESTURE_CONFIG = {
    # 카메라 설정
    'camera_index': int(os.getenv("GESTURE_CAMERA_INDEX", "1")),
    
    # 활성화 설정
    'palm_hold_duration': float(os.getenv("GESTURE_PALM_DURATION", "2.0")),
    'no_hand_timeout': float(os.getenv("GESTURE_TIMEOUT", "2.0")),
    
    # 마우스 제어
    'smoothing': int(os.getenv("GESTURE_SMOOTHING", "2")),
    
    # 제스처 임계값
    'pinch_threshold': int(os.getenv("GESTURE_PINCH_THRESHOLD", "40")),
    'swipe_threshold': int(os.getenv("GESTURE_SWIPE_THRESHOLD", "100")),
    'scroll_threshold': int(os.getenv("GESTURE_SCROLL_THRESHOLD", "25")),
    'scroll_sensitivity': int(os.getenv("GESTURE_SCROLL_SENSITIVITY", "120")),
}