from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class OrderAction(BaseModel):
    """주문 액션"""
    type: str = Field(..., description="액션 타입 (ADD, UPDATE, REMOVE, CLEAR)")
    data: Optional[Dict[str, Any]] = Field(None, description="액션 데이터")
    targetId: Optional[str] = Field(None, description="UPDATE 대상 ID")
    id: Optional[str] = Field(None, description="메뉴 ID (REMOVE용)")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "ADD",
                "data": {
                    "id": "americano",
                    "name": "아메리카노",
                    "options": ["따뜻하게", "그란데 사이즈"],
                    "option_ids": ["hot", "grande"],
                    "price": 4000,
                    "quantity": 1
                }
            }
        }


class VoiceOrderResponse(BaseModel):
    """음성 주문 응답"""
    text: str = Field(..., description="인식된 텍스트")
    actions: List[OrderAction] = Field(..., description="주문 액션 목록")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "아메리카노 한 잔 주세요",
                "actions": [
                    {
                        "type": "ADD",
                        "data": {
                            "id": "americano",
                            "name": "아메리카노",
                            "options": ["따뜻하게", "그란데 사이즈"],
                            "option_ids": ["hot", "grande"],
                            "price": 4000,
                            "quantity": 1
                        }
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """에러 응답"""
    text: str = Field(..., description="에러 메시지")
    actions: List = Field(default_factory=list, description="빈 액션 목록")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "오류 발생",
                "actions": []
            }
        }