import streamlit as st
import pandas as pd
import json
import urllib.request
import urllib.parse
import datetime
import math
import ssl
import warnings

# GPS取得用ライブラリ
try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    st.error("ライブラリ不足: 'streamlit-js-eval' がインストールされていません。requirements.txtを確認してください。")
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
    .sub-info { font-size: 15px; color: #2c3e50; font-weight: bold; margin-top: 5px;}
    
    /* フッターデザイン修正 */
    .footer-box {
        background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px;
        padding: 20px; margin-top: 30px; font-size: 12px; color: #555;
    }
    .footer-title { font-weight: bold; color: #d63031; margin-bottom: 15px; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 5px;}
    .footer-box ul { padding-left: 20px; margin: 0; }
    .footer-box li { margin-bottom: 10px; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

# --- 定数 ---
# 明石海峡大橋付近（航路中央）の座標
DEFAULT_LAT = 34.616
DEFAULT_LON = 135.021

HISTORICAL_TEMPS = {
    1: 10.5, 2: 9.8, 3: 10.5, 4: 13.0, 5: 17.5, 6: 21.0,
    7: 25.5, 8: 27.0, 9: 25.5, 10: 22.0, 11: 18.0, 12: 14.0
}

# --- 関数群 ---
def deg_to_cardinal(d):
    """角度を16方位の文字列に変換する"""
    dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", 
            "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    idx = int((d + 11.25) / 22.5)
    return dirs[idx % 16]

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
    # 簡易計算ロジック
    high_tide_base = 8.5
    delay = 0.8
    high_tide_time = (high_tide_base + (moon_age % 15) * delay) % 12
    
    diff = abs(hour - high_tide_time)
    if diff > 6: diff = 12 - diff 
    
    current_speed_factor = math.sin(diff * (math.pi / 6))
    
    # 潮流の向き（明石基準）
    is_rising = True
    if (high_tide_time - 6) < hour < high_tide_time:
        is_rising = True  # 西へ流れる
    else:
        is_rising = False # 東へ流れる

    return current_speed_factor, is_rising

def calc_strategy_realtime(wind_spd, wind_dir, tide_factor, is_rising, temp, cloud, rain):
    # 潮の角度設定
    tide_dir_deg = 280 if is_rising else 100
    
    # 風と潮の角度差計算
    diff_angle = abs(wind_dir - tide_dir_deg)
    if diff_angle > 180: diff_angle = 360 - diff_angle
    
    # 同調判定
    is_synced = diff_angle < 90
    
    # --- ヘッド重量計算 (タングステン想定) ---
    base_weight = 60
    if tide_factor > 0.8: base_weight += 20
    if is_synced: base_weight += 20
    if wind_spd > 7.0: base_weight += 20
    
    # タングステン表記用に調整
    if base_weight > 120: base_weight = "120g〜150g" 
    elif base_weight < 45: base_weight = "45g"
    else: base_weight = f"{int(base_weight)}g"

    # --- ネクタイサイズ判定 ---
    tie_size = "標準カーリー"
    
    if temp < 12.0:
        tie_size = "極細ショート / ストレート" # 冬・低水温
    elif tide_factor < 0.2:
        tie_size = "ショート / スリム" # 潮止まり
    elif rain > 0.5:
        tie_size = "ワイド / 強波動" # 濁り
    elif tide_factor > 0.8 and is_synced:
        tie_size = "ロングカーリー / ワイド" # 高活性
    elif temp > 22.0:
        tie_size = "中厚カーリー" # 夏の高活性
    else:
        tie_size = "ショートカーリー" # 万能

    # --- ネクタイカラー判定 ---
    color = "オレンジ / 赤オレ" # デフォルト
    
    if rain >= 0.5:
        color = "黒金 / チャート"
    elif cloud >= 80:
        color = "マジョーラゼブラ / 赤ゼブラ"
    elif 30 <= cloud < 80:
        color = "オレンジゼブラ / オレンジ"
    elif temp < 12.0:
        color = "海苔グリーン / 黒"
    elif wind_spd < 2.0 and cloud < 30:
        color = "ピンク / クリアレッド"
    elif is_synced and tide_factor > 0.6:
        color = "赤オレ / 蛍光オレンジ"
    
    # --- 巻き速度・戦術 ---
    speed = "等速巻き"
    tactic = "バーチカル気味"
    
    if is_synced and wind_spd > 3.0:
        tactic = "ドテラ流し"
        speed = "早巻きリアクション"
    elif tide_factor < 0.3:
        tactic = "キャスティング"
        speed = "デッドスロー"
        if temp > 15:
             speed = "スロー〜普通"
        
    return base_weight, color, tie_size, speed, tactic, is_synced, tide_dir_deg

# --- メイン画面 ---
def main():
    st.markdown("""
        <h1 style='text-align: center; color: #2c3e50;'>⚓️ 魔釣 Pro</h1>
        <p style='text-align: center; font-size: 14px; color: gray;'>
            Real-time Akashi Tai-Raba Strategy v3.2
        </p>
    """, unsafe_allow_html=True)

    # --- GPSスイッチエリア ---
    col_sw, col_status = st.columns([2, 3])
    
    with col_sw:
        use_gps = st.toggle("🛰️ GPSを利用する", value=True)

    lat = DEFAULT_LAT
    lon = DEFAULT_LON

    if use_gps:
        loc = get_geolocation()
        if loc and 'coords' in loc:
            lat = loc['coords']['latitude']
            lon = loc['coords']['longitude']
            with col_status:
                st.success(f"📍 取得中: 北緯{lat:.3f} 東経{lon:.3f}")
        else:
            with col_status:
                st.info("📡 GPS信号待ち...")
    else:
        with col_status:
            st.warning("⚓️ 明石海峡大橋下 (定点観測)")

    # --- 解析処理 ---
    with st.spinner('風向き・潮流・水温を解析中...'):
        now = datetime.datetime.now()
        data = get_current_weather(lat, lon)
        
        if data:
            current = data["current"]
            current_hour = now.hour
            
            hourly_temps = data["hourly"].get("sea_surface_temperature", [])
            if hourly_temps and current_hour < len(hourly_temps) and hourly_temps[current_hour]:
                sst = hourly_temps[current_hour]
            else:
                sst = HISTORICAL_TEMPS.get(now.month, 15)
            
            wind_spd = current["wind_speed_10m"]
            wind_dir = current["wind_direction_10m"]
            cloud = current["cloud_cover"]
            rain = current["rain"]
            
            moon_age = get_moon_age_simple(now)
            tide_factor, is_rising = estimate_tide_current(moon_age, now.hour + now.minute/60)
            
            rec_weight, rec_color, rec_size, rec_speed, rec_tactic, is_synced, tide_dir_deg = calc_strategy_realtime(
                wind_spd, wind_dir, tide_factor, is_rising, sst, cloud, rain
            )

            wind_cardinal = deg_to_cardinal(wind_dir) 
            tide_cardinal = deg_to_cardinal(tide_dir_deg) 
            
            tide_speed_text = "激流" if tide_factor > 0.8 else ("緩潮" if tide_factor < 0.3 else "適度")
            if tide_factor < 0.2: 
                tide_display = "★潮止まり"
                tide_dir_display = "-"
            else:
                tide_display = f"{tide_cardinal}流 ({'上げ' if is_rising else '下げ'})"
                tide_dir_display = f"{tide_dir_deg}°"

            # --- UI表示 ---
            st.markdown("---")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("風向き", f"{wind_cardinal}", f"{wind_dir}° / {wind_spd}m")
            c2.metric("潮流(推測)", tide_display, tide_speed_text)
            c3.metric("水温・天気", f"{sst}℃", f"{'雨' if rain > 0 else '曇' if cloud > 60 else '晴'}")
            
            sync_label = "同調 (流れる)" if is_synced else "喧嘩/無風 (立つ)"
            c4.metric("船の流れ", sync_label, delta="Go!" if is_synced else "Stay", delta_color="normal" if is_synced else "off")

            st.markdown("### 🦐 魔釣・リアルタイム攻め時")
            
            # 推奨タングステン表示
            st.markdown(f"""
            <div class="rec-box">
                <div class="rec-title">推奨タングステン(TG)</div>
                <div class="rec-content">{rec_weight}</div>
                <div class="sub-info">戦術: {rec_tactic}</div>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""
                <div class="rec-box" style="border-color: #f39c12; background-color: #fef9e7;">
                    <div class="rec-title">当たりネクタイ (色)</div>
                    <div class="rec-content" style="font-size: 20px;">{rec_color}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div class="rec-box" style="border-color: #e67e22; background-color: #fdf2e9;">
                    <div class="rec-title">推奨サイズ (形状)</div>
                    <div class="rec-content" style="font-size: 20px;">{rec_size}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="rec-box" style="border-color: #3498db; background-color: #ebf5fb; margin-top: 15px;">
                <div class="rec-title">リトリーブスピード</div>
                <div class="rec-content" style="font-size: 20px;">{rec_speed}</div>
            </div>
            """, unsafe_allow_html=True)
                
            st.write("")
            st.info(f"""
            **【玄人解説】**
            現在、風は**{wind_cardinal} ({wind_dir}°) **から吹いています。
            潮流は**{tide_cardinal} ({tide_dir_deg}°) **方向への{tide_speed_text}と予測されます。
            {'風と潮の向きが揃っているため、船が速く流されます。' if is_synced else '風と潮の向きがズレている（または風が弱い）ため、船があまり流れません。'}
            """)

        else:
            st.error("データの取得に失敗しました。時間をおいて再読み込みしてください。")

    st.markdown("---")
    if st.button("🔄 情報を更新する"):
        st.rerun()

    # --- 免責事項・利用規約エリア（HTML構造修正済み） ---
    st.markdown("""
    <div class="footer-box">
        <div class="footer-title">⚠️ 利用規約・免責事項 (Terms of Use)</div>
        <ul>
            <li>
                <strong>【営利利用の禁止】</strong><br>
                本アプリは個人の趣味の範囲での利用を目的としています。本アプリのソースコードや生成された情報を<strong>第三者へ販売・有償配布すること、および営利目的のイベント等で使用することを固く禁じます。</strong>
            </li>
            
            <li>
                <strong>【安全第一・船長の指示遵守】</strong><br>
                本アプリの予報に関わらず、現場では必ず<strong>遊漁船の船長の指示、および海上保安庁の安全情報</strong>を最優先してください。本アプリの使用中に生じた事故、怪我、スマートフォンの故障（水没等）について、開発者は一切の責任を負いません。
            </li>
            
            <li>
                <strong>【情報の性質】</strong><br>
                本アプリの提案は推測ロジックに基づくものであり、実際の海況や釣果を保証するものではありません。特に潮流情報は計算値であり、実際の現場（反転流など）と異なる場合があります。
            </li>
            
            <li>
                <strong>【データ出典】</strong><br>
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
