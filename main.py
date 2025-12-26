import ssl
import uvicorn
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# SSL 인증 우회 (맥 개발 환경용)
ssl._create_default_https_context = ssl._create_unverified_context

# 서비스 import
from services.detect import DepthFaceAnalyzer
from services.voice import VoiceOrderService
from services.gesture import HandGestureService


# 라우터 import
import routers.detect as detect_router
import routers.voice as voice_router
import routers.gesture as gesture_router


app = FastAPI(
    title="Integrated API - Face Detection & Voice Order",
    version="1.0.0",
    description="얼굴 감지/분석, 음성 주문, 비접촉 터치를 통합한 서비스"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 글로벌 서비스 인스턴스
face_analyzer = DepthFaceAnalyzer()
voice_service = VoiceOrderService()
gesture_service = None  # 시작 시 초기화


# 라우터에 서비스 주입
detect_router.set_analyzer(face_analyzer)
voice_router.set_service(voice_service)

# 라우터 등록
app.include_router(detect_router.router, tags=["Face Detection"])
app.include_router(voice_router.router, tags=["Voice Order"])
app.include_router(gesture_router.router, tags=["Gesture Control"])  # 🆕 추가



@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Integrated API - Face Detection & Voice Order",
        "version": "1.0.0",
        "services": {
            "face_detection": {
                "description": "Intel RealSense 기반 얼굴 감지 및 분석",
                "endpoints": {
                    "analysis": "/api/analysis",
                    "status": "/api/status",
                    "stream_status": "/api/stream/status"
                }
            },
            "voice_order": {
                "description": "음성 인식 기반 주문 처리",
                "endpoints": {
                    "voice_order": "/order/voice",
                    "test": "/order/test"
                }
            },
            "gesture_control": {
                "description": "손 제스처 기반 비접촉 터치",
                "status": "auto_start",
                "note": "서버 시작 시 자동으로 카메라 활성화. 손바닥을 2초간 보여주면 제스처 제어 활성화.",
                "endpoints": {
                    "status": "/gesture/status",
                    "info": "/gesture/info",
                    "health": "/gesture/health"
                }
            }
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """전체 시스템 헬스 체크"""
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # 얼굴 감지 서비스 상태
    try:
        detection_status = face_analyzer.get_status()
        health_status["services"]["face_detection"] = {
            "status": "running" if detection_status.get("is_running") else "stopped",
            "camera_connected": detection_status.get("camera_connected", False)
        }
    except Exception as e:
        health_status["services"]["face_detection"] = {
            "status": "error",
            "error": str(e)
        }
    
    # 음성 주문 서비스 상태
    health_status["services"]["voice_order"] = {
        "status": "ready"
    }
    
    # 비접촉 터치 서비스 상태
    try:
        if gesture_service is not None:
            gesture_status = gesture_service.get_status()
            health_status["services"]["gesture_control"] = {
                "status": "running" if gesture_status.get("running") else "stopped",
                "active": gesture_status.get("active", False),
                "fist_mode": gesture_status.get("fist_mode", False)
            }
        else:
            health_status["services"]["gesture_control"] = {
                "status": "not_initialized"
            }
    except Exception as e:
        health_status["services"]["gesture_control"] = {
            "status": "error",
            "error": str(e)
        }
    
    return health_status

@app.on_event("startup")
async def startup_event():
    """FastAPI 시작 시 실행"""
    global gesture_service
    
    print("=" * 60)
    print("🚀 통합 API 시스템 시작...")
    print("=" * 60)
    
    # 얼굴 감지 서비스 초기화
    print("\n[1/3] 얼굴 감지 서비스 초기화 중...")
    if face_analyzer.initialize_camera():
        detection_thread = threading.Thread(
            target=face_analyzer.run_detection_loop, 
            daemon=True
        )
        detection_thread.start()
        print("✅ 얼굴 감지 서비스 시작 완료")
    else:
        print("❌ 얼굴 감지 서비스 초기화 실패")
    
    # 음성 주문 서비스 초기화
    print("\n[2/3] 음성 주문 서비스 초기화 중...")
    voice_service.initialize()
    print("✅ 음성 주문 서비스 시작 완료")
    
    # 비접촉 터치 서비스 자동 시작
    print("\n[3/3] 비접촉 터치 서비스 시작 중...")
    print("   → 웹캠 (카메라 인덱스: 0)")
    try:
        # 제스처 설정 (카메라 인덱스 0)
        gesture_config = {
            'camera_index': 0,  # 카메라 인덱스 0
            'palm_hold_duration': 2.0,
            'no_hand_timeout': 2.0,
            'smoothing': 2,
            'pinch_threshold': 40,
            'swipe_threshold': 100,
            'scroll_threshold': 25,
            'scroll_sensitivity': 120,
        }
        
        gesture_service = HandGestureService(gesture_config)
        success = gesture_service.start()
        
        if success:
            # gesture_router에도 서비스 인스턴스 전달
            gesture_router.gesture_service = gesture_service
            gesture_router.service = gesture_service
            
            print("✅ 비접촉 터치 서비스 시작 완료")
            print("   💡 카메라 화면이 자동으로 표시됩니다 (개발 모드)")
            print("   💡 손바닥을 2초간 보여주면 제스처 제어가 활성화됩니다")
            print("   💡 ESC 키를 누르면 제스처 서비스가 종료됩니다")
        else:
            print("❌ 비접촉 터치 서비스 시작 실패")
            print("   → 카메라를 열 수 없습니다. 로그를 확인하세요.")
            gesture_service = None
    except Exception as e:
        print(f"❌ 비접촉 터치 서비스 오류: {e}")
        gesture_service = None
    
    print("\n" + "=" * 60)
    print("✅ 모든 서비스 준비 완료!")
    print("📍 서버 주소: http://0.0.0.0:8000")
    print("📚 API 문서: http://0.0.0.0:8000/docs")
    print("🏥 헬스 체크: http://0.0.0.0:8000/health")
    print("\n💡 카메라 구성:")
    print("   - 얼굴 감지: RealSense 카메라")
    print("   - 비접촉 터치: 웹캠 (카메라 인덱스 0)")
    print("\n🎥 비접촉 터치:")
    print("   - 손바닥을 2초간 보여주면 활성화")
    print("=" * 60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI 종료 시 실행"""
    print("\n" + "=" * 60)
    print("🛑 시스템 종료 중...")
    print("=" * 60)
    
    # 얼굴 감지 서비스 종료
    print("\n[1/3] 얼굴 감지 서비스 종료 중...")
    face_analyzer.stop()
    print("✅ 얼굴 감지 서비스 종료 완료")
    
    # 음성 주문 서비스 종료
    print("\n[2/3] 음성 주문 서비스 종료 중...")
    voice_service.cleanup()
    print("✅ 음성 주문 서비스 종료 완료")
    
    # 비접촉 터치 서비스 종료
    print("\n[3/3] 비접촉 터치 서비스 종료 중...")
    try:
        if gesture_service is not None:
            gesture_service.stop()
            print("✅ 비접촉 터치 서비스 종료 완료")
        else:
            print("ℹ️  비접촉 터치 서비스가 실행 중이 아닙니다.")
    except Exception as e:
        print(f"⚠️  비접촉 터치 서비스 종료 중 오류: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 모든 서비스 종료 완료")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )