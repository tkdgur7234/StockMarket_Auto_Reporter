# backend/main.py (최적화 버전)
from fastapi import FastAPI
import yfinance as yf
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FRED_API_KEY") # 없으면 None 반환
DB_PW = os.getenv("DB_PASSWORD")

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Python Server is running!"}

@app.post("/StockMarket_Auto_Reporter")
def get_StockMarket_Auto_Reporter():
    start_time = datetime.now()
    print(f"[{start_time}] 🚀 데이터 요청 도착! 처리 시작...")

    # 1. 여러 종목을 리스트로 정의 (S&P500, Nasdaq, Russell 2000, Bitcoin, etc.)
    # 필요하면 여기에 추가만 하면 한 번에 다 가져옵니다.
    target_tickers = {
        'S&P500': '^GSPC', 
        'Nasdaq': '^IXIC',
        'Bitcoin': 'BTC-USD' 
    }
    
    symbols = list(target_tickers.values())
    result = {}

    try:
        # 2. [핵심 최적화] yf.download로 한 번에 병렬 요청 (threads=True)
        # period="1d"는 장중이면 현재가, 장 마감이면 종가를 가져옵니다.
        df = yf.download(symbols, period="2d", group_by='ticker', threads=True, progress=False)

        # 3. 데이터 파싱
        for name, symbol in target_tickers.items():
            try:
                # 해당 심볼의 데이터 추출
                if len(symbols) > 1:
                    data = df[symbol]
                else:
                    data = df # 종목이 하나일 경우 구조가 다름
                
                # 최신 종가 가져오기 (데이터가 있는 마지막 행)
                if not data.empty:
                    last_close = data['Close'].iloc[-1]
                    # 전일 대비 변동률 계산 (오늘 종가 - 어제 종가) / 어제 종가
                    prev_close = data['Close'].iloc[-2] if len(data) >= 2 else last_close
                    change_rate = ((last_close - prev_close) / prev_close) * 100
                    
                    result[name] = {
                        "price": round(float(last_close), 2),
                        "change": f"{round(float(change_rate), 2)}%"
                    }
                else:
                    result[name] = {"error": "No Data"}
            except Exception as parse_error:
                print(f"Error parsing {name}: {parse_error}")
                result[name] = {"error": "Parse Error"}

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"[{end_time}] ✅ 처리 완료! (소요시간: {duration}초)")

        return {
            "timestamp": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "data": result,
            "performance": f"{duration} sec",
            "message": "데이터 수집 성공"
        }

    except Exception as e:
        print(f"Server Error: {e}")
        return {"error": str(e)}