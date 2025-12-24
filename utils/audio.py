import librosa
import soundfile as sf
import noisereduce as nr
import shutil
from config.settings import AUDIO_SAMPLE_RATE, NOISE_REDUCTION_PROP


def remove_noise(input_path: str, output_path: str) -> None:
    """
    오디오 파일의 노이즈 제거
    
    Args:
        input_path: 입력 오디오 파일 경로
        output_path: 출력 오디오 파일 경로
    """
    print(f"🧹 노이즈 제거 시작: {input_path}")
    try:
        # 1. 파일 읽기 (librosa는 모든 포맷을 자동으로 변환)
        y, sr = librosa.load(input_path, sr=AUDIO_SAMPLE_RATE)
        
        # 2. 노이즈 제거
        # prop_decrease: 잡음 감소 비율 (너무 높으면 목소리 왜곡됨)
        reduced_noise = nr.reduce_noise(
            y=y, 
            sr=sr, 
            stationary=True, 
            prop_decrease=NOISE_REDUCTION_PROP
        )
        
        # 3. 저장
        sf.write(output_path, reduced_noise, sr)
        print("🧹 노이즈 제거 완료")
        
    except Exception as e:
        print(f"⚠️ 노이즈 제거 실패: {e}")
        # 실패 시 원본을 그대로 복사 (비상 대책)
        shutil.copy(input_path, output_path)


def validate_audio_file(file_path: str) -> bool:
    """
    오디오 파일 유효성 검증
    
    Args:
        file_path: 검증할 파일 경로
        
    Returns:
        유효한 오디오 파일이면 True
    """
    try:
        y, sr = librosa.load(file_path, duration=0.1)
        return len(y) > 0
    except Exception as e:
        print(f"⚠️ 오디오 파일 검증 실패: {e}")
        return False