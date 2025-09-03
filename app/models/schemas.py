# app/models/schemas.py
# 예시임.
from typing import Optional, List
from pydantic import BaseModel, Field

class DietRecommendReq(BaseModel):
    user_id: str = Field(..., examples=["user_123"])
    fpg: Optional[float] = Field(None, description="공복혈당")
    ppg_1h: Optional[float] = Field(None, description="식후 1시간 혈당")
    ppg_2h: Optional[float] = Field(None, description="식후 2시간 혈당")
    preferences: Optional[List[str]] = None  # 선호 식재료

class DietItem(BaseModel):
    name: str
    kcal: float
    carbs_g: float
    protein_g: float
    fat_g: float

class DietRecommendRes(BaseModel):
    user_id: str
    items: List[DietItem]
    note: Optional[str] = None
