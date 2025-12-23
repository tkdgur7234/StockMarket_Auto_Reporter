# backend/routers/report.py

from fastapi import APIRouter
from services.briefing_market_condition import get_market_summary_markdown, get_sp500_map_image 

router = APIRouter(
    prefix="/report",  # 이 라우터의 모든 주소 앞에 /report가 붙음
    tags=["Report"]
)

# 1-1. 각종 지표 데일리 시황 마크다운 생성 엔드포인트
@router.post("/market-indicators")
def generate_market_indicators():
    markdown_table = get_market_summary_markdown()
    
    # n8n이 바로 쓸 수 있는 JSON 구조로 리턴
    return {
        "status": "success",
        "market_summary_markdown": markdown_table
    }


router = APIRouter(
    prefix="/report",
    tags=["Report"]
)

# 1-2. S&P 500 Map 이미지(Base64) 생성 엔드포인트
@router.post("/sp500-map")
def fetch_sp500_map():
    img_base64 = get_sp500_map_image()
    
    if img_base64:
        return {
            "status": "success",
            "image_type": "base64",
            "image_data": img_base64
        }
    else:
        return {
            "status": "error", 
            "message": "이미지 캡처 실패"
        }