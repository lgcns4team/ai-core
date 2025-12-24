from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
from typing import Dict
from schemas.detect import AnalysisResult, StatusResponse, MessageResponse

router = APIRouter(prefix="/api")

_analyzer = None


def set_analyzer(analyzer):
    """분석기 인스턴스 설정"""
    global _analyzer
    _analyzer = analyzer


def get_analyzer():
    """분석기 인스턴스 가져오기"""
    if _analyzer is None:
        raise RuntimeError("Analyzer not initialized")
    return _analyzer


@router.get("/analysis", response_model=AnalysisResult)
async def get_analysis() -> Dict:
    """최신 분석 결과 반환"""
    analyzer = get_analyzer()
    
    if analyzer.latest_analysis:
        return analyzer.latest_analysis.copy()
    else:
        raise HTTPException(status_code=404, detail="분석 데이터 없음")


@router.delete("/analysis", response_model=MessageResponse)
async def clear_analysis() -> Dict:
    """분석 데이터 초기화"""
    analyzer = get_analyzer()
    analyzer.clear_analysis()
    return {"message": "분석 데이터가 초기화되었습니다"}


@router.get("/status", response_model=StatusResponse)
async def get_status() -> Dict:
    """시스템 상태 확인"""
    analyzer = get_analyzer()
    return analyzer.get_status()


@router.get("/stream/status")
async def stream_status():
    """SSE - 실시간 상태 스트리밍"""
    analyzer = get_analyzer()
    
    async def event_generator():
        try:
            while True:
                status_data = analyzer.get_status()
                yield f"data: {json.dumps(status_data)}\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            print("SSE 연결 종료")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )