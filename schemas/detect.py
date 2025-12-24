from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """얼굴 분석 결과 스키마"""
    age: int = Field(..., description="추정 나이")
    gender: str = Field(..., description="성별 (남성/여성)")
    timestamp: str = Field(..., description="분석 시간")


class StatusResponse(BaseModel):
    """시스템 상태 응답 스키마"""
    status: str
    is_analyzing: bool
    face_detected: bool
    has_data: bool
    depth_threshold: float
    cooldown_period: int


class MessageResponse(BaseModel):
    """일반 메시지 응답 스키마"""
    message: str