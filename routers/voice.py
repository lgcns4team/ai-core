import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict
from schemas.voice import VoiceOrderResponse

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
    음성 주문 처리 (Zero-Copy Optimization)
    """
    service = get_service()
    
    try:
        # 1. 파일 내용을 메모리로 읽기 (await 필수)
        # 디스크에 저장하지 않습니다.
        file_bytes = await file.read()
        
        # 2. 바이트 데이터를 서비스로 전달
        result = service.process_voice_order(file_bytes)
        
        return result
    
    except Exception as e:
        print(f"⚠️ 음성 주문 API 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    # finally 블록 제거 - 임시 파일을 사용하지 않으므로 정리할 필요 없음


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