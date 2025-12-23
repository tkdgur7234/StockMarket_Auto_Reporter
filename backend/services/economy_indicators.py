import requests
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# 1. 지표 매핑 설정
INDICATOR_MAP = {
    "CPIAUCSL": {"name": "소비자물가지수 (CPI)", "units": "pc1", "suffix": "%", "decimal": 1, "ff_title": "CPI y/y"},
    "PPIFIS":   {"name": "생산자물가지수 (PPI)", "units": "pc1", "suffix": "%", "decimal": 1, "ff_title": "PPI m/m"},
    "PCEPI":    {"name": "개인소비지출 (PCE)", "units": "pc1", "suffix": "%", "decimal": 1, "ff_title": "Core PCE Price Index m/m"},
    "PAYEMS":   {"name": "비농업 고용지수 (NFP)", "units": "chg", "suffix": "K", "decimal": 0, "ff_title": "Non-Farm Employment Change"},
    "ICSA":     {"name": "신규 실업수당 청구", "units": "lin", "suffix": "K", "divide": 1000, "decimal": 0, "ff_title": "Unemployment Claims"},
    "RSAFS":    {"name": "소매 판매", "units": "pch", "suffix": "%", "decimal": 1, "ff_title": "Retail Sales m/m"},
    "DFEDTARU": {"name": "기준금리 (FOMC)", "units": "lin", "suffix": "%", "decimal": 2, "ff_title": "Federal Funds Rate"}
}

def get_fred_data():
    """FRED API에서 최신 데이터 가져오기"""
    api_key = os.getenv("FRED_API_KEY")
    results = {}
    
    for sid, info in INDICATOR_MAP.items():
        try:
            url = f"https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": sid,
                "units": info.get("units"),
                "sort_order": "desc",
                "limit": 1,
                "api_key": api_key,
                "file_type": "json"
            }
            res = requests.get(url, params=params).json()
            
            if "observations" in res and res["observations"]:
                obs = res["observations"][0]
                val = float(obs["value"])
                
                if "divide" in info:
                    val /= info["divide"]
                
                decimal_places = info.get("decimal", 2)
                formatted_num = f"{val:,.{decimal_places}f}"
                
                date_str = obs["date"]
                if sid == 'ICSA':
                    ref_date = date_str[2:] # 25-12-13
                else:
                    ref_date = date_str[2:7] # 25-11
                
                results[info["ff_title"]] = {
                    "name": info["name"],
                    "value": val,
                    "display_value": f"{formatted_num}{info['suffix']}",
                    "ref_date": ref_date,
                    "ff_title": info["ff_title"]
                }
        except Exception as e:
            print(f"FRED Error ({sid}): {e}")
            
    return results

def get_forex_factory_data():
    """Forex Factory XML 파싱 (공백 제거 기능 강화)"""
    try:
        url = f"https://nfs.faireconomy.media/ff_calendar_thisweek.xml?t={int(datetime.now().timestamp())}"
        
        # User-Agent 추가 (가끔 차단될 수 있음)
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        
        # XML 파싱
        try:
            root = ET.fromstring(res.content)
        except ET.ParseError:
            print("XML Parse Error: Forex Factory 응답이 올바르지 않습니다.")
            return []
        
        items = []
        for event in root.findall("event"):
            # 안전하게 텍스트 가져오기 함수 (None 방지 및 공백 제거)
            def get_text(tag):
                elem = event.find(tag)
                if elem is not None and elem.text:
                    return elem.text.strip() # [핵심] 앞뒤 공백 제거
                return None

            country = get_text("country")
            if country != "USD": continue
            
            title = get_text("title")
            forecast = get_text("forecast") # 예상치가 없는 경우도 있음
            date_str = get_text("date")
            time_str = get_text("time")
            impact = get_text("impact")
            
            # title과 date만 있어도 리스트에는 추가해야 함 (forecast가 없어도 매칭은 시도)
            if title and date_str and time_str:
                
                # 날짜/시간 파싱 (MM-DD-YYYY, 1:30pm)
                try:
                    mm, dd, yyyy = map(int, date_str.split('-'))
                    
                    time_str = time_str.lower()
                    is_pm = "pm" in time_str
                    is_am = "am" in time_str
                    time_part = time_str.replace("am", "").replace("pm", "").strip()
                    
                    if ":" in time_part:
                        hour, minute = map(int, time_part.split(':'))
                    else:
                        hour, minute = int(time_part), 0
                        
                    if is_pm and hour < 12: hour += 12
                    if is_am and hour == 12: hour = 0
                    
                    # UTC 시간 생성 (뉴욕시간 가정 -> +9시간 KST 변환 보정)
                    # 정확히는 XML 시간대에 따라 다르지만, 기존 JS 로직(+9h)을 따름
                    dt_obj = datetime(yyyy, mm, dd, hour, minute)
                    kst_time = dt_obj + timedelta(hours=9)
                    
                    kst_full_str = kst_time.strftime("%Y-%m-%d %H:%M")
                    kst_date_str = kst_time.strftime("%Y-%m-%d")
                    
                    # Forecast 숫자 변환
                    forecast_val = 0.0
                    if forecast:
                        clean_forecast = forecast.replace('%', '').replace('K', '').strip()
                        try:
                            forecast_val = float(clean_forecast)
                        except:
                            forecast_val = 0.0

                    items.append({
                        "title": title,
                        "forecast_str": forecast if forecast else "-",
                        "forecast_val": forecast_val,
                        "impact": impact if impact else "-",
                        "kst_full_str": kst_full_str,
                        "kst_date_str": kst_date_str
                    })
                    
                    # [디버깅] 매칭될 제목 확인용 (로그에 찍힘)
                    # print(f"[XML Found] {title} / {date_str}")

                except Exception as e:
                    print(f"Date Parse Error ({title}): {e}")
                    continue

        return items
        
    except Exception as e:
        print(f"FF Error: {e}")
        return []

def get_economy_indicators():
    """최종 데이터 병합 및 리턴"""
    fred_data = get_fred_data() # Dict
    ff_data = get_forex_factory_data() # List
    
    final_list = []
    
    for ff_title, f_item in fred_data.items():
        # [핵심] 부분 일치 매칭 (Partial Match)
        # 예: "Unemployment Claims" in "Unemployment Claims" -> True
        matched_ff = next((x for x in ff_data if f_item['ff_title'].lower() in x['title'].lower()), None)
        
        res_item = {
            "지표명": f_item["name"],
            "발표값": f_item["display_value"],
            "기준월": f_item["ref_date"],
            "예상": "-",
            "발표일(KST)": "-",
            "필터링(전일 발표)": "-",
            "중요도": "-"
        }
        
        if matched_ff:
            res_item["예상"] = matched_ff["forecast_str"]
            res_item["발표일(KST)"] = matched_ff["kst_full_str"]
            res_item["필터링(전일 발표)"] = matched_ff["kst_date_str"]
            
            # 중요도 이모지
            imp = matched_ff["impact"]
            if imp == 'High': res_item["중요도"] = "🔴 High"
            elif imp == 'Medium': res_item["중요도"] = "🟠 Med"
            elif imp == 'Low': res_item["중요도"] = "🟡 Low"
            else: res_item["중요도"] = imp
            
            # 발표값 색상 처리 (예상치와 비교)
            # 예상치가 있고(0이 아니고), 비교 가능할 때만 색상 입힘
            if matched_ff["forecast_val"] != 0:
                diff = f_item["value"] - matched_ff["forecast_val"]
                # 실업수당청구(ICSA)는 값이 '낮아야' 좋은 것임. (반대 로직 필요하면 추가)
                # 여기서는 단순히 예측치보다 높으면 빨강(서프라이즈/쇼크) 로직 유지
                
                # 주의: 단순히 diff > 0.05 하면 224 vs 223 에서 1차이 나므로 무조건 걸림.
                # 단위가 K(천)이므로 1K 차이는 1.0임. 기준을 조금 유연하게 잡아야 함.
                
                if diff > 0: # 예상보다 높음 (빨강)
                    res_item["발표값"] = f'<span style="color: #e74c3c;"><b>{f_item["display_value"]}</b></span>'
                elif diff < 0: # 예상보다 낮음 (파랑)
                    res_item["발표값"] = f'<span style="color: #3498db;"><b>{f_item["display_value"]}</b></span>'
                
        final_list.append(res_item)
        
    return final_list