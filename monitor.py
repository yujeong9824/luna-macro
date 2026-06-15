import time
from datetime import datetime, timedelta
from flask import Flask
import threading
import requests

app = Flask(__name__)

# 🔗 디스코드 채널 ID (링크 맨 뒤에 있는 숫자들입니다)
CHANNELS = {
    "물고기": "1471878638051000404",
    "농작물": "1471878691628908698",
    "요리": "1477276897556697088"
}

SHOP_RULES = {
    "농작물": {"min_pct": -25, "max_pct": 20},
    "물고기": {"min_pct": -15, "max_pct": 10},
    "요리": {"min_pct": -20, "max_pct": 10}
}

# ⚠️ 이전에 구하셨던 본인의 디스코드 토큰(Authorization)을 꼭 여기에 입력해 주세요!
DISCORD_TOKEN = "MjkzMDYwOTA4ODU3NTU2OTkz.GBL-he.OwqOesWZJANpxzr-_Kv7jq1t0ETxgdGow3c3nk"

market_data = {"물고기": [], "농작물": [], "요리": []}

def get_seconds_until_next_hour():
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
    return (next_hour - now).total_seconds()

def get_next_update_time_str():
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return next_hour.strftime('%H:%M')

def parse_text(all_text):
    lines = all_text.split('\n')
    current_status = ""
    current_item = None
    parsed_items = []

    for line in lines:
        line = line.strip()
        if '상승 아이템' in line: current_status = "상승"; continue
        elif '하락 아이템' in line: current_status = "하락"; continue

        if (line.startswith('- ') and '[' in line) or line.startswith('- 특급'):
            if current_item: parsed_items.append(current_item)
            name = line.replace('- ', '').strip()
            current_item = {"status": current_status, "name": name, "cost": "-", "prev": "-", "current": "-", "diff": "-"}
        
        elif current_item and line.startswith('-'):
            if '원가' in line and ':' in line: current_item["cost"] = line.split(':')[1].replace('`', '').strip()
            elif '이전 변동가' in line and ':' in line: current_item["prev"] = line.split(':')[1].replace('`', '').strip()
            elif '현재 변동가' in line and ':' in line: current_item["current"] = line.split(':')[1].replace('`', '').strip()
            elif '원가 대비 변동폭' in line and ':' in line: current_item["diff"] = line.split(':')[1].replace('`', '').strip()
                
    if current_item: parsed_items.append(current_item)
    return parsed_items

def fetch_all_channels():
    headers = {
        "Authorization": DISCORD_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for category, channel_id in CHANNELS.items():
        # 디스코드 공식 메시지 수집 주소 (가장 최근 메시지 10개만 가볍게 요청)
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=10"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                messages = response.json()
                # 봇이 올린 메시지 중 '원가 대비 변동폭'이 포함된 가장 최신 텍스트 결합
                combined_text = ""
                for msg in messages:
                    content = msg.get("content", "")
                    if "원가 대비 변동폭" in content:
                        combined_text += content + "\n"
                
                if combined_text:
                    market_data[category] = parse_text(combined_text)
                    print(f"✨ [성공] {category} API 데이터 수집 완료.")
            else:
                print(f"❌ {category} 요청 실패 (코드: {response.status_code}). 토큰이 유효한지 확인하세요.")
        except Exception as e:
            print(f"❌ {category} 연결 에러: {e}")

def cron_job():
    print("🚀 최초 1회 API 데이터 수집 시작...")
    fetch_all_channels()
    while True:
        seconds_to_wait = get_seconds_until_next_hour()
        time.sleep(seconds_to_wait)
        print("🔔 정각 알림 API 수집 시작...")
        fetch_all_channels()

@app.route('/')
def home():
    next_time_str = get_next_update_time_str()
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>루나서버 종합 시세 마스터판</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; background-color: #1a1a24; color: #fff; padding: 20px; display: flex; flex-direction: column; align-items: center; }}
        h1 {{ color: #f1c40f; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); margin-bottom: 5px; }}
        .info-bar {{ background: #2c3e50; border: 1px solid #34495e; padding: 10px 20px; border-radius: 30px; font-weight: bold; margin-bottom: 25px; }}
        .container {{ width: 100%; max-width: 950px; background: #242432; padding: 25px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); margin-bottom: 30px; }}
        .rule-badge {{ font-size: 0.85rem; color: #bdc3c7; background: #34495e; padding: 3px 8px; border-radius: 5px; margin-left: 10px; font-weight: normal; }}
        h2 {{ border-left: 5px solid #f1c40f; padding-left: 10px; color: #f1c40f; font-size: 1.4rem; margin-top: 0; display: flex; align-items: center; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; background-color: #1c1c26; }}
        th, td {{ border: 1px solid #34495e; padding: 12px; text-align: center; }}
        th {{ background-color: #2c3e50; font-weight: bold; }}
        .up-row {{ background-color: rgba(46, 204, 113, 0.08); }}
        .down-row {{ background-color: rgba(231, 76, 60, 0.08); }}
        .up-badge {{ background-color: #2ecc71; color: #000; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }}
        .down-badge {{ background-color: #e74c3c; color: #fff; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; }}
        .limit-max {{ background-color: rgba(241, 196, 15, 0.2) !important; color: #f1c40f; font-weight: bold; }}
        .no-data {{ color: #777; padding: 30px; text-align: center; font-style: italic; }}
    </style>
</head>
<body>
    <h1>🌙 루나서버 종합 시세 실시간 알림판</h1>
    <div class="info-bar">⏱️ API 서버 가동 중 (다음 정각 갱신 예정: {next_time_str})</div>
    """

    for category in ["물고기", "농작물", "요리"]:
        emoji = "🐟" if category == "물고기" else "🌽" if category == "농작물" else "🍳"
        rules = SHOP_RULES.get(category, {"min_pct": 0, "max_pct": 0})
        
        html_content += f"""<div class="container">
            <h2>{emoji} {category} 변동 시세 테이블 <span class="rule-badge">한도: {rules['min_pct']}% ~ +{rules['max_pct']}%</span></h2>
            <table>
                <thead>
                    <tr><th>상태</th><th>아이템 이름</th><th>원가</th><th>이전 변동가</th><th>현재 변동가</th><th>변동폭</th></tr>
                </thead>
                <tbody>"""
        
        items = market_data[category]
        if not items:
            html_content += f'<tr><td colspan="6" class="no-data">첫 정각 데이터 수집 대기 중 또는 동기화 중입니다...</td></tr>'
        else:
            for item in items:
                badge = '<span class="up-badge">상승 ▲</span>' if item["status"] == "상승" else '<span class="down-badge">하락 ▼</span>'
                row_class = "up-row" if item["status"] == "상승" else "down-row"
                diff_style = "color: #2ecc71; font-weight:bold;" if item["status"] == "상승" else "color: #e74c3c; font-weight:bold;"
                
                if str(rules['max_pct']) in item["diff"] or str(abs(rules['min_pct'])) in item["diff"]:
                    row_class += " limit-max"
                
                html_content += f"""<tr class="{row_class}">
                    <td>{badge}</td>
                    <td style="text-align: left; font-weight: bold;">{item["name"]}</td>
                    <td>{item["cost"]}</td>
                    <td>{item["prev"]}</td>
                    <td>{item["current"]}</td>
                    <td style="{diff_style}">{item["diff"]}</td>
                </tr>"""
        html_content += "</tbody></table></div>"
    html_content += "</body></html>"
    return html_content

if __name__ == "__main__":
    # 💡 켜지자마자 즉시 1회 강제 수집하라는 명령어를 여기에 추가합니다!
    fetch_all_channels() 
    
    t = threading.Thread(target=cron_job, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=10000)
