import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import urllib.request
import urllib.parse
import datetime
import math
import ssl
import warnings
import time

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
    .rec-content { font-size: 18px; font-weight: 800; color: #2c3e50; }
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
    
    /* スマホ対応で余白と文字サイズを最適化した表CSS */
    .forecast-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; table-layout: fixed; }
    .forecast-table th { background-color: #f8f9fa; border-bottom: 2px solid #ddd; padding: 6px 2px; text-align: center; color: #555; font-size: 10px; word-wrap: break-word; }
    .forecast-table td { border-bottom: 1px solid #eee; padding: 6px 2px; text-align: center; color: #333; font-size: 11px; word-wrap: break-word; vertical-align: middle; }
    .fc-time { font-weight: bold; color: #2c3e50; font-size: 12px; }
    .fc-tide-stop { color: #d63031; font-weight: bold; }
    
    .fc-score-high { color: #e74c3c; font-weight: 900; font-size: 16px; } 
    .fc-score-mid { color: #f39c12; font-weight: 900; font-size: 15px; } 
    .fc-score-low { color: #bdc3c7; font-weight: bold; font-size: 14px; } 

    .maker-rec { font-size: 13px; color: #0277bd; font-weight: bold; margin-top: 5px; border-top: 1px dashed #ccc; padding-top: 5px; }

    div[data-testid="stRadio"] { margin-top: -15px; margin-bottom: -25px !important; }
    div[data-testid="stRadio"] > label { margin-bottom: 0px !important; }

    .footer-box { background-color: #f8f9fa; border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin-top: 30px; font-size: 12px; color: #555; }
    .footer-title { font-weight: bold; color: #d63031; margin-bottom: 15px; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 5px;}
    .footer-box ul { padding-left: 20px; margin: 0; }
    .footer-box li { margin-bottom: 10px; line-height: 1.6; }
    
    .link-button {
        display: block; width: 100%; background-color: #0288d1; color: white !important; text-align: center;
        padding: 15px; border-radius: 10px; font-weight: bold; text-decoration: none; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: background-color 0.3s; margin-top: 10px;
    }
    .link-button:hover { background-color: #0277bd; }
    .link-button-secondary { background-color: #009688; }
    .link-button-secondary:hover { background-color: #00796b; }
    
    /* 予報表内のネクタイサイズラベル */
    .size-label { display: inline-block; padding: 1px 4px; border-radius: 3px; font-size: 9px; margin-top: 2px; color: white; font-weight: bold; }
    .size-l { background-color: #e74c3c; } /* 赤 (大) */
    .size-m { background-color: #3498db; } /* 青 (中) */
    .size-s { background-color: #2ecc71; } /* 緑 (小) */
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
    },
    "seto_ohashi": {
        "name": "瀬戸大橋 (備讃瀬戸)",
        "lat": 34.396, "lon": 133.813, 
        "url": None, 
        "offset_min": 120, 
        "ref_key": "akashi"
    }
}

RELIABLE_SST_POINTS = {
    "akashi": {"lat": 34.580, "lon": 135.000}, 
    "naruto": {"lat": 34.230, "lon": 134.700}, 
    "tomogashima": {"lat": 34.350, "lon": 135.000}, 
    "shodoshima": {"lat": 34.450, "lon": 134.300},
    "seto_ohashi": {"lat": 34.380, "lon": 133.800}
}

DEFAULT_LAT = 34.616
DEFAULT_LON = 135.021

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
    return JCG_POINTS[nearest_key], km_dist, nearest_key

def calculate_historical_sst_precise(now_dt):
    monthly_temps = {
        1: 12.0, 2: 9.5, 3: 10.5, 4: 13.5, 5: 17.5, 6: 21.0,
        7: 25.0, 8: 27.5, 9: 26.0, 10: 22.5, 11: 18.5, 12: 15.0
    }
    month = now_dt.month
    day = now_dt.day
    hour = now_dt.hour
    
    current_val = monthly_temps[month]
    if day < 15:
        prev_month = month - 1 if month > 1 else 12
        prev_val = monthly_temps[prev_month]
        ratio = (day + 15) / 30.0
        base_temp = prev_val + (current_val - prev_val) * ratio
    else:
        next_month = month + 1 if month < 12 else 1
        next_val = monthly_temps[next_month]
        ratio = (day - 15) / 30.0
        base_temp = current_val + (next_val - current_val) * ratio
        
    diurnal_variation = 0.3 * math.sin(((hour - 9) / 24.0) * 2 * math.pi)
    final_temp = base_temp + diurnal_variation
    return round(final_temp, 1)

def fetch_open_meteo(lat, lon, retries=2):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,wind_direction_10m,cloud_cover,rain",
        "hourly": "sea_surface_temperature,wind_speed_10m,wind_direction_10m,weather_code,rain,cloud_cover",
        "daily": "sunrise,sunset",
        "timezone": "Asia/Tokyo",
        "forecast_days": 2,
        "wind_speed_unit": "ms"
    }
    req_url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(req_url)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
                return json.loads(res.read().decode())
        except Exception as e:
            if i < retries - 1:
                time.sleep(1) 
            else:
                return None

@st.cache_data(ttl=300) 
def get_current_weather(lat, lon):
    fixed_key = None
    for key, pt in JCG_POINTS.items():
        if abs(lat - pt["lat"]) < 0.001 and abs(lon - pt["lon"]) < 0.001:
            fixed_key = key
            break

    fetch_lat = lat
    fetch_lon = lon
    
    if fixed_key and fixed_key in RELIABLE_SST_POINTS:
        fetch_lat = RELIABLE_SST_POINTS[fixed_key]['lat']
        fetch_lon = RELIABLE_SST_POINTS[fixed_key]['lon']

    base_data = fetch_open_meteo(fetch_lat, fetch_lon)
    if not base_data: return None

    current_hour = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).hour
    hourly = base_data.get("hourly", {})
    sst_list = hourly.get("sea_surface_temperature", [])
    
    has_sst = False
    if sst_list and current_hour < len(sst_list) and sst_list[current_hour] is not None:
        has_sst = True
        base_data["sst_source"] = "search" if fixed_key else "local"
    
    if not has_sst and not fixed_key:
        search_offsets = [
            (-0.02, 0.00), (-0.05, 0.00), (-0.03, 0.03), (-0.03, -0.03), (0.00, 0.05)
        ]
        for d_lat, d_lon in search_offsets:
            search_lat = lat + d_lat
            search_lon = lon + d_lon
            search_data = fetch_open_meteo(search_lat, search_lon)
            if search_data:
                s_sst_list = search_data["hourly"].get("sea_surface_temperature", [])
                if s_sst_list and current_hour < len(s_sst_list) and s_sst_list[current_hour] is not None:
                    base_data["hourly"]["sea_surface_temperature"] = s_sst_list
                    base_data["hourly"]["cloud_cover"] = search_data["hourly"].get("cloud_cover", [])
                    base_data["sst_source"] = "search"
                    has_sst = True
                    break
    
    if not has_sst:
        base_data["sst_source"] = "none"

    return base_data

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
    weights = [30, 45, 60, 80, 100, 120, 150, 200, 250]
    return min(weights, key=lambda x: abs(x - val))

# 形状文字列から大・中・小のサイズラベルを判定する関数
def get_size_label(tie_size_str):
    if "強波動" in tie_size_str or "ビッグ" in tie_size_str or "ワイド" in tie_size_str or "ロング" in tie_size_str or "極厚" in tie_size_str:
        return "size-l", "大"
    elif "極細" in tie_size_str or "ショート" in tie_size_str or "マイクロ" in tie_size_str or "フィネス" in tie_size_str or "スリム" in tie_size_str:
        return "size-s", "小"
    else:
        return "size-m", "中"

def calc_strategy_realtime(wind_spd, wind_dir, tide_factor, is_rising, temp, cloud, rain, target_depth_mode, sunrise_dt, sunset_dt, current_dt, area_key):
    tide_dir_deg = 280 if is_rising else 100
    diff_angle = abs(wind_dir - tide_dir_deg)
    if diff_angle > 180: diff_angle = 360 - diff_angle
    is_synced = diff_angle < 90
    
    multiplier = 1.1 
    if tide_factor > 0.7: multiplier += 0.5
    elif tide_factor > 0.3: multiplier += 0.2
    if is_synced: multiplier += 0.3 
    if wind_spd > 7.0: multiplier += 0.2 
    
    base_depth = 45 
    if target_depth_mode == "15m": base_depth = 15
    elif target_depth_mode == "30m": base_depth = 30
    elif target_depth_mode == "60m": base_depth = 50 
    elif target_depth_mode == "80m": base_depth = 65 
    
    target_weight = get_closest_weight(base_depth * multiplier)
    
    current_month = current_dt.month
    is_nori_season = current_month in [12, 1, 2, 3, 4]
    is_summer = current_month in [6, 7, 8]

    # --- 激渋判定 (スリムストレートを出す条件) ---
    # 潮が動いていない(0.2未満)、または水温が極端に低い(10度未満)、または完全な海苔パターン時
    is_super_tough = (tide_factor < 0.2) or (temp < 10.0) or (is_nori_season and cloud > 80)

    # --- ネクタイ形状とメーカー ---
    tie_size = "標準カーリー"
    maker_rec = "推奨例: ジャッカル マスターカーリー / 海遊 WG" 

    # エリア別パターン判定 (v22.5: 細身カーリー優先、激渋時のみスリムストレート)
    if area_key == "naruto":
        if target_depth_mode in ["60m", "80m"] or tide_factor > 0.5:
            tie_size = "強波動ビッグカーリー / 極厚ツイン"
            maker_rec = "推奨例: ジャッカル マスターカーリー強波動 / sasalabo 極厚"
        elif is_super_tough:
            tie_size = "極細スリムストレート / 喰わせ特化"
            maker_rec = "推奨例: sasalabo 極薄ストレート / START スキニー"
        else:
            # 基本のローアピールは細身カーリー
            tie_size = "細身カーリー / バルキーショート"
            maker_rec = "推奨例: START マジカーリー / ジャッカル フィネスカーリー"
            
    elif area_key == "seto_ohashi":
        if target_depth_mode in ["60m", "80m"] or tide_factor > 0.6:
            tie_size = "中太カーリー / ロングワイド"
            maker_rec = "推奨例: START マジカーリー / 松岡スペシャル"
        elif is_super_tough:
            tie_size = "スリムストレート / フィネス"
            maker_rec = "推奨例: START シリコンネクタイ(ストレート) / ササラボ 極薄"
        else:
            tie_size = "細身カーリー / ショート"
            maker_rec = "推奨例: START ショートスキニー / ジャッカル デュアルカーリー"

    elif area_key == "shodoshima":
        if is_super_tough:
            tie_size = "極細スリムストレート / 究極喰わせ"
            maker_rec = "推奨例: ササラボ 極薄ストレート / START スキニー"
        elif target_depth_mode in ["15m", "30m"]:
            tie_size = "細身カーリー / 極細ショート"
            maker_rec = "推奨例: START ショートスキニー / ジャッカル フィネス"
        else:
            tie_size = "ツインカーリー / ロングカーリー"
            maker_rec = "推奨例: START ツイン / 松岡スペシャル"
            
    else: # 明石エリア
        if is_super_tough:
            # 明石の極限のタフコンディションのみスリムストレート
            tie_size = "極細スリムストレート / ワーム単体"
            maker_rec = "推奨例: ササラボ 極薄ストレート / 海遊 リトル(カット)"
        elif is_nori_season or temp < 12.0:
            # 通常の低水温・スレ時は細身カーリー優先
            tie_size = "細身ショートカーリー / マイクロ"
            maker_rec = "推奨例: ジャッカル フィネスカーリー / START ショートスキニー"
        elif is_summer:
            if target_depth_mode in ["60m", "80m"]:
                tie_size = "ワイドカーリー / ビッグシルエット"
                maker_rec = "推奨例: ジャッカル マスターカーリー / 海遊 WG"
            else:
                tie_size = "フィッシュテール / Wカーリー"
                maker_rec = "推奨例: 海遊 WGショート / ジャッカル イカクロー"
        else:
            if tide_factor > 0.6:
                tie_size = "ロングカーリー / 強波動"
                maker_rec = "推奨例: ジャッカル マスターカーリー / 海遊 WG"
            else:
                tie_size = "細身カーリー / スタンダード"
                maker_rec = "推奨例: ジャッカル マスターカーリー(細身) / 海遊 シングル"

    # --- 日照時間・UV量の判定 ---
    is_mazume = False
    is_night = False
    is_daytime = False
    
    if sunrise_dt and sunset_dt:
        current_dt_naive = current_dt.replace(tzinfo=None)
        sr = datetime.datetime.fromisoformat(sunrise_dt).replace(tzinfo=None)
        ss = datetime.datetime.fromisoformat(sunset_dt).replace(tzinfo=None)
        
        if (sr - datetime.timedelta(minutes=60)) <= current_dt_naive <= (sr + datetime.timedelta(minutes=90)): 
            is_mazume = True # 朝マズメ（UV弱い、ファーストカラー時間）
        elif (ss - datetime.timedelta(minutes=60)) <= current_dt_naive <= (ss + datetime.timedelta(minutes=60)): 
            is_mazume = True # 夕マズメ
        elif current_dt_naive > (sr + datetime.timedelta(minutes=90)) and current_dt_naive < (ss - datetime.timedelta(minutes=60)):
            is_daytime = True # 日中（UV強い、セカンド・サードカラー時間）
        
        if current_dt_naive < (sr - datetime.timedelta(minutes=30)) or current_dt_naive > (ss + datetime.timedelta(minutes=30)): 
            is_night = True

    # --- カラーロジック ---
    color = "オレンジ / 赤オレ"

    if is_night:
        color = "グロー / フルブラック (シルエット重視)"
    elif is_mazume:
        color = "蛍光オレンジ / ゼブラドット / しましまオレンジ [ファーストカラー]"
    else:
        if rain >= 0.5:
            color = "黒金 (クロキン) / しましまオレンジゴールドラメ [濁り対策]"
        elif cloud >= 80:
            if area_key == "naruto": 
                color = "グローゼブラ / オレンジゴールド"
            else: 
                color = "黒金 (クロキン) / マジョーラゼブラ [曇天パターン]"
        else:
            if tide_factor < 0.3:
                if area_key == "akashi" and is_nori_season:
                    color = "海苔グリーン / コーラ" 
                elif area_key == "shodoshima" or area_key == "seto_ohashi":
                    color = "グリーン / ケイムラ (ナチュラル・エビ)"
                else:
                    color = "赤黒 (レッドブラック) / スモーク [スレ対策]"
            else:
                if target_depth_mode in ["15m", "30m"]:
                    color = "赤黒 / リバーシブル赤オレ / マスターオレンジ [セカンドカラー]"
                elif target_depth_mode in ["45m", "60m", "80m"]:
                    color = "エビオレ / エビチリ / 網みオレ [サードカラー]"
                
    speed = "Medium (等速)"
    tactic = "バーチカル気味 (縦の釣り)"
    if is_synced and wind_spd > 3.0:
        tactic = "斜め引き (広範囲攻略)" 
        speed = "High Speed (早巻き)"
    elif tide_factor < 0.3:
        if target_depth_mode == "15m":
            tactic = "キャスティング (投げて横引き)"
            speed = "Dead Slow (デッドスロー)"
        else:
            tactic = "キャスティング (投げて横引き)"
            speed = "Dead Slow (デッドスロー)"
            if temp > 15: speed = "Slow (スロー)"
        
    return target_weight, color, tie_size, maker_rec, speed, tactic, is_synced, tide_dir_deg

# --- メイン画面 ---
def main():
    st.markdown("""
        <h1 style='text-align: center; color: #2c3e50;'>⚓️ 魔釣 Pro</h1>
        <p style='text-align: center; font-size: 14px; color: gray;'>
            瀬戸内タイラバの「今」を制する<br>
            玄人のための海況戦術盤<br>
            [明石/鳴門/小豆島/瀬戸大橋 対応] v22.5
        </p>
    """, unsafe_allow_html=True)

    col_sw, col_status = st.columns([2, 3])
    with col_sw:
        use_gps = st.toggle("🛰️ GPSを利用する (現在地から解析)", value=True)
    
    if not use_gps:
        manual_area = st.radio(
            "📍 定点観測エリアを選択:", 
            ["明石海峡", "鳴門海峡", "岡山沖 (小豆島)", "瀬戸大橋 (備讃瀬戸)"], 
            horizontal=True
        )
    else:
        manual_area = "明石海峡"

    st.markdown("### 🎣 ターゲット水深 (Depth)")
    target_depth_mode = st.radio(
        "狙うポイントの水深を選択してください:",
        ["15m", "30m", "45m", "60m", "80m"],
        index=2, 
        horizontal=True
    )

    if use_gps:
        loc = get_geolocation()
        if loc and 'coords' in loc:
            lat = loc['coords']['latitude']
            lon = loc['coords']['longitude']
            st.success("📍 GPS測位完了 (座標非表示)")
            port_info, dist_km, port_key = get_nearest_port(lat, lon)
        else:
            st.info("📡 GPS信号待ち (または拒否)...")
            lat = JCG_POINTS["akashi"]["lat"]
            lon = JCG_POINTS["akashi"]["lon"]
            port_info, dist_km, port_key = get_nearest_port(lat, lon)
    else:
        if manual_area == "明石海峡":
            lat = JCG_POINTS["akashi"]["lat"]
            lon = JCG_POINTS["akashi"]["lon"]
            port_key = "akashi"
            msg = "⚓️ 明石海峡 (定点観測)"
        elif manual_area == "鳴門海峡":
            lat = JCG_POINTS["naruto"]["lat"]
            lon = JCG_POINTS["naruto"]["lon"]
            port_key = "naruto"
            msg = "⚓️ 鳴門海峡 (定点観測)"
        elif manual_area == "瀬戸大橋 (備讃瀬戸)":
            lat = JCG_POINTS["seto_ohashi"]["lat"]
            lon = JCG_POINTS["seto_ohashi"]["lon"]
            port_key = "seto_ohashi"
            msg = "⚓️ 瀬戸大橋/備讃瀬戸周辺 (定点観測)"
        else:
            lat = JCG_POINTS["shodoshima"]["lat"]
            lon = JCG_POINTS["shodoshima"]["lon"]
            port_key = "shodoshima"
            msg = "⚓️ 岡山沖/小豆島周辺 (定点観測)"
            
        st.warning(msg)
        port_info = JCG_POINTS[port_key]
        dist_km = 0

    with st.spinner('気象データ解析中...'):
        t_delta = datetime.timedelta(hours=9)
        JST = datetime.timezone(t_delta, 'JST')
        now = datetime.datetime.now(JST)

        data = get_current_weather(lat, lon)
        
        if data:
            current = data["current"]
            current_hour = now.hour
            
            hourly_temps = data["hourly"].get("sea_surface_temperature", [])
            raw_
