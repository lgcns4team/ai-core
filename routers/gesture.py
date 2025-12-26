"""
비접촉 터치 제스처 API 라우터
routers/gesture.py
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gesture", tags=["gesture"])

# 전역 서비스 인스턴스
gesture_service = None
service = None  # main.py의 health check에서 사용


# ===== Request/Response 스키마 =====

class GestureStartRequest(BaseModel):
    """제스처 시작 요청"""
    camera_index: Optional[int] = 1
    palm_hold_duration: Optional[float] = 3.0
    no_hand_timeout: Optional[float] = 2.0
    smoothing: Optional[int] = 2
    pinch_threshold: Optional[int] = 40
    swipe_threshold: Optional[int] = 100
    scroll_threshold: Optional[int] = 25
    scroll_sensitivity: Optional[int] = 120
    
    class Config:
        json_schema_extra = {
            "example": {
                "camera_index": 1,
                "palm_hold_duration": 3.0,
                "no_hand_timeout": 2.0,
                "smoothing": 2
            }
        }


class GestureStatusResponse(BaseModel):
    """제스처 상태 응답"""
    running: bool
    active: bool
    fist_mode: bool
    pinch_down: bool
    cursor_hidden: bool


class MessageResponse(BaseModel):
    """기본 메시지 응답"""
    status: str
    message: str


# ===== API 엔드포인트 =====

@router.post("/start", response_model=MessageResponse, summary="비접촉 터치 시작")
async def start_gesture(request: GestureStartRequest):
    """
    비접촉 터치 제스처 인식 시작
    
    **사용법:**
    1. 이 API 호출로 시스템 시작
    2. 손바닥을 3초간 카메라에 보여주면 활성화
    3. 제스처 사용:
       - 검지로 마우스 이동
       - 엄지+검지 핀치로 클릭
       - 주먹 쥐고 좌우 스와이프: 브라우저 앞/뒤
       - 주먹 쥐고 상하 움직임: 스크롤
    4. 손이 2초간 감지되지 않으면 자동 비활성화
    
    **Parameters:**
    - **camera_index**: 카메라 인덱스 (0: 기본, 1: 외장)
    - **palm_hold_duration**: 활성화 손바닥 유지 시간 (초)
    - **no_hand_timeout**: 자동 비활성화 시간 (초)
    - **smoothing**: 마우스 스무딩 (1-5, 클수록 부드러움)
    """
    global gesture_service, service
    
    if gesture_service and gesture_service.running:
        raise HTTPException(status_code=400, detail="이미 실행 중입니다")
    
    try:
        # 서비스 import (지연 import)
        from services.gesture import HandGestureService
        
        config = {
            'camera_index': request.camera_index,
            'palm_hold_duration': request.palm_hold_duration,
            'no_hand_timeout': request.no_hand_timeout,
            'smoothing': request.smoothing,
            'pinch_threshold': request.pinch_threshold,
            'swipe_threshold': request.swipe_threshold,
            'scroll_threshold': request.scroll_threshold,
            'scroll_sensitivity': request.scroll_sensitivity,
        }
        
        logger.info(f"비접촉 터치 시작 요청 (카메라: {request.camera_index})")
        
        gesture_service = HandGestureService(config)
        success = gesture_service.start()
        
        if not success:
            error_msg = f"카메라 {request.camera_index}를 열 수 없습니다. "
            error_msg += "해결 방법: (1) python quick_test.py로 사용 가능한 카메라 확인, "
            error_msg += "(2) 다른 프로그램에서 카메라 사용 중인지 확인, "
            error_msg += "(3) .env의 GESTURE_CAMERA_INDEX 수정"
            gesture_service = None
            service = None
            raise HTTPException(status_code=500, detail=error_msg)
        
        # main.py의 health check에서 사용하기 위해 service 변수도 설정
        service = gesture_service
        
        logger.info("✅ 비접촉 터치 시작 성공")
        
        return MessageResponse(
            status="success",
            message=f"비접촉 터치가 시작되었습니다 (카메라: {request.camera_index}). 손바닥을 {request.palm_hold_duration}초간 보여주세요."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"비접촉 터치 시작 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"서비스 시작 실패: {str(e)}"
        )


@router.post("/stop", response_model=MessageResponse, summary="비접촉 터치 중지")
async def stop_gesture():
    """
    비접촉 터치 제스처 인식 중지
    
    시스템을 완전히 종료하고 커서를 복구합니다.
    """
    global gesture_service, service
    
    if not gesture_service or not gesture_service.running:
        raise HTTPException(status_code=400, detail="실행 중이 아닙니다")
    
    try:
        gesture_service.stop()
        gesture_service = None
        service = None
        logger.info("비접촉 터치 중지됨")
        
        return MessageResponse(
            status="success",
            message="비접촉 터치가 중지되었습니다"
        )
    
    except Exception as e:
        logger.error(f"비접촉 터치 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=GestureStatusResponse, summary="상태 조회")
async def get_gesture_status():
    """
    현재 비접촉 터치 상태 조회
    
    **응답:**
    - **running**: 시스템 실행 여부
    - **active**: 제스처 제어 활성화 여부
    - **fist_mode**: 주먹 모드 (스와이프/스크롤)
    - **pinch_down**: 핀치 클릭 중
    - **cursor_hidden**: 커서 숨김 상태
    """
    global gesture_service
    
    if not gesture_service:
        return GestureStatusResponse(
            running=False,
            active=False,
            fist_mode=False,
            pinch_down=False,
            cursor_hidden=False
        )
    
    status = gesture_service.get_status()
    return GestureStatusResponse(**status)


@router.get("/health", summary="헬스 체크")
async def health_check():
    """
    서비스 헬스 체크
    
    시스템이 정상적으로 작동하는지 확인합니다.
    """
    global gesture_service
    
    return {
        "status": "healthy",
        "service": "hand_gesture",
        "running": gesture_service.running if gesture_service else False,
        "version": "2.0.0"
    }


@router.get("/info", summary="제스처 정보")
async def get_gesture_info():
    """
    지원하는 제스처 정보 반환
    
    사용 가능한 모든 제스처와 설명을 제공합니다.
    """
    return {
        "gestures": {
            "activation": {
                "name": "손바닥 보여주기",
                "description": "모든 손가락을 펴고 2초간 유지하면 시스템 활성화",
                "duration": "2초"
            },
            "deactivation": {
                "name": "손 치우기",
                "description": "손이 2초간 감지되지 않으면 자동 비활성화",
                "duration": "2초"
            },
            "mouse_move": {
                "name": "검지로 이동",
                "description": "검지 손가락 위치로 마우스 커서 이동"
            },
            "click": {
                "name": "핀치 클릭",
                "description": "엄지와 검지를 붙여서 클릭"
            },
            "navigate_forward": {
                "name": "주먹 + 오른쪽",
                "description": "주먹 쥐고 오른쪽으로 스와이프 (브라우저 앞으로)"
            },
            "navigate_back": {
                "name": "주먹 + 왼쪽",
                "description": "주먹 쥐고 왼쪽으로 스와이프 (브라우저 뒤로)"
            },
            "scroll": {
                "name": "주먹 + 상하",
                "description": "주먹 쥐고 위/아래로 움직여서 스크롤"
            }
        },
        "tips": [
            "조명이 밝은 곳에서 사용하세요",
            "손을 카메라 정면에 위치시키세요",
            "손바닥 활성화는 정확히 3초간 유지해야 합니다",
            "자동 비활성화 후 다시 손바닥을 보여주면 재활성화됩니다"
        ]
    }