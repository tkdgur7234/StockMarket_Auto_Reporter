# backend/services/stock_data.py

import yfinance as yf
import pandas as pd
import math

TICKERS = {
    "다우 존스": "^DJI",
    "S&P 500": "^GSPC",
    "나스닥": "^IXIC",
    "러셀 2000": "^RUT",
    "WTI 원유": "CL=F",
    "금": "GC=F",
    "비트코인": "BTC-USD",
    "미 국채 10년": "^TNX",
    "달러 인덱스": "DX-Y.NYB"
}

def get_market_summary_markdown():
    symbols = list(TICKERS.values())
    
    # period="5d"로 늘려서 주말/휴일 이슈 방어 (데이터 양 조금 늘려도 속도 차이 없음)
    df = yf.download(symbols, period="5d", group_by='ticker', threads=True, progress=False, auto_adjust=False)

    rows = []
    
    for name, symbol in TICKERS.items():
        try:
            # 1. 해당 심볼의 데이터 프레임 추출
            if len(symbols) > 1:
                # 멀티 인덱스 컬럼 처리 (가끔 yfinance 버전에 따라 구조가 다를 수 있음)
                try:
                    data = df[symbol]
                except KeyError:
                    # 티커가 컬럼에 없는 경우 (다운로드 실패 등)
                    rows.append(f"| {name} | N/A | ⚠️ 티커 오류 |")
                    continue
            else:
                data = df

            # 2. 컬럼명 찾기 (Close 또는 Adj Close)
            # 대소문자 이슈 방지를 위해 컬럼명을 리스트로 변환 후 찾기
            cols = [c.lower() for c in data.columns]
            
            target_col = None
            if 'close' in cols:
                # 원본 컬럼명 복구
                target_col = data.columns[cols.index('close')]
            elif 'adj close' in cols:
                target_col = data.columns[cols.index('adj close')]
            
            if target_col is None:
                rows.append(f"| {name} | N/A | ⚠️ 컬럼 없음 |")
                continue

            # 3. [핵심 수정] NaN 값 제거 후 유효한 데이터만 추출
            # 비트코인 시간대 때문에 생긴 빈 행(NaN)을 제거하고, 진짜 데이터가 있는 마지막 행을 잡음
            valid_series = data[target_col].dropna()

            if valid_series.empty:
                rows.append(f"| {name} | N/A | ⚠️ 데이터 없음 (Empty) |")
                continue

            last_close = float(valid_series.iloc[-1]) # 유효한 마지막 값 (현재가/종가)
            
            # 전일 종가 (데이터가 2개 이상일 때만)
            if len(valid_series) >= 2:
                prev_close = float(valid_series.iloc[-2])
            else:
                prev_close = last_close

            # 4. 변동률 계산
            change_amt = last_close - prev_close
            change_pct = (change_amt / prev_close) * 100 if prev_close != 0 else 0.0

            # 5. 포맷팅
            emoji = "🔴" if change_pct >= 0 else "🔵"
            sign = "+" if change_pct >= 0 else ""
            
            if symbol in ["^TNX", "DX-Y.NYB"]:
                price_str = f"{last_close:.3f}"
            elif symbol == "BTC-USD":
                price_str = f"{last_close:,.0f}"
            else:
                price_str = f"{last_close:,.2f}"

            rows.append(f"| {name} | {price_str} | {emoji} {sign}{change_pct:.2f}% |")

        except Exception as e:
            print(f"Error processing {name}: {e}")
            rows.append(f"| {name} | Error | ⚠️ {str(e)} |")

    header = "| 지표 | 현재가 | 변동률 |\n| :--- | :---: | :---: |"
    return header + "\n" + "\n".join(rows)