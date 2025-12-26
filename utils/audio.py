import ffmpeg
import numpy as np
import shutil
from config.settings import AUDIO_SAMPLE_RATE, NOISE_REDUCTION_PROP


def load_audio_with_ffmpeg(file_bytes: bytes, sr: int = 16000) -> np.ndarray:
    """
    FFmpeg를 사용하여 오디오 로드 및 Bandpass Filter 적용 (In-Memory)
    
    Args:
        file_bytes: 업로드된 파일의 바이너리 데이터
        sr: 샘플링 레이트 (Whisper는 16000 권장)
        
    Returns:
        Numpy float32 배열 (Whisper 입력용)
    """
    try:
        # FFmpeg 파이프라인
        # 1. pipe:0 -> 메모리에서 입력
        # 2. highpass=200 -> 웅~ 하는 저음(팬소음) 제거
        # 3. lowpass=3000 -> 치~ 하는 고음(전기노이즈) 제거
        out, _ = (
            ffmpeg
            .input('pipe:0')
            .filter('highpass', f='200')
            .filter('lowpass', f='3000')
            .output('pipe:1', format='f32le', acodec='pcm_f32le', ac=1, ar=str(sr))
            .run(input=file_bytes, capture_stdout=True, capture_stderr=True)
        )
        
        # 바이트 데이터를 Numpy 배열로 변환
        return np.frombuffer(out, np.float32)
        
    except ffmpeg.Error as e:
        print(f"❌ FFmpeg 처리 오류: {e.stderr.decode()}")
        raise e
    except Exception as e:
        print(f"⚠️ 오디오 처리 실패: {e}")
        # 실패 시 빈 배열 반환
        return np.array([], dtype=np.float32)




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