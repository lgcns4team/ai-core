from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from typing import Dict
from schemas.voice import VoiceOrderResponse, ErrorResponse

router = APIRouter(prefix="/order")

# 서비스 인스턴스는 main.py에서 주입받음
_service = None


def set_service(service):
    """서비스 인스턴스 설정"""
    global _service
    _service = service


def get_service():
    """서비스 인스턴스 가져오기"""
    if _service is None:
        raise RuntimeError("Service not initialized. Call set_service() first.")
    return _service


@router.post(
    "/voice",
    response_model=VoiceOrderResponse,
    summary="음성 주문 처리",
    description="음성 파일을 업로드하여 주문 의도를 분석하고 주문 액션을 반환합니다."
)
async def voice_order(file: UploadFile = File(...)) -> Dict:
    """
    음성 주문 처리
    
    Args:
        file: 업로드된 음성 파일 (.webm, .wav, .mp3 등)
        
    Returns:
        인식된 텍스트와 주문 액션 리스트
    """
    service = get_service()
    
    # 임시 파일로 저장
    temp_path = f"temp_upload_{file.filename}"
    
    try:
        # 파일 저장
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 음성 주문 처리
        result = service.process_voice_order(temp_path, file.filename)
        
        return result
    
    except Exception as e:
        print(f"⚠️ 음성 주문 API 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@router.get(
    "/test",
    summary="API 테스트",
    description="API가 정상적으로 작동하는지 테스트합니다."
)
async def test_endpoint():
    """API 테스트 엔드포인트"""
    return {
        "status": "ok",
        "message": "Voice Order API is running",
        "service_initialized": _service is not None
    }