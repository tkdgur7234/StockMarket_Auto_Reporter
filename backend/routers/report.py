# backend/routers/report.py

from fastapi import APIRouter
from services.indicators import get_market_summary_markdown

router = APIRouter(
    prefix="/report",  # 이 라우터의 모든 주소 앞에 /report가 붙음
    tags=["Report"]
)

@router.post("/market-indicators")
def generate_market_indicators():
    """
    1-1. 각종 지표 데일리 시황 마크다운 생성
    """
    markdown_table = get_market_summary_markdown()
    
    # n8n이 바로 쓸 수 있는 JSON 구조로 리턴
    return {
        "status": "success",
        "market_summary_markdown": markdown_table
    }