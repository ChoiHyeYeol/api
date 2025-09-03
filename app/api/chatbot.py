# api/chatbot.py
from __future__ import annotations
from fastapi import APIRouter
from . import svc, AssessIn

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/ask")
def chat_ask(payload: AssessIn):
    """
    자유로운 문장 입력:
    - 예) "나 지금 갈비천왕 먹어도 돼?"
    """
    return svc.assess(
        message=payload.message,
        recent_glucose=payload.recent_glucose,
        portion_g=payload.portion_g,
    )
