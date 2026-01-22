import streamlit as st
import pandas as pd
import json
import urllib.request
import urllib.parse
import datetime
import math
import ssl
import warnings

# GPS取得用ライブラリ (インストール: pip install streamlit-js-eval)
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    st.error("ライブラリ不足: 'streamlit-js-eval' がインストールされていません。")
    st.stop()

# --- 設定 ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="魔釣Pro - Realtime", page_icon="⚓️")

# --- CSS ---
st.markdown("""
    <style>
    .big-font { font-size: 20px !important; font-weight: bold; color: #2c3e50; }
    .rec-box { border: 2px solid #e74c3c; padding: 15px; border-radius: 10px; background-color: #fff5f5; text-align: center; }
    .rec-title { font-size: 16px; color: #c0392b; font-weight: bold; margin-bottom: 5px; }
    .rec-content { font-size: 24px; font-weight: 800; color: #2c3e50; }
    .sub-info { font-size: 14px; color: #7f8c8d; }
    
    /* 免責事項エリアのデザイン */
    .footer-box {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 15px;
        margin-top: 30px;
        font-size: 12px;
        color: #555;
    }
    .footer-title {
        font-weight: bold;
        color: #d63031;
        margin-bottom: 10px;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 定数 ---
DEFAULT_LAT = 34.60  # 明石沖
DEFAULT_LON = 135.00
HISTORICAL_TEMPS = {
    1: 10.5, 2: 9.8, 3: 10.5, 4: 13.0, 5: 17.5, 6: 21.0,
    7: 25.5, 8: 27.0, 9: 25.5, 10: 22.0, 11: 18.0, 12: 14.0
}

# --- 関数群 ---
@st.cache_data(ttl=300) 
def get_current_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,cloud_cover,rain",
        "hourly": "sea_surface_temperature",
        "timezone": "Asia/Tokyo",
        "forecast_days": 1
    }
    req_url = f"{url}?{urllib.parse.urlencode(params)}"
    
    req = urllib.request.Request(req_url)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx) as res:
            return json.loads(res.read().decode())
    except:
        return None

def get_moon_age_simple(date):
    year, month, day = date.year, date.month, date.day
    if month < 3: year -= 1; month += 12
    p = math.floor(year / 4)
    age = (year + p + month * 9 / 25 + day + 11) % 30
    return age

def estimate_tide_current(moon_age, hour):
    high_tide_base = 8.5
    delay = 0.8
    high_tide_time = (high_tide_base + (moon_age % 15) * delay) % 12
    
    diff = abs(hour - high_tide_time)
    if diff > 6: diff = 12 - diff 
    
    current_speed_factor = math.sin(diff * (math.pi / 6))
    
    is_rising = True
    if (high_tide_time - 6) < hour < high_tide_time:
        is_rising = True 
    else:
        is_rising = False 

    return current_speed_factor, is_rising

def calc_strategy_realtime(wind_spd, wind_dir, tide_factor, is_rising, temp, cloud, rain):
    tide_dir_deg = 270 if is_rising else 90
    diff_angle = abs(wind_dir - tide_dir_deg)
    if diff_angle > 180: diff_angle = 360 - diff_angle
    
    is_synced = diff_angle < 90
    
    base_weight = 60
    if tide_factor > 0.8: base_weight += 20
    if is_synced: base_weight += 20
    if wind_spd > 7.0: base_weight += 20
    
    if base_weight > 120: base_weight = "120g〜150g" 
    elif base_weight < 45: base_weight = "45g"
    else: base_weight = f"{int(base_weight)}g"

    color = "オレンジ"
    if rain > 0: color = "ソリッドレッド/チャート"
    elif cloud > 80: color = "赤ゼブラ/チャート"
    elif temp < 12.0: color = "海苔グリーン/黒"
    elif temp > 22.0: color = "赤オレ/蛍光オレンジ"
    
    speed = "等速巻き"
    tactic = "バーチカル気味"
    
    if is_synced and wind_spd > 3.0:
        tactic = "ドテラ流し（ライン放出注意）"
        speed = "早巻きリアクション"
    elif tide_factor < 0.3:
        tactic = "キャスティングで広範囲に"
        speed = "デッドスロー"
        color += " (極細)"
        
    return base_weight, color, speed, tactic, is_synced

# --- メイン画面 ---
def main():
    st.markdown("""
        <h1 style='text-align: center; color: #2c3e50;'>⚓️ 魔釣 Pro</h1>
        <p style='text-align: center; font-size: 14px; color: gray;'>
            Real-time Akashi Tai-Raba Strategy
        </p>
    """, unsafe_allow_html=True)

    loc = get_geolocation()
    
    col_status, col_btn = st.columns([3, 1])
    with col_btn:
        st.write("GPS読込:自動")
        
    lat = DEFAULT_LAT
    lon = DEFAULT_LON
    
    if loc:
        lat = loc['coords']['latitude']
        lon = loc['coords']['longitude']
        with col_status:
            st.success(f"📍 現在地: 北緯{lat:.3f} 東経{lon:.3f}")
    else:
        with col_status:
            st.warning("📡 GPS未取得（明石海峡大橋付近を基準にします）")

    with st.spinner('海況を解析中...'):
        now = datetime.datetime.now()
        data = get_current_weather(lat, lon)
        
        if data:
            current = data["current"]
            current_hour = now.hour
            sst = data["hourly"]["sea_surface_temperature"][current_hour] if data["hourly"]["sea_surface_temperature"][current_hour] else HISTORICAL_TEMPS.get(now.month, 15)
            
            wind_spd = current["wind_speed_10m"]
            wind_dir = current["wind_direction_10m"]
            cloud = current["cloud_cover"]
            rain = current["rain"]
            
            moon_age = get_moon_age_simple(now)
            tide_factor, is_rising = estimate_tide_current(moon_age, now.hour + now.minute/60)
            
            tide_str = "激流" if tide_factor > 0.8 else ("緩潮" if tide_factor < 0.3 else "適度")
            if tide_factor < 0.2: tide_dir_text = "★潮止まり"
            else: tide_dir_text = "西流 (上げ)" if is_rising else "東流 (下げ)"
            
            rec_weight, rec_color, rec_speed, rec_tactic, is_synced = calc_strategy_realtime(
                wind_spd, wind_dir, tide_factor, is_rising, sst, cloud, rain
            )

            st.markdown("---")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("現在の風", f"{wind_spd}m", f"{wind_dir}°")
            c2.metric("推測潮流", tide_str, tide_dir_text)
            c3.metric("天気/水温", f"{sst}℃", f"雨量{rain}mm")
            c4.metric("潮同調", "同調(流れる)" if is_synced else "逆(立つ)", delta_color="off")

            st.markdown("### 🦐 魔釣・リアルタイム攻め時")
            
            st.markdown(f"""
            <div class="rec-box">
                <div class="rec-title">推奨ヘッドウェイト</div>
                <div class="rec-content">{rec_weight}</div>
                <div class="sub-info">戦術: {rec_tactic}</div>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""
                <div class="rec-box" style="border-color: #f39c12; background-color: #fef9e7;">
                    <div class="rec-title">当たりネクタイ</div>
                    <div class="rec-content" style="font-size: 20px;">{rec_color}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div class="rec-box" style="border-color: #3498db; background-color: #ebf5fb;">
                    <div class="rec-title">リトリーブ</div>
                    <div class="rec-content" style="font-size: 20px;">{rec_speed}</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.write("")
            st.info(f"""
            **【玄人解説】**
            現在、風は**{wind_dir}度**から吹いており、潮は**{tide_dir_text}**と予測されます。
            {'風と潮が同調しているため、船が速く流れます。底取り重視で重くしましょう。' if is_synced else '風と潮が喧嘩（または無風）しており、船が流れにくい状況です。キャストして斜めに引くか、軽めでフワリと見せましょう。'}
            """)

            if rain > 0 or cloud > 90:
                st.warning("⚠️ ローライトコンディションです。グローやチャート系、シルエットの出る黒などを混ぜてください。")
            if sst < 12:
                st.error("⚠️ 水温が低いです。ネクタイのボリュームを落とし、スローな展開を意識してください。")

        else:
            st.error("天気データの取得に失敗しました。")

    st.markdown("---")
    if st.button("🔄 最新情報に更新"):
        st.rerun()

    # --- 免責事項・利用規約エリア ---
    st.markdown("""
    <div class="footer-box">
        <div class="footer-title">⚠️ 利用規約・免責事項 (Terms of Use)</div>
        <ul>
            <li><strong>【営利利用の禁止】</strong><br>
            本アプリは個人の趣味の範囲での利用を目的としています。本アプリのソースコードや生成された情報を<strong>第三者へ販売・有償配布すること、および営利目的のイベント等で使用することを固く禁じます。</strong></li>
            
            <li><strong>【安全第一・船長の指示遵守】</strong><br>
            本アプリの予報に関わらず、現場では必ず<strong>遊漁船の船長の指示、および海上保安庁の安全情報</strong>を最優先してください。本アプリの使用中に生じた事故、怪我、スマートフォンの故障（水没等）について、開発者は一切の責任を負いません。</li>
            
            <li><strong>【情報の性質】</strong><br>
            本アプリの提案は推測ロジックに基づくものであり、実際の海況や釣果を保証するものではありません。</li>
            
            <li><strong>【データ出典】</strong><br>
            気象データは <a href="https://open-meteo.com/" target="_blank">Open-Meteo.com</a> のAPIを使用しています。<br>
            Weather data provided by Open-Meteo.com under <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC BY 4.0</a>.
            </li>
        </ul>
        <div style="text-align: center; margin-top: 10px;">
            © 2026 魔釣 - Matsuri Fishing Forecast (Personal Use Only)
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
