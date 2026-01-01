import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import base64

# 1. 감시할 티커 목록 (KRW=X 제거함)
TICKERS = {
    "다우 존스": "^DJI",
    "S&P 500": "^GSPC",
    "나스닥": "^IXIC",
    "러셀 2000": "^RUT",
    "WTI 원유": "CL=F",
    "금": "GC=F",
    "비트코인": "BTC-USD",
    "미 국채 10년": "^TNX",
    "달러 인덱스 / 환율": "DX-Y.NYB"
}

# 네이버 금융에서 원달러 환율 크롤링
def get_naver_usd_rate():
    """
    네이버 금융에서 실시간 원달러 환율(매매기준율) 크롤링
    """
    try:
        url = "https://finance.naver.com/marketindex/"
        # 봇 탐지 방지용 헤더
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 네이버 금융 환율 섹션의 '미국 USD' 값 추출
            usd_item = soup.select_one("#exchangeList > li.on > a.head.usd > div > span.value")
            if usd_item:
                # 쉼표(,) 제거 후 float 변환
                return float(usd_item.text.replace(",", ""))
    except Exception as e:
        print(f"Naver Crawl Error: {e}")
    
    return 0.0 # 실패 시 0.0 반환

# 1-1. 마켓 요약 마크다운 생성
def get_market_summary_markdown():
    symbols = list(TICKERS.values())
    
    # yfinance 데이터 다운로드
    df = yf.download(symbols, period="5d", group_by='ticker', threads=True, progress=False, auto_adjust=False)

    rows = []
    
    # [1단계] 네이버에서 환율 가져오기 (Source 변경)
    krw_rate = get_naver_usd_rate()
    # 만약 크롤링 실패하면 0.0원이 뜸

    # [2단계] 표 생성 루프
    for name, symbol in TICKERS.items():
        if symbol == "KRW=X":
            continue
        try:
            if len(symbols) > 1:
                try:
                    data = df[symbol]
                except KeyError:
                    rows.append(f"| {name} | N/A | ⚠️ 티커 오류 |")
                    continue
            else:
                data = df

            # 컬럼명 찾기
            cols = [c.lower() for c in data.columns]
            target_col = None
            if 'close' in cols:
                target_col = data.columns[cols.index('close')]
            elif 'adj close' in cols:
                target_col = data.columns[cols.index('adj close')]
            
            if target_col is None:
                rows.append(f"| {name} | N/A | ⚠️ 컬럼 없음 |")
                continue

            # 유효 데이터 필터링
            valid_series = data[target_col].dropna()

            if valid_series.empty:
                rows.append(f"| {name} | N/A | ⚠️ 데이터 없음 |")
                continue

            last_close = float(valid_series.iloc[-1])
            
            if len(valid_series) >= 2:
                prev_close = float(valid_series.iloc[-2])
            else:
                prev_close = last_close

            change_amt = last_close - prev_close
            change_pct = (change_amt / prev_close) * 100 if prev_close != 0 else 0.0

            emoji = "🔴" if change_pct >= 0 else "🔵"
            sign = "+" if change_pct >= 0 else ""
            
            # 포맷팅
            if symbol == "DX-Y.NYB":
                # [수정] 네이버에서 가져온 krw_rate 사용
                price_str = f"{last_close:.2f} / {krw_rate:,.2f}원"
            elif symbol == "^TNX":
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

# 1-2. S&P 500 Map 이미지(Base64) 생성
def get_sp500_map_image():
    access_key = os.getenv("APIFLASH_ACCESS_KEY")
    if not access_key: return None
    
    url = "https://api.apiflash.com/v1/urltoimage"
    params = {
        "access_key": access_key,
        "url": "https://finviz.com/map.ashx?t=sec",
        "element": "#canvas-wrapper",
        "response_type": "image",
        "format": "png",
        "quality": 100,
        "width": 1920,
        "height": 1080,
        "wait_until": "page_loaded"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        print(f"ApiFlash Error: {e}")
        return None