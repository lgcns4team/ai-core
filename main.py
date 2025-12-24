# import uvicorn
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# import threading

# # 서비스 import
# from services.detect import DepthFaceAnalyzer

# # 라우터는 앱 생성 후 import
# import routers.detect as detect_router

# app = FastAPI(title="Depth Face Analysis API", version="1.0.0")

# # CORS 설정
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 글로벌 분석기 인스턴스
# analyzer = DepthFaceAnalyzer()

# # 라우터에 analyzer 주입
# detect_router.set_analyzer(analyzer)

# # 라우터 등록
# app.include_router(detect_router.router, tags=["Detection"])


# @app.get("/")
# async def root():
#     """루트 엔드포인트"""
#     return {
#         "message": "Depth Face Analysis API",
#         "version": "1.0.0",
#         "endpoints": {
#             "analysis": "/api/analysis",
#             "status": "/api/status",
#             "stream_status": "/api/stream/status",
#             "docs": "/docs"
#         }
#     }


# @app.on_event("startup")
# async def startup_event():
#     """FastAPI 시작 시 실행"""
#     print("🚀 깊이 얼굴 분석 시스템 시작...")
#     if analyzer.initialize_camera():
#         detection_thread = threading.Thread(target=analyzer.run_detection_loop, daemon=True)
#         detection_thread.start()
#         print("✅ 감지 스레드 시작됨")
#     else:
#         print("❌ 카메라 초기화 실패")


# @app.on_event("shutdown")
# async def shutdown_event():
#     """FastAPI 종료 시 실행"""
#     print("🛑 시스템 종료 중...")
#     analyzer.stop()


# if __name__ == '__main__':
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=5000,
#         reload=False,
#         log_level="info"
#     )

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

# 라우터 import
import routers.detect as detect_router
import routers.voice as voice_router

app = FastAPI(
    title="Integrated API - Face Detection & Voice Order",
    version="1.0.0",
    description="얼굴 감지/분석 API와 음성 주문 API를 통합한 서비스"
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

# 라우터에 서비스 주입
detect_router.set_analyzer(face_analyzer)
voice_router.set_service(voice_service)

# 라우터 등록
app.include_router(detect_router.router, tags=["Face Detection"])
app.include_router(voice_router.router, tags=["Voice Order"])


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
            }
        },
        "docs": "/docs"
    }


@app.on_event("startup")
async def startup_event():
    """FastAPI 시작 시 실행"""
    print("=" * 60)
    print("🚀 통합 API 시스템 시작...")
    print("=" * 60)
    
    # 얼굴 감지 서비스 초기화
    print("\n[1/2] 얼굴 감지 서비스 초기화 중...")
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
    print("\n[2/2] 음성 주문 서비스 초기화 중...")
    voice_service.initialize()
    print("✅ 음성 주문 서비스 시작 완료")
    
    print("\n" + "=" * 60)
    print("✅ 모든 서비스 준비 완료!")
    print("📍 서버 주소: http://0.0.0.0:8000")
    print("📚 API 문서: http://0.0.0.0:8000/docs")
    print("=" * 60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI 종료 시 실행"""
    print("\n" + "=" * 60)
    print("🛑 시스템 종료 중...")
    print("=" * 60)
    
    # 얼굴 감지 서비스 종료
    print("\n[1/2] 얼굴 감지 서비스 종료 중...")
    face_analyzer.stop()
    print("✅ 얼굴 감지 서비스 종료 완료")
    
    # 음성 주문 서비스 종료
    print("\n[2/2] 음성 주문 서비스 종료 중...")
    voice_service.cleanup()
    print("✅ 음성 주문 서비스 종료 완료")
    
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