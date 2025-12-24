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