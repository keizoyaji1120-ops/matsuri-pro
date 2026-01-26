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
    st.error("⚠️ 重要: requirements.txtに 'streamlit-js-eval' を追加してください。")
    st.stop()

# --- 設定 ---
warnings.filterwarnings("ignore")
st.set_page_config(page_title="魔釣Pro - 海況戦術盤", page_icon="⚓️")

# --- CSS ---
st.markdown("""
    <style>
    .big-font { font-size: 20px !important; font-weight: bold; color: #2c3e50; }
    .rec-box { border: 2px solid #e74c3c; padding: 10px; border-radius: 10px; background-color: #fff5f5; text-align: center; }
    .rec-title { font-size: 16px; color: #c0392b; font-weight: bold; margin-bottom: 5px; }
    .rec-content { font-size: 20px; font-weight: 800; color: #2c3e50; }
    .sub-info { font-size: 15px; color: #2c3e50; font-weight: bold; margin-top: 5px;}
    
    .weight-val { font-weight: bold; font-size: 28px; color: #d63031; line-height: 1.2; }
    .captain-note { font-size: 11px; color: #d63031; font-weight: bold; background-color: #ffeaea; padding: 3px 5px; border-radius: 4px; margin-top: 5px; display: inline-block; }
    
    .score-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 20px; border-radius: 15px; text-align: center;
        margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .score-label { font-size: 18px; font-weight: bold; margin-bottom: 5px; opacity: 0.9; }
    .score-value { font-size: 56px; font-weight: 900; line-height: 1; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
    .score-desc { font-size: 16px; font-weight: bold; margin-top: 5px; background-color: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; display: inline-block;}

    .seat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; background-color: #e3f2fd; padding: 15px; border-radius: 15px; text-align: center; border: 2px solid #2196f3; position: relative; }
    .seat-cell { background-color: white; padding: 10px; border-radius: 5px; border: 1px solid #ccc; font-weight: bold; color: #555; }
    .seat-best { background-color: #ffeb3b; border: 2px solid #fbc02d; color: #d32f2f; box-shadow: 0 0 10px rgba(255, 235, 59, 0.8); transform: scale(1.05); }
    .boat-shape { grid-column: 1 / -1; background-color: #607d8b; color: white; padding: 5px; border-radius: 50% 50% 5px 5px; margin-bottom: 10px; font-size: 12px; }
    .wind-arrow { font-size: 24px; margin-bottom: 5px; }
    .note-box { font-size: 12px; color: #666; margin-top: 15px; background-color: #f1f1f1; padding: 10px; border-radius: 5px; line-height: 1.5; }
    
    .forecast-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 10px; }
    .forecast-table th { background-color: #f8f9fa; border-bottom: 2px solid #ddd; padding: 8px; text-align: center; color: #555; font-size: 12px; }
    .forecast-table td { border-bottom: 1px solid #eee; padding: 8px 4px; text-align: center; color: #333; }
    .fc-time { font-weight: bold; color: #2c3e50; }
    .fc-tide-stop { color: #d63031; font-weight: bold; }
    
    .fc-score-high { color: #e74c3c; font-weight: 900; font-size: 16px; } 
    .fc-score-mid { color: #f39c12; font-weight: 900; font-size: 15px; } 
    .fc-score-low { color: #bdc3c7; font-weight: bold; } 

    .maker-rec { font-size: 13px; color: #0277bd; font-weight: bold; margin-top: 5px; border-top: 1px dashed #ccc; padding-top: 5px; }

    /* ラジオボタン周りの余白調整 */
    div[data-testid="stRadio"] {
        margin-top: -15px;
        margin-bottom: -25px !important;
    }
    div[data-testid="stRadio"] > label {
        margin-bottom: 0px !important;
    }

    .footer-box { background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin-top: 30px; font-size: 12px; color: #555; }
    .footer-title { font-weight: bold; color: #d63031; margin-bottom: 15px; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 5px;}
    .footer-box ul { padding-left: 20px; margin: 0; }
    .footer-box li { margin-bottom: 10px; line-height: 1.6; }
    </style>
""", unsafe_allow_html=True)

# --- 定数 (主要海峡の座標とURL) ---
JCG_POINTS = {
    "akashi": {
        "name": "明石海峡",
        "lat": 34.616, "lon": 135.021,
        "url": "https://www1.kaiho.mlit.go.jp/KAN5/tyouryuu/stream_akashi.html",
        "offset_min": 0, "ref_key": "akashi"
    },
    "naruto": {
        "name": "鳴門海峡",
        "lat": 34.238, "lon": 134.653,
        "url": "https://www1.kaiho.mlit.go.jp/KAN5/tyouryuu/stream_naruto.html",
        "offset_min": 0, "ref_key": "naruto"
    },
    "tomogashima": {
        "name": "友ヶ島水道",
        "lat": 34.283, "lon": 135.003,
        "url": "https://www1.kaiho.mlit.go.jp/KAN5/tyouryuu/stream_tomogashima.html",
        "offset_min": 0, "ref_key": "tomogashima"
    },
    "shodoshima": {
        "name": "小豆島 (播磨灘)",
        "lat": 34.480, "lon": 134.350, 
        "url": None, 
        "offset_min": 60, 
        "ref_key": "akashi"
    }
}

DEFAULT_LAT = 34.616
DEFAULT_LON = 135.021
HISTORICAL_TEMPS = { 1: 10.5, 2: 9.8, 3: 10.5, 4: 13.0, 5: 17.5, 6: 21.0, 7: 25.5, 8: 27.0, 9: 25.5, 10: 22.0, 11: 18.0, 12: 14.0 }

# --- 関数群 ---
def deg_to_cardinal(d):
    dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", 
            "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    idx = int((d + 11.25) / 22.5)
    return dirs[idx % 16]

def get_nearest_port(lat, lon):
    min_dist = float('inf')
    nearest_key = "akashi"
    for key, data in JCG_POINTS.items():
        dist = math.sqrt((lat - data["lat"])**2 + (lon - data["lon"])**2)
        if dist < min_dist:
            min_dist = dist
            nearest_key = key
    km_dist = min_dist * 111
    return JCG_POINTS[nearest_key], km_dist

@st.cache_data(ttl=300) 
def get_current_weather(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,cloud_cover,rain",
        "hourly": "sea_surface_temperature,wind_speed_10m,wind_direction_10m,weather_code,rain",
        "timezone": "Asia/Tokyo",
        "forecast_days": 2, 
        "wind_speed_unit": "ms"
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

@st.cache_data(ttl=1800)
def get_jcg_tide_data(target_url):
    try:
        try: import lxml
        except ImportError: return None 
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        dfs = pd.read_html(target_url, encoding='shift_jis')
        if dfs: return dfs[0]
        return None
    except Exception: return None

def parse_jcg_data(df, current_hour, current_min):
    if df is None: return None, None, False
    try:
        target_time = current_hour * 60 + current_min
        best_diff = 9999
        knot = 0.0
        direction = "不明"
        for index, row in df.iterrows():
            try:
                h = int(row[0])
                m = int(row[1])
                spd = float(row[3])
                dr = str(row[2])
                row_time = h * 60 + m
                diff = abs(target_time - row_time)
                if diff < best_diff:
                    best_diff = diff
                    knot = spd
                    direction = dr
            except: continue
        return knot, direction, True
    except Exception: return None, None, False

def get_hybrid_tide_data(target_datetime, now_datetime, port_info):
    ref_dt = target_datetime - datetime.timedelta(minutes=port_info["offset_min"])
    ref_port_key = port_info["ref_key"]
    ref_url = JCG_POINTS[ref_port_key]["url"]
    is_same_day_as_source = (ref_dt.day == now_datetime.day)
    
    success = False
    knot = 0.0
    dr_text = ""
    
    if is_same_day_as_source and ref_url:
        df = get_jcg_tide_data(ref_url)
        knot, dr_text, success = parse_jcg_data(df, ref_dt.hour, ref_dt.minute)
    
    if success:
        is_rising = ("西" in dr_text) or ("北" in dr_text)
        tide_factor = min(knot / 6.0, 1.0) 
        return tide_factor, is_rising, knot, True 
    else:
        moon_age = get_moon_age_simple(ref_dt)
        tide_factor, is_rising, knot = estimate_tide_current_logic(moon_age, ref_dt.hour + ref_dt.minute/60)
        return tide_factor, is_rising, knot, False 

def estimate_tide_current_logic(moon_age, hour):
    high_tide_base = 8.5
    delay = 0.8
    high_tide_time = (high_tide_base + (moon_age % 15) * delay) % 12
    diff = abs(hour - high_tide_time)
    if diff > 6: diff = 12 - diff 
    current_speed_factor = math.sin(diff * (math.pi / 6))
    is_rising = True
    if (high_tide_time - 6) < hour < high_tide_time: is_rising = True 
    else: is_rising = False 
    norm_age = moon_age % 15
    if norm_age <= 2 or norm_age >= 13: max_knot = 5.5
    elif 3 <= norm_age <= 5 or 10 <= norm_age <= 12: max_knot = 3.5
    else: max_knot = 2.0
    estimated_knot = max_knot * current_speed_factor
    return current_speed_factor, is_rising, estimated_knot

def calculate_best_seat(wind_dir, tide_dir_deg):
    boat_heading = wind_dir
    tide_from_deg = (tide_dir_deg + 180) % 360
    relative_angle = (tide_from_deg - boat_heading) % 360
    seat_name = "判定中"; seat_code = "none" 
    if 337.5 <= relative_angle or relative_angle < 22.5: seat_name = "ミヨシ (船首)"; seat_code = "m_center"
    elif 22.5 <= relative_angle < 67.5: seat_name = "右ミヨシ"; seat_code = "m_right"
    elif 67.5 <= relative_angle < 112.5: seat_name = "右舷 (胴の間)"; seat_code = "c_right"
    elif 112.5 <= relative_angle < 157.5: seat_name = "右トモ"; seat_code = "t_right"
    elif 157.5 <= relative_angle < 202.5: seat_name = "トモ (船尾)"; seat_code = "t_center"
    elif 202.5 <= relative_angle < 247.5: seat_name = "左トモ"; seat_code = "t_left"
    elif 247.5 <= relative_angle < 292.5: seat_name = "左舷 (胴の間)"; seat_code = "c_left"
    elif 292.5 <= relative_angle < 337.5: seat_name = "左ミヨシ"; seat_code = "m_left"
    return seat_name, seat_code

def calculate_matsuri_score(tide_factor, is_synced, wind_spd, temp, rain):
    score = 5.0 
    if tide_factor > 0.7: score += 2.5
    elif tide_factor > 0.4: score += 1.0
    elif tide_factor < 0.2: score -= 3.0
    if is_synced: score += 2.0
    else: score -= 1.0
    if 2.0 <= wind_spd <= 6.0: score += 1.0
    elif wind_spd > 8.0: score -= 2.0
    elif wind_spd < 1.0 and not is_synced: score -= 1.0
    if 18.0 <= temp <= 24.0: score += 2.0 
    elif 15.0 <= temp < 18.0 or temp > 24.0: score += 1.0
    elif 12.0 <= temp < 15.0: score += 0.0 
    elif 10.0 <= temp < 12.0: score -= 1.5 
    elif temp < 10.0: score -= 3.0 
    if rain > 0: score += 0.5
    if score < 1: score = 1
    if score > 10: score = 10
    return int(score)

def get_score_comment(score):
    if score >= 9: return "🔥 超・爆釣チャンス！"
    elif score >= 7: return "🎣 好条件！期待大"
    elif score >= 5: return "🐟 通常 (腕の見せ所)"
    elif score >= 3: return "😓 渋いかも (粘れ)"
    else: return "💀 激渋警報 (修行)"

def get_closest_weight(val):
    weights = [30, 45, 60, 80, 100, 120, 150]
    return min(weights, key=lambda x: abs(x - val))

def calc_strategy_realtime(wind_spd, wind_dir, tide_factor, is_rising, temp, cloud, rain, target_depth_mode):
    tide_dir_deg = 280 if is_rising else 100
    diff_angle = abs(wind_dir - tide_dir_deg)
    if diff_angle > 180: diff_angle = 360 - diff_angle
    is_synced = diff_angle < 90
    
    # --- ウェイト計算 ---
    multiplier = 1.1 
    if tide_factor > 0.7: multiplier += 0.5
    elif tide_factor > 0.3: multiplier += 0.2
    if is_synced: multiplier += 0.3 
    if wind_spd > 7.0: multiplier += 0.2 
    
    base_depth = 45 
    if target_depth_mode == "15m": base_depth = 15
    elif target_depth_mode == "30m": base_depth = 30
    elif target_depth_mode == "60m": base_depth = 60
    
    target_weight = get_closest_weight(base_depth * multiplier)
    
    # --- ネクタイ選定ロジック ---
    tie_size = "標準カーリー"
    maker_rec = "推奨例: START カーリー / がまかつ 桜幻" 
    
    if tide_factor < 0.2:
        tie_size = "極細ショート ＋ ワーム"
        maker_rec = "推奨例: START スキニー ＋ FishArrow フラッシュJ"
    elif temp < 12.0:
        tie_size = "極細ショートカーリー"
        maker_rec = "推奨例: Jackall フィネスカーリー / ササラボ 極薄"
    else:
        # 水深による形状変化 (v17.1: 15m 高活性対応)
        if target_depth_mode == "60m":
            tie_size = "強波動カーリー / ワイド"
            maker_rec = "推奨例: Jackall マスターカーリー / 松岡スペシャル"
        elif target_depth_mode == "30m":
            tie_size = "ショートカーリー (小粒)"
            maker_rec = "推奨例: START シリコンネクタイ / がまかつ 極細"
        elif target_depth_mode == "15m":
            # 浅場の高活性(潮が動いている)か？
            if tide_factor > 0.5:
                tie_size = "強波動ワイド / セミロング"
                maker_rec = "推奨例: Jackall マスターカーリー / 松岡スペシャル"
            else:
                tie_size = "マイクロカーリー (極小)"
                maker_rec = "推奨例: START ショートスキニー / 海遊 リトル"
        elif 6 <= datetime.datetime.now().month <= 8 and tide_factor > 0.5:
            tie_size = "フィッシュテール / ツイン"
            maker_rec = "推奨例: ササラボ 極厚 / Jackall イカクロー"
        elif rain > 0.5 or tide_factor > 0.8:
            tie_size = "強波動ワイド / ビッグ"
            maker_rec = "推奨例: Jackall マスターカーリー / 海遊 WG"
        else:
            tie_size = "ショートカーリー (標準)"
            maker_rec = "推奨例: START カーリー / がまかつ 桜幻"

    # --- カラー選定ロジック ---
    color = "オレンジ / 赤オレ"
    
    current_month = datetime.datetime.now().month
    is_nori_season = current_month in [11, 12, 1, 2, 3, 4]
    
    if rain >= 0.5:
        color = "黒金 / チャート (濁り対策)"
    elif tide_factor < 0.3:
        if is_nori_season: color = "海苔グリーン / コーラ (海苔パターン)"
        else: color = "レッドブラック / スモーク (スレ対策)"
    elif is_nori_season and cloud > 50:
        color = "コーラ / レッドゼブラ (海苔・シルエット)"
    elif temp < 12.0:
        if is_nori_season: color = "コーラ / マットブラック (低水温)"
        else: color = "ダークグリーン / マットブラック"
    elif cloud >= 90:
        color = "マジョーラゼブラ / 赤ゼブラ"
    elif 60 <= cloud < 90:
        color = "コーラ / 赤黒"
    elif 30 <= cloud < 60:
        color = "シマシマオレンジ / オレンジゼブラ"
    elif cloud < 30 and tide_factor > 0.3:
        color = "オレンジドット / 金オレ"
    elif wind_spd < 2.0 and cloud < 30:
        color = "ピンク / クリアレッド"
    elif is_synced and tide_factor > 0.6:
        color = "赤オレ / 蛍光オレンジ"

    # 水深 × 天候 アレンジ
    if target_depth_mode in ["15m", "30m"]:
        if "オレンジ" in color:
            if cloud < 50: color = "クリアオレンジ / 蛍光オレンジ (光透過)" 
            else: color = "オレンジ / 赤オレ (膨張色)" 
        elif "赤" in color:
            color = color.replace("赤", "クリアレッド") 
        elif "黒" in color or "ブラック" in color:
            if target_depth_mode == "15m": color = "スモーク / クリアブラック (ステルス)"
            else: color += " (スモーク/薄め)"
            
    elif target_depth_mode == "60m":
        if "オレンジ" in color:
            if cloud < 50: color = "金オレ / オレンジゴールド (フラッシング)" 
            else: color = "オレンジ (グロー) / チャート (視認性)" 
        elif "赤" in color:
            if cloud >= 50: color += " (グロー)"
        elif "グリーン" in color:
            color += " (チャート/ゴールド)"
        
    speed = "Medium (等速)"
    tactic = "バーチカル気味"
    if is_synced and wind_spd > 3.0:
        tactic = "ドテラ流し"
        speed = "High Speed (早巻き)"
    elif tide_factor < 0.3:
        if target_depth_mode == "15m":
            tactic = "キャスティング (必須)"
            speed = "Dead Slow (デッドスロー)"
        else:
            tactic = "キャスティング"
            speed = "Dead Slow (デッドスロー)"
            if temp > 15: speed = "Slow (スロー)"
        
    return target_weight, color, tie_size, maker_rec, speed, tactic, is_synced, tide_dir_deg

# --- メイン画面 ---
def main():
    st.markdown("""
        <h1 style='text-align: center; color: #2c3e50;'>⚓️ 魔釣 Pro</h1>
        <p style='text-align: center; font-size: 14px; color: gray;'>
            明石の「今」を制する<br>
            玄人のための海況戦術盤 [GPS搭載] v17.1
        </p>
    """, unsafe_allow_html=True)

    col_sw, col_status = st.columns([2, 3])
    with col_sw:
        use_gps = st.toggle("🛰️ GPSを利用する", value=True)

    # --- 水深選択 ---
    st.markdown("### 🎣 ターゲット水深 (Depth)")
    target_depth_mode = st.radio(
        "狙うポイントの水深を選択してください:",
        ["15m", "30m", "45m", "60m"],
        index=1, 
        horizontal=True
    )

    lat = DEFAULT_LAT
    lon = DEFAULT_LON
    gps_status_msg = "GPS未利用 (定点観測)"

    if use_gps:
        loc = get_geolocation()
        if loc and 'coords' in loc:
            lat = loc['coords']['latitude']
            lon = loc['coords']['longitude']
            gps_status_msg = f"📍 取得中: 北緯{lat:.3f} 東経{lon:.3f}"
            with col_status:
                st.success(gps_status_msg)
        else:
            gps_status_msg = "📡 GPS信号待ち (または拒否)..."
            with col_status:
                st.info(gps_status_msg)
    else:
        with col_status:
            st.warning("⚓️ 明石海峡大橋下 (定点観測)")

    with st.spinner('解析中...'):
        t_delta = datetime.timedelta(hours=9)
        JST = datetime.timezone(t_delta, 'JST')
        now = datetime.datetime.now(JST)

        port_info, dist_km = get_nearest_port(lat, lon)
        data = get_current_weather(lat, lon)
        
        if data:
            current = data["current"]
            current_hour = now.hour
            hourly_temps = data["hourly"].get("sea_surface_temperature", [])
            sst = hourly_temps[current_hour] if (hourly_temps and current_hour < len(hourly_temps) and hourly_temps[current_hour]) else HISTORICAL_TEMPS.get(now.month, 15)
            
            wind_spd = current["wind_speed_10m"]
            wind_dir = current["wind_direction_10m"]
            cloud = current["cloud_cover"]
            rain = current["rain"]
            
            tide_factor, is_rising, real_knot, is_official = get_hybrid_tide_data(now, now, port_info)
            
            rec_weight, rec_color, rec_size, rec_maker, rec_speed, rec_tactic, is_synced, tide_dir_deg = calc_strategy_realtime(
                wind_spd, wind_dir, tide_factor, is_rising, sst, cloud, rain, target_depth_mode
            )

            matsuri_score = calculate_matsuri_score(tide_factor, is_synced, wind_spd, sst, rain)
            score_comment = get_score_comment(matsuri_score)

            best_seat_name, seat_code = calculate_best_seat(wind_dir, tide_dir_deg)

            wind_cardinal = deg_to_cardinal(wind_dir) 
            tide_cardinal = deg_to_cardinal(tide_dir_deg) 
            
            if tide_factor < 0.1 and real_knot < 0.5: 
                tide_display = "★転流/潮止まり"
                knot_text = f"{real_knot:.1f} kt"
            else: 
                tide_display_suffix = "上げ" if is_rising else "下げ"
                tide_display = f"{tide_cardinal}流 ({tide_display_suffix})"
                knot_text = f"{real_knot:.1f} kt"

            st.markdown("---")
            
            st.markdown(f"""
            <div class="score-container">
                <div class="score-label">🌊 魔釣指数 (Matsuri Index)</div>
                <div class="score-value">{matsuri_score}<span style="font-size: 24px;">/10</span></div>
                <div class="score-desc">{score_comment}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(matsuri_score / 10.0)

            port_msg = f"{port_info['name']}"
            if port_info["offset_min"] != 0:
                port_msg += f" (時差補正 +{port_info['offset_min']}分)"
            elif dist_km > 20:
                port_msg += f" (距離 {int(dist_km)}km ※参考値)"
            else:
                port_msg += " (JCG公式)"

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("風向き・風速", f"{wind_cardinal}", f"{wind_spd}m / {wind_dir}°")
            c2.metric("潮流データ元", knot_text, port_msg)
            c3.metric("水温", f"{sst}℃", f"{'雨' if rain > 0 else '曇' if cloud > 60 else '晴'}")
            c4.metric("流れ", "同調" if is_synced else "逆/無", delta="Go!" if is_synced else "Stay", delta_color="normal" if is_synced else "off")

            st.markdown("### 💺 現在の有利ポジション (潮先)")
            st.caption("※スパンカーを使用し、船首を風上に向ける「縦流し」時の判定です。")
            
            def get_style(target_code):
                base = "seat-cell"
                if target_code == seat_code: return base + " seat-best"
                if seat_code == "m_center" and target_code in ["m_left", "m_right"]: return base + " seat-best"
                if seat_code == "t_center" and target_code in ["t_left", "t_right"]: return base + " seat-best"
                return base

            st.markdown(f"""
            <div class="seat-grid">
                <div class="boat-shape">
                    <div class="wind-arrow">↑ 風 (Wind)</div>
                    <div>▲ 船首 (ミヨシ)</div>
                </div>
                <div class="{get_style('m_left')}">左ミヨシ</div>
                <div class="{get_style('m_right')}">右ミヨシ</div>
                <div class="{get_style('c_left')}">左舷(胴)</div>
                <div class="{get_style('c_right')}">右舷(胴)</div>
                <div class="{get_style('t_left')}">左トモ</div>
                <div class="{get_style('t_right')}">右トモ</div>
                <div style="grid-column: 1 / -1; background-color: #90a4ae; color: white; border-radius: 0 0 10px 10px; padding: 5px;">
                    ▼ 船尾 (トモ)
                </div>
            </div>
            <div style="text-align: center; margin-top: 10px; font-weight: bold; color: #d63031;">
                ★今の狙い目は「{best_seat_name}」周辺です！
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"### 🦐 {target_depth_mode}エリア・リアルタイム攻め時")
            
            st.markdown(f"""
            <div class="rec-box">
                <div class="rec-title">推奨TGウェイト ({target_depth_mode} 想定)</div>
                <div class="weight-val">{rec_weight}g</div>
                <div class="captain-note">※船長の重さ指示がある場合は、必ずそちらに従ってください。</div>
                <div style="margin-top:10px; font-size:14px; font-weight:bold;">戦術: {rec_tactic}</div>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""
                <div class="rec-box" style="border-color: #f39c12; background-color: #fef9e7;">
                    <div class="rec-title">当たりネクタイ</div>
                    <div class="rec-content" style="font-size: 18px;">{rec_color}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""
                <div class="rec-box" style="border-color: #e67e22; background-color: #fdf2e9;">
                    <div class="rec-title">推奨サイズ / 形状</div>
                    <div class="rec-content" style="font-size: 18px;">{rec_size}</div>
                    <div class="maker-rec">{rec_maker}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="rec-box" style="border-color: #3498db; background-color: #ebf5fb; margin-top: 15px;">
                <div class="rec-title">リトリーブスピード</div>
                <div class="rec-content" style="font-size: 20px;">{rec_speed}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.info(f"**【玄人解説】**\n現在、風は**{wind_cardinal}**から吹いており船首はその方向を向いています。\n潮流は**{tide_cardinal}方向**へ**{knot_text}**の速さで流れているため、潮先となる**「{best_seat_name}」**にいち早くポイントが入ります。")

            st.markdown("### 🔮 この先4時間の予報 (Wind & Tide & Index)")
            forecast_html = "<table class='forecast-table'><thead><tr><th>時間</th><th>天気 / 風予報</th><th>潮流予報 (JCG/推測)</th><th>指数</th></tr></thead><tbody>"
            
            for i in range(1, 5):
                f_time = now + datetime.timedelta(hours=i)
                f_h = f_time.hour
                target_idx = now.hour + i
                
                fw_spd = 0
                fw_dir = 0
                ft_rain = 0
                ft_sst = sst
                fw_text = "- - -"
                
                if data["hourly"]["wind_speed_10m"] and len(data["hourly"]["wind_speed_10m"]) > target_idx:
                    fw_spd = data["hourly"]["wind_speed_10m"][target_idx]
                    fw_dir = data["hourly"]["wind_direction_10m"][target_idx]
                    ft_rain = data["hourly"]["rain"][target_idx]
                    ft_sst = data["hourly"]["sea_surface_temperature"][target_idx] if data["hourly"]["sea_surface_temperature"][target_idx] else sst
                    
                    fw_card = deg_to_cardinal(fw_dir)
                    fw_code = data["hourly"]["weather_code"][target_idx]
                    w_icon = "☀️"
                    if fw_code > 3: w_icon = "☁️"
                    if fw_code > 50: w_icon = "☔"
                    fw_text = f"{w_icon} {fw_card} {fw_spd}m"

                ft_fac, ft_rise, ft_knot, ft_off = get_hybrid_tide_data(f_time, now, port_info)
                tide_source = "" if ft_off else "<br><span style='font-size:10px;color:gray;'>(推測)</span>"
                
                if ft_fac < 0.1 and ft_knot < 0.5:
                    ft_text = f"<span class='fc-tide-stop'>★転流 / 潮止まり</span>{tide_source}"
                else:
                    ft_dir_s = "西 (上げ)" if ft_rise else "東 (下げ)"
                    ft_text = f"{ft_dir_s} {ft_knot:.1f}kt{tide_source}"
                
                ft_tide_dir_deg = 280 if ft_rise else 100
                diff_angle = abs(fw_dir - ft_tide_dir_deg)
                if diff_angle > 180: diff_angle = 360 - diff_angle
                ft_synced = diff_angle < 90
                
                f_score = calculate_matsuri_score(ft_fac, ft_synced, fw_spd, ft_sst, ft_rain)
                
                score_class = "fc-score-low"
                if f_score >= 8:
                    score_class = "fc-score-high"
                elif f_score >= 6:
                    score_class = "fc-score-mid"
                
                f_score_html = f"<span class='{score_class}'>{f_score}</span>"

                day_str = ""
                if f_time.day != now.day:
                    day_str = "<span style='font-size:10px;color:blue;'>(翌日)</span><br>"
                
                forecast_html += f"<tr><td class='fc-time'>{day_str}{f_h}:00</td><td>{fw_text}</td><td>{ft_text}</td><td>{f_score_html}</td></tr>"
            
            forecast_html += "</tbody></table>"
            st.markdown(forecast_html, unsafe_allow_html=True)

        else:
            st.error("天気データが取得できませんでした。しばらく経ってからリロードしてください。")

    st.markdown("---")
    if st.button("🔄 情報を更新する"):
        st.rerun()

    # --- 免責事項 ---
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
                本アプリの提案は推測ロジックに基づくものであり、実際の海況や釣果を保証するものではありません。特に潮流データは外部サイト（海上保安庁）の稼働状況により、推測値に切り替わる場合があります。
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
