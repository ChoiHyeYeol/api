from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


from app.services.recipe_service import (
    transform_recipe_from_dict,
    crawl_recipe_stub, # (2번) 함수 시그니처만 유지 – 내부는 비워둠
)


router = APIRouter(prefix="/recipe", tags=["recipe"])




class ConvertRequest(BaseModel):
# 2번까지 끝났다고 가정: 이미 추출된 JSON 파일 경로 또는 JSON 본문 자체를 받는다  
    url: Optional[str] = Field(
    None, description="이미 추출된 food*.json 경로. 예: /data/recipes/recipes/food123.json"
    )
    recipe_json: Optional[Dict[str, Any]] = Field(
    None, description="크롤링 결과 레시피 JSON. (recipe_path 대신 사용 가능)"
    )
    user_type: str = Field(
    ..., description="사용자 유형: FPG_HIGH | PPG_HIGH | WEIGHT_GAIN | INSULIN"
    )
    allergies: List[str] = Field(default_factory=list, description="알러지 재료 목록")




@router.post("/convert_recipe")
async def convert_recipe(req: ConvertRequest):
    """(3번 흐름) 저당 변환 + GI/영양 분석 후 'food*.json' 포맷으로 반환"""
    if req.recipe_json:
        return transform_recipe_from_dict(req.recipe_json, req.user_type, req.allergies)  
    
    return transform_recipe_from_dict(crawl_recipe_stub(req.url), req.user_type, req.allergies)
    