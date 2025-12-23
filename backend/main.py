# backend/main.py

from fastapi import FastAPI
import yfinance as yf
from datetime import datetime
import pandas as pd
import math
import os
from dotenv import load_dotenv
from routers import report


# 1. 환경변수 로드
load_dotenv()

app = FastAPI()

# 라우터 등록 
app.include_router(report.router)

# ---------------------------------------------------------
# [핵심] JSON 변환 에러 방지용 '청소기 함수'
# 데이터 안에 숨어있는 NaN(Not a Number)을 찾아서 None(null)으로 바꿈
# ---------------------------------------------------------
def clean_data(data):
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None  # NaN이나 무한대는 None으로 변경
    return data
# ---------------------------------------------------------

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Server running with Router pattern!"}

@app.post("/StockMarket_Auto_Reporter")
def get_StockMarket_Auto_Reporter():
    start_time = datetime.now()
    print(f"[{start_time}] 🚀 데이터 요청 도착! 처리 시작...")

    target_tickers = {
        'S&P500': '^GSPC', 
        'Nasdaq': '^IXIC',
        'Bitcoin': 'BTC-USD' 
    }
    
    symbols = list(target_tickers.values())
    result = {}

    try:
        # yf.download 실행
        df = yf.download(symbols, period="2d", group_by='ticker', threads=True, progress=False, auto_adjust=False)

        for name, symbol in target_tickers.items():
            try:
                # 1. 데이터 추출
                if len(symbols) > 1:
                    data = df[symbol]
                else:
                    data = df
                
                # 2. 유효성 검사 및 계산
                if not data.empty:
                    # 컬럼명 찾기 ('Close' 또는 'Adj Close')
                    if 'Close' in data.columns:
                        price_col = 'Close'
                    elif 'Adj Close' in data.columns:
                        price_col = 'Adj Close'
                    else:
                        price_col = data.columns[-1]

                    last_close = float(data[price_col].iloc[-1])
                    prev_close = float(data[price_col].iloc[-2]) if len(data) >= 2 else last_close
                    
                    # 변동률 계산
                    if prev_close != 0:
                        change_rate = ((last_close - prev_close) / prev_close) * 100
                    else:
                        change_rate = 0.0
                    
                    result[name] = {
                        "price": round(last_close, 2),
                        "change": f"{round(change_rate, 2)}%"
                    }
                else:
                    result[name] = {"error": "No Data"}
            except Exception as parse_error:
                print(f"Error parsing {name}: {parse_error}")
                result[name] = {"error": "Parse Error"}

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"[{end_time}] ✅ 처리 완료! (소요시간: {duration}초)")

        # 3. 응답 데이터 구성
        response_data = {
            "timestamp": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": result,
            "performance": f"{duration} sec",
            "message": "데이터 수집 성공"
        }

        # [중요] 마지막에 청소기 돌려서 내보내기 (NaN -> None)
        return clean_data(response_data)

    except Exception as e:
        print(f"Server Error: {e}")
        return {"status": "error", "message": str(e)}