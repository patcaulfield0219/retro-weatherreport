"""
╔══════════════════════════════════════════════════════════════════╗
║         Arcadia 5000 — 復古未來企業氣象終端                       ║
║         模仿 WeatherStar 4000 / The Weather Channel 風格         ║
║         作者：Python 全端開發專家                                 ║
╚══════════════════════════════════════════════════════════════════╝

依賴套件安裝：
    pip install requests pygame pillow

Weather API:
    Open-Meteo forecast + geocoding APIs, no API key required.

使用方法：
    1. Set CITY / COUNTRY / LATITUDE / LONGITUDE as the default station.
    2. Optional: point BGM_PATH to an .mp3/.wav music file.
    3. Run: python retro_weather_tv.py
    4. Use the CITY search box to jump to cities worldwide.
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import math
import random
import datetime
import requests
import queue
import os
import json
import tempfile
import wave
import struct
from io import BytesIO
import unicodedata
import sys
import ctypes
from ctypes.util import find_library

# ── 嘗試載入 pygame（音效可選功能）──────────────────────────────
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("[音效] pygame 未安裝，音效功能停用。執行 pip install pygame 以啟用。")

# ── 嘗試載入 PIL（圖像處理，雷達圖用）───────────────────────────
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageEnhance, ImageOps, ImageChops
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[圖像] Pillow 未安裝，雷達圖將使用簡化版。執行 pip install pillow 以啟用。")


# ════════════════════════════════════════════════════════════════
#  設定區塊 — 請依需求修改
# ════════════════════════════════════════════════════════════════
class Config:
    """集中管理所有設定參數"""

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSET_DIR = os.path.join(BASE_DIR, "assets")
    CONFIG_PATH = os.path.join(BASE_DIR, "retro_weather_config.json")

    # ── 天氣 API 設定 ──────────────────────────────────────────
    # Open-Meteo does not require an API key.
    CITY        = "Taipei"                         # Target city
    COUNTRY     = "TW"                             # Country code
    LATITUDE    = 25.0330
    LONGITUDE   = 121.5654
    API_UNITS   = "metric"                         # metric=攝氏 / imperial=華氏
    TEMP_UNIT   = "°C"

    # ── 背景音樂與語音提示設定 ────────────────────────────────
    BGM_PATH    = os.path.join(ASSET_DIR, "audio", "wiiUmiimaker.mp3")
    BOOT_SOUND_PATH = os.path.join(ASSET_DIR, "audio", "terminal_open.mp3")
    BGM_VOLUME  = 0.34     # 音量 0.0 ~ 1.0
    MUSIC_ENABLED = True
    SFX_ENABLED = True
    CUE_VOLUME = 0.72

    # ── 畫面尺寸 ──────────────────────────────────────────────
    WIN_WIDTH   = 800
    WIN_HEIGHT  = 600
    BEZEL_SIZE  = 24

    # ── 字體設定 ──────────────────────────────────────────────
    FONT_PATH   = os.path.join(ASSET_DIR, "fonts", "Belgrad.ttf")
    FONT_FAMILY = "Courier"
    FONT_FALLBACK = "Courier"
    ICON_FONT_FAMILY = "Apple Color Emoji"

    # ── 輪播間隔（秒）────────────────────────────────────────
    SLIDE_INTERVAL   = 8        # 每張看板顯示秒數
    API_REFRESH      = 300      # API 重新抓取間隔（秒），預設 5 分鐘

    # ── 顏色主題（WeatherStar x retro-future broadcast terminal）──
    BG_DARK     = "#090B0A"     # terminal black-green
    BG_MEDIUM   = "#20251C"     # oxidized metal panel
    BG_PANEL    = "#10140F"     # deep terminal panel
    BG_WARM     = "#2A1B12"     # corporate amber panel
    TEXT_YELLOW = "#F2C14E"     # Halcyon amber
    TEXT_WHITE  = "#D8D0B0"     # aged CRT white
    TEXT_CYAN   = "#54B7A2"     # phosphor teal
    TEXT_RED    = "#C94738"     # warning red
    TEXT_GREEN  = "#77A75B"     # radar green
    TEXT_ORANGE = "#D88945"     # brass orange
    TEXT_BLUE   = "#5D8F9E"
    BORDER_COL  = "#A77A3D"     # brass border
    SCAN_COLOR  = "#000000"     # CRT 掃描線顏色（半透明效果）

    # ── 跑馬燈設定 ────────────────────────────────────────────
    MARQUEE_SPEED    = 3        # 每次移動像素數（越大越快）
    MARQUEE_INTERVAL = 30       # 移動間隔（毫秒）
    MARQUEE_HEIGHT   = 30       # 跑馬燈區塊高度
    CONTROL_HEIGHT   = 46       # 底部控制列高度

    # ── CRT 掃描線 ────────────────────────────────────────────
    SCANLINE_STEP    = 7        # 掃描線間距（像素），越小越密
    SCANLINE_ALPHA   = 0.06     # 掃描線透明度（模擬效果強度）
    CRT_AMBIENCE_MS  = 90       # CRT 氣氛層刷新速度
    CRT_SCAN_STEP    = 11       # 全畫面淡掃描線間距；保持稀疏避免影響閱讀

    # ── 地圖雷達設定 ──────────────────────────────────────────
    MAP_ZOOM         = 10       # OpenStreetMap tile zoom. Larger = closer.
    MAP_TILE_URL     = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    MAP_USER_AGENT   = "RetroCast4000/1.0 (local Tk weather display)"
    REVERSE_GEOCODE_URL = "https://nominatim.openstreetmap.org/reverse"
    RAINVIEWER_API_URL = "https://api.rainviewer.com/public/weather-maps.json"
    RAINVIEWER_ZOOM    = 6
    OLLAMA_API_URL     = "http://localhost:11434/api/generate"
    OLLAMA_MODEL       = "llama3.2"
    OLLAMA_TIMEOUT     = 60

    # ── 企業廣告素材 ─────────────────────────────────────────
    AD_IMAGE_PATHS = [
        os.path.join(ASSET_DIR, "ads", "plasma_cutter.png"),
        os.path.join(ASSET_DIR, "ads", "plasma_cutter_alt.png"),
        os.path.join(ASSET_DIR, "ads", "adrena_time_syringe.png"),
        os.path.join(ASSET_DIR, "ads", "ace_exterminator.png"),
        os.path.join(ASSET_DIR, "ads", "spacers_gun.png"),
        os.path.join(ASSET_DIR, "ads", "morale.png"),
    ]
    AD_SLOGANS = {
        "PlasmaCutter": "SLICES. DICES. CAUTERIZES. PRODUCTIVITY HAS NEVER BEEN SO BRIGHT.",
        "AdreaTimeSyringe": "TWICE THE SPEED, HALF THE PRICE. BE A BETTER YOU WITH ADRENA-TIME.",
        "EAAEAE": "AUNTIE CLEO PRESENTS HEROISM FOR EVERY AUTHORIZED LUNCH BREAK.",
        "Spacers_Gun": "IT IS NOT THE BEST CHOICE. IT IS SPACER'S CHOICE.",
        "Morale": "WORKPLACE MALAISE IS MORAL BANKRUPTCY. REPORT JOY IMMEDIATELY.",
    }

    LOGO_PATHS = {
        "halcyon": os.path.join(ASSET_DIR, "logos", "halcyon_logo.webp"),
        "flaw": os.path.join(ASSET_DIR, "logos", "flaw.webp"),
        "auntie_cleo": os.path.join(ASSET_DIR, "logos", "auntie_cleo_logo.webp"),
        "aunties_choice": os.path.join(ASSET_DIR, "logos", "aunties_choice_logo.webp"),
        "spacers_choice": os.path.join(ASSET_DIR, "logos", "spacers_choice_logo.webp"),
        "order": os.path.join(ASSET_DIR, "logos", "order_ascendant_logo.webp"),
        "sub_rosa": os.path.join(ASSET_DIR, "logos", "sub_rosa_logo.webp"),
    }

    CONFIG_FIELDS = {
        "city": "CITY",
        "country": "COUNTRY",
        "latitude": "LATITUDE",
        "longitude": "LONGITUDE",
        "bgm_path": "BGM_PATH",
        "boot_sound_path": "BOOT_SOUND_PATH",
        "bgm_volume": "BGM_VOLUME",
        "music_enabled": "MUSIC_ENABLED",
        "sfx_enabled": "SFX_ENABLED",
        "cue_volume": "CUE_VOLUME",
        "font_path": "FONT_PATH",
        "slide_interval": "SLIDE_INTERVAL",
        "api_refresh": "API_REFRESH",
        "marquee_speed": "MARQUEE_SPEED",
        "crt_ambience_ms": "CRT_AMBIENCE_MS",
        "map_zoom": "MAP_ZOOM",
        "rainviewer_zoom": "RAINVIEWER_ZOOM",
    }

    @classmethod
    def load_from_json(cls):
        if not os.path.exists(cls.CONFIG_PATH):
            cls.save_to_json()
            return
        try:
            with open(cls.CONFIG_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            print(f"[Config] Could not read config.json: {exc}")
            return

        for json_key, attr in cls.CONFIG_FIELDS.items():
            if json_key not in data:
                continue
            current = getattr(cls, attr)
            value = data[json_key]
            try:
                if isinstance(current, bool):
                    value = bool(value)
                elif isinstance(current, int) and not isinstance(current, bool):
                    value = int(value)
                elif isinstance(current, float):
                    value = float(value)
            except (TypeError, ValueError):
                continue
            setattr(cls, attr, value)

    @classmethod
    def save_to_json(cls):
        data = {json_key: getattr(cls, attr) for json_key, attr in cls.CONFIG_FIELDS.items()}
        try:
            with open(cls.CONFIG_PATH, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[Config] Could not write config.json: {exc}")



# ════════════════════════════════════════════════════════════════
#  資料層 — 負責 API 串接與資料快取
# ════════════════════════════════════════════════════════════════
class WeatherData:
    """
    天氣資料管理器
    職責：API 呼叫、資料解析、快取管理
    設計原則：所有 HTTP 請求在背景執行緒進行，避免阻塞 UI
    """

    def __init__(self):
        self.current   = {}      # 目前天氣資料
        self.forecast  = []      # 3 日預報列表
        self.hourly    = []      # 12 小時逐時預報
        self.comparison = []     # 多城市比較資料
        self.last_fetch = None   # 最後更新時間
        self.error_msg  = ""     # 錯誤訊息
        self.is_loading = False  # 載入中旗標
        self._lock      = threading.Lock()  # 執行緒鎖，保護共享資料

    # ── 轉換天氣代碼為復古圖示 ────────────────────────────────
    @staticmethod
    def code_to_icon(weather_id: int, icon_code: str = "") -> str:
        """
        將 Open-Meteo WMO weather code 轉換為圖示
        """
        if weather_id in (95, 96, 99):
            return "⛈"
        elif weather_id in (51, 53, 55, 56, 57):
            return "🌦"
        elif weather_id in (61, 63, 65, 66, 67, 80, 81, 82):
            return "🌧"
        elif weather_id in (71, 73, 75, 77, 85, 86):
            return "❄️"
        elif weather_id in (45, 48):
            return "🌫"
        elif weather_id == 0:
            return "☀️"
        elif weather_id == 1:
            return "🌤"
        elif weather_id == 2:
            return "⛅"
        else:
            return "☁️"

    @staticmethod
    def code_to_ascii(weather_id: int) -> list:
        """
        將天氣代碼轉換為多行 ASCII 藝術圖示（用於主畫面）
        返回字串列表，每個元素為一行
        """
        if weather_id in (95, 96, 99):
            return ["  .--.  ", " (    ) ", "(_`-.._)", " /!!  !!\\", "  ~~~~  "]
        elif weather_id in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            return ["  .--.  ", " (    ) ", "(_`-.._)", " ' ' ' '", " ' ' ' '"]
        elif weather_id in (71, 73, 75, 77, 85, 86):
            return ["  .--.  ", " (    ) ", "(_`-.._)", " * * * *", " * * * *"]
        elif weather_id == 0:
            return ["   \\  / ", "  .-~~-.", " (      )", "  `-..-'", "   /  \\ "]
        elif weather_id in (1, 2):
            return [" .-~~-. ", "(      )", " `.__.'"," .--~-."," `-..-' "]
        else:
            return [" .--~~-.", "(      )", " )____( ", "(_______)","        "]

    @staticmethod
    def code_to_description(weather_id: int) -> str:
        descriptions = {
            0: "CLEAR SKY",
            1: "MAINLY CLEAR",
            2: "PARTLY CLOUDY",
            3: "OVERCAST",
            45: "FOG",
            48: "DEPOSITING RIME FOG",
            51: "LIGHT DRIZZLE",
            53: "MODERATE DRIZZLE",
            55: "DENSE DRIZZLE",
            56: "FREEZING DRIZZLE",
            57: "DENSE FREEZING DRIZZLE",
            61: "SLIGHT RAIN",
            63: "MODERATE RAIN",
            65: "HEAVY RAIN",
            66: "FREEZING RAIN",
            67: "HEAVY FREEZING RAIN",
            71: "SLIGHT SNOW",
            73: "MODERATE SNOW",
            75: "HEAVY SNOW",
            77: "SNOW GRAINS",
            80: "SLIGHT RAIN SHOWERS",
            81: "RAIN SHOWERS",
            82: "VIOLENT RAIN SHOWERS",
            85: "SLIGHT SNOW SHOWERS",
            86: "HEAVY SNOW SHOWERS",
            95: "THUNDERSTORM",
            96: "THUNDERSTORM WITH HAIL",
            99: "SEVERE THUNDERSTORM",
        }
        return descriptions.get(weather_id, "UNKNOWN CONDITIONS")

    def fetch_current_weather(self) -> dict:
        """
        串接 Open-Meteo Forecast API
        端點：https://api.open-meteo.com/v1/forecast
        """
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": Config.LATITUDE,
            "longitude": Config.LONGITUDE,
            "current": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "apparent_temperature",
                "is_day",
                "precipitation",
                "weather_code",
                "cloud_cover",
                "pressure_msl",
                "wind_speed_10m",
                "wind_direction_10m",
                "visibility",
            ]),
            "daily": "sunrise,sunset",
            "timezone": "auto",
            "wind_speed_unit": "kmh",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json()

        # ── 解析並標準化資料結構 ──────────────────────────────
        current = raw.get("current", {})
        daily = raw.get("daily", {})
        weather_id = int(current.get("weather_code", 3))
        sunrise = daily.get("sunrise", ["--T--:--"])[0][-5:]
        sunset = daily.get("sunset", ["--T--:--"])[0][-5:]
        humidity = current.get("relative_humidity_2m")
        visibility = current.get("visibility")
        visibility_km = "--"
        if isinstance(visibility, (int, float)):
            visibility_km = round(visibility / 1000, 1)

        return {
            "city"        : Config.CITY,
            "country"     : Config.COUNTRY,
            "temp"        : round(current.get("temperature_2m", 0), 1),
            "feels_like"  : round(current.get("apparent_temperature", 0), 1),
            "humidity"    : "--" if humidity is None else round(humidity),
            "pressure"    : round(current.get("pressure_msl", 0)),
            "wind_speed"  : round(current.get("wind_speed_10m", 0), 1),
            "wind_deg"    : current.get("wind_direction_10m", 0),
            "visibility"  : visibility_km,
            "description" : self.code_to_description(weather_id),
            "weather_id"  : weather_id,
            "icon"        : self.code_to_icon(weather_id),
            "ascii_art"   : self.code_to_ascii(weather_id),
            "sunrise"     : sunrise,
            "sunset"      : sunset,
            "clouds"      : current.get("cloud_cover", "--"),
            "lat"         : Config.LATITUDE,
            "lon"         : Config.LONGITUDE,
            "observations": self.fetch_real_observations(
                                Config.CITY, Config.LATITUDE, Config.LONGITUDE
                            ),
        }

    def fetch_forecast(self) -> list:
        """
        串接 Open-Meteo Daily Forecast API
        """
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": Config.LATITUDE,
            "longitude": Config.LONGITUDE,
            "daily": ",".join([
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
            ]),
            "hourly": "relative_humidity_2m",
            "forecast_days": 4,
            "timezone": "auto",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        raw = resp.json()
        daily = raw.get("daily", {})
        hourly = raw.get("hourly", {})
        humidity_by_date = {}
        humidity_groups = {}
        for stamp, value in zip(hourly.get("time", []), hourly.get("relative_humidity_2m", [])):
            if value is None:
                continue
            date_key = stamp.split("T", 1)[0]
            humidity_groups.setdefault(date_key, []).append(value)
        for date_key, values in humidity_groups.items():
            if values:
                humidity_by_date[date_key] = round(sum(values) / len(values))
        result = []
        for idx, date_str in enumerate(daily.get("time", [])[1:4], start=1):
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            weather_id = int(daily.get("weather_code", [3])[idx])
            result.append({
                "date"       : dt.strftime("%m/%d"),
                "weekday"    : ["MON","TUE","WED","THU","FRI","SAT","SUN"][dt.weekday()],
                "temp_max"   : round(daily.get("temperature_2m_max", [0])[idx], 1),
                "temp_min"   : round(daily.get("temperature_2m_min", [0])[idx], 1),
                "humidity"   : humidity_by_date.get(date_str, "--"),
                "description": self.code_to_description(weather_id),
                "icon"       : self.code_to_icon(weather_id),
                "weather_id" : weather_id,
                "pop"        : round(daily.get("precipitation_probability_max", [0])[idx] or 0),
            })
        return result

    def fetch_hourly_forecast(self) -> list:
        """Fetch the next 12 hours of real Open-Meteo forecast data."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": Config.LATITUDE,
            "longitude": Config.LONGITUDE,
            "hourly": ",".join([
                "temperature_2m",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
                "relative_humidity_2m",
                "visibility",
            ]),
            "forecast_days": 2,
            "timezone": "auto",
            "wind_speed_unit": "kmh",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        hourly = resp.json().get("hourly", {})
        times = hourly.get("time", [])
        now = datetime.datetime.now()
        result = []
        temps = hourly.get("temperature_2m", [])
        pops = hourly.get("precipitation_probability", [])
        codes = hourly.get("weather_code", [])
        winds = hourly.get("wind_speed_10m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        visibility = hourly.get("visibility", [])
        for idx, stamp in enumerate(times):
            if idx >= min(len(temps), len(pops), len(codes), len(winds)):
                break
            try:
                dt = datetime.datetime.fromisoformat(stamp)
            except ValueError:
                continue
            if dt < now.replace(minute=0, second=0, microsecond=0):
                continue
            code = int(codes[idx])
            result.append({
                "time": dt.strftime("%H:%M"),
                "hour": dt.hour,
                "temp": round(temps[idx], 1),
                "pop": round(pops[idx] or 0),
                "wind": round(winds[idx], 1),
                "humidity": round(humidity[idx]) if idx < len(humidity) and humidity[idx] is not None else "--",
                "visibility": round(visibility[idx] / 1000, 1) if idx < len(visibility) and visibility[idx] is not None else "--",
                "weather_id": code,
                "icon": self.code_to_icon(code),
                "description": self.code_to_description(code),
            })
            if len(result) >= 12:
                break
        return result

    def calculate_alert(self, current: dict, forecast: list, hourly: list) -> dict:
        """Corporate risk tier based on weather severity and operational impact."""
        temp = current.get("temp", 0) if current else 0
        wind = current.get("wind_speed", 0) if current else 0
        code = current.get("weather_id", 0) if current else 0
        max_pop = max([h.get("pop", 0) for h in hourly[:6]] + [d.get("pop", 0) for d in forecast[:1]] + [0])

        level = "CLEAR"
        color = Config.TEXT_GREEN
        message = "Atmospheric conditions are within profitable tolerance."

        if code in (95, 96, 99) or wind >= 55 or max_pop >= 85 or temp >= 38 or temp <= -5:
            level = "ASSET RISK"
            color = Config.TEXT_RED
            message = "Corporate assets may experience weather-related depreciation."
        elif code in (65, 67, 75, 82, 85, 86) or wind >= 38 or max_pop >= 65 or temp >= 34 or temp <= 2:
            level = "HAZARD"
            color = Config.TEXT_ORANGE
            message = "Operational inconvenience likely. Morale remains mandatory."
        elif code in (45, 48, 51, 53, 55, 61, 63, 71, 73, 80, 81) or wind >= 24 or max_pop >= 40:
            level = "WATCH"
            color = Config.TEXT_YELLOW
            message = "Supervisory awareness recommended for exposed personnel."

        return {"level": level, "color": color, "message": message, "pop": max_pop}

    def calculate_radar_profile(self, current: dict, hourly: list) -> dict:
        """Build a forecast-driven radar profile from Open-Meteo precipitation probability."""
        code = current.get("weather_id", 0) if current else 0
        max_pop = max([h.get("pop", 0) for h in hourly[:6]] + [0])
        rainy_code = code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99)
        base = max_pop / 100
        if rainy_code:
            base = max(base, 0.45)
        cell_count = 0 if base < 0.12 else min(10, max(3, int(2 + base * 9)))
        return {
            "pop": max_pop,
            "intensity": base,
            "cell_count": cell_count,
            "source": "OPEN-METEO FORECAST MODEL",
            "is_real_radar": False,
        }

    def generate_weather_summary(self, current: dict, forecast: list, hourly: list) -> dict:
        """Generate an AI weather summary with local Ollama when available."""
        fallback = self.local_weather_summary(current, forecast, hourly)
        next_hours = [
            {
                "time": h.get("time"),
                "temp": h.get("temp"),
                "pop": h.get("pop"),
                "wind": h.get("wind"),
                "humidity": h.get("humidity"),
            }
            for h in hourly[:4]
        ]
        near_forecast = [
            {
                "day": d.get("weekday") or d.get("date"),
                "weather": d.get("description"),
                "high_c": d.get("temp_max"),
                "low_c": d.get("temp_min"),
                "pop": d.get("pop"),
            }
            for d in forecast[:1]
        ]
        payload = {
            "city": current.get("city", Config.CITY),
            "country": current.get("country", Config.COUNTRY),
            "temperature_c": current.get("temp"),
            "feels_like_c": current.get("feels_like"),
            "description": current.get("description"),
            "humidity_percent": current.get("humidity"),
            "visibility_km": current.get("visibility"),
            "wind_kmh": current.get("wind_speed"),
            "cloud_cover_percent": current.get("clouds"),
            "pressure_hpa": current.get("pressure"),
            "alert_level": current.get("alert", {}).get("level"),
            "alert_message": current.get("alert", {}).get("message"),
            "rain_probability_percent": current.get("alert", {}).get("pop"),
            "next_hours": next_hours,
            "forecast": near_forecast,
        }
        prompt = (
            "You are writing text for a retro-future corporate colony weather terminal.\n"
            "Style: cheerful corporate space-colony propaganda with dry satire.\n"
            "Tone: mandatory morale, employee productivity, liability disclaimers,\n"
            "company-town bureaucracy, brass-and-teal terminal announcements.\n"
            "Do not mention or copy any existing game title, faction, character, or universe.\n"
            "Prioritize a useful integrated weather briefing over jokes.\n"
            "Summarize current conditions, comfort, wind, rain risk, and near forecast.\n"
            "Use only the real weather data in the JSON. Do not invent numbers.\n"
            "Return exactly 4 compact English lines, each under 64 characters.\n"
            "No markdown, no bullets, no numbering, no extra explanation.\n\n"
            f"WEATHER DATA JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        try:
            resp = requests.post(
                Config.OLLAMA_API_URL,
                json={
                    "model": Config.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.82,
                        "num_predict": 120,
                    },
                },
                timeout=Config.OLLAMA_TIMEOUT,
            )
            resp.raise_for_status()
            raw = resp.json()
            text = raw.get("response", "").strip()
            if not text:
                return {
                    "text": fallback,
                    "source": "LOCAL FALLBACK",
                    "ai_ok": False,
                    "error": "Ollama returned an empty response.",
                }
            return {
                "text": self._clean_ai_summary(text),
                "source": f"OLLAMA {Config.OLLAMA_MODEL}",
                "ai_ok": True,
                "error": "",
            }
        except Exception as exc:
            print(f"[AI Summary] Ollama unavailable: {exc}")
            return {
                "text": fallback,
                "source": "LOCAL FALLBACK",
                "ai_ok": False,
                "error": self._short_error(exc),
            }

    @staticmethod
    def _short_error(exc: Exception) -> str:
        message = str(exc).strip()
        if not message:
            return "Ollama did not respond."
        message = message.replace("\n", " ")
        return message[:110]

    @staticmethod
    def _clean_ai_summary(text: str) -> str:
        lines = []
        for raw in text.replace("\r", "").split("\n"):
            line = raw.strip().lstrip("-*0123456789. )")
            if line:
                lines.append(line[:66])
            if len(lines) >= 4:
                break
        return "\n".join(lines) if lines else text.strip()[:360]

    def local_weather_summary(self, current: dict, forecast: list, hourly: list) -> str:
        """Useful non-AI fallback summary based on the same live weather data."""
        city = current.get("city", Config.CITY)
        desc = current.get("description", "unknown conditions").lower()
        temp = current.get("temp", "--")
        feels = current.get("feels_like", "--")
        wind = current.get("wind_speed", "--")
        humidity = current.get("humidity", "--")
        alert = current.get("alert", {})
        pop = alert.get("pop", 0)
        tomorrow = forecast[0] if forecast else {}
        return "\n".join([
            f"{city} reports {desc}, {temp}{Config.TEMP_UNIT}; field comfort reads {feels}{Config.TEMP_UNIT}.",
            f"Wind allocation is {wind} km/h with humidity near {humidity} percent.",
            f"Rain probability tops out near {pop} percent in the current weather window.",
            f"Tomorrow: {tomorrow.get('description', 'conditions pending').lower()}, high {tomorrow.get('temp_max', '--')}{Config.TEMP_UNIT}.",
        ])

    def fetch_comparison(self, current: dict) -> list:
        """Fetch real current weather for a compact global city comparison board."""
        targets = [
            (current.get("city", Config.CITY), current.get("country", Config.COUNTRY),
             current.get("lat", Config.LATITUDE), current.get("lon", Config.LONGITUDE)),
            ("Los Angeles", "US", 34.0522, -118.2437),
            ("Tokyo", "JP", 35.6762, 139.6503),
            ("London", "GB", 51.5072, -0.1276),
            ("Sydney", "AU", -33.8688, 151.2093),
        ]
        rows = []
        seen = set()
        for city, country, lat, lon in targets:
            key = (round(float(lat), 2), round(float(lon), 2))
            if key in seen:
                continue
            seen.add(key)
            try:
                weather = self.fetch_point_weather(lat, lon)
                alert = self.calculate_alert(
                    {"temp": weather["temp"], "wind_speed": weather["wind_speed"],
                     "weather_id": weather["weather_id"]},
                    [],
                    [{"pop": 0}],
                )
                rows.append({
                    "city": city,
                    "country": country,
                    "temp": weather["temp"],
                    "weather": weather["weather"].title(),
                    "wind": weather["wind_speed"],
                    "risk": alert["level"],
                    "risk_color": alert["color"],
                    "lat": lat,
                    "lon": lon,
                })
            except Exception:
                continue
        return rows

    def search_cities(self, query: str, count: int = 6) -> list:
        """Use Open-Meteo Geocoding API and return matching cities."""
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": query.strip(), "count": count, "language": "en", "format": "json"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            raise ValueError(f"No city found for '{query}'.")
        places = []
        seen = set()
        for place in results:
            lat = float(place["latitude"])
            lon = float(place["longitude"])
            key = (place.get("name", query).lower(), place.get("country_code", ""), round(lat, 3), round(lon, 3))
            if key in seen:
                continue
            seen.add(key)
            admin = place.get("admin1") or place.get("admin2") or ""
            places.append({
                "city": place.get("name", query).title(),
                "country": place.get("country_code", ""),
                "admin": admin,
                "lat": lat,
                "lon": lon,
                "population": place.get("population", 0),
            })
        return places

    def search_city(self, query: str) -> dict:
        """Use Open-Meteo Geocoding API and return the first matching city."""
        return self.search_cities(query, count=1)[0]

    def set_location(self, city: str, country: str, lat: float, lon: float):
        Config.CITY = city
        Config.COUNTRY = country
        Config.LATITUDE = float(lat)
        Config.LONGITUDE = float(lon)
        Config.save_to_json()

    def fetch_real_observations(self, city: str, lat: float, lon: float) -> list:
        """Fetch real weather for nearby real-world coordinate points."""
        lat = float(lat)
        lon = float(lon)
        lon_step = 0.32 / max(0.35, math.cos(math.radians(lat)))
        points = [
            ("CENTER", city, lat, lon),
            ("NORTH", None, lat + 0.28, lon),
            ("EAST", None, lat, lon + lon_step),
            ("SOUTH", None, lat - 0.28, lon),
            ("WEST", None, lat, lon - lon_step),
            ("NE", None, lat + 0.20, lon + lon_step * 0.72),
            ("SW", None, lat - 0.20, lon - lon_step * 0.72),
            ("SE", None, lat - 0.20, lon + lon_step * 0.72),
        ]
        rows = []
        seen_names = {}
        for signal, preset_name, p_lat, p_lon in points:
            try:
                weather = self.fetch_point_weather(p_lat, p_lon)
                base_name = preset_name or self.reverse_place_name(p_lat, p_lon, signal)
                name_key = self._normalize_place_key(base_name)
                if name_key in seen_names:
                    suffix = signal.title() if signal != "CENTER" else "Center"
                    name = f"{base_name} {suffix}"[:24]
                else:
                    name = base_name
                seen_names[name_key] = seen_names.get(name_key, 0) + 1
                rows.append({
                    "city": name,
                    "temp": weather["temp"],
                    "weather": weather["weather"].title(),
                    "wind": self.wind_direction(weather["wind_deg"]),
                    "speed": weather["wind_speed"],
                    "signal": "LOCKED" if signal == "CENTER" else "LIVE",
                    "lat": p_lat,
                    "lon": p_lon,
                })
            except Exception:
                continue

        if len(rows) >= 3:
            return rows
        return self.synthetic_observations(city, 0, 3, 0, 0)

    @staticmethod
    def _normalize_place_key(value: str) -> str:
        return "".join(ch for ch in value.lower() if ch.isalnum())

    def fetch_point_weather(self, lat: float, lon: float) -> dict:
        """Fetch real current weather at a coordinate from Open-Meteo."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ",".join([
                "temperature_2m",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
            ]),
            "timezone": "auto",
            "wind_speed_unit": "kmh",
        }
        resp = requests.get(url, params=params, timeout=6)
        resp.raise_for_status()
        current = resp.json().get("current", {})
        code = int(current.get("weather_code", 3))
        return {
            "temp": round(current.get("temperature_2m", 0), 1),
            "weather": self.code_to_description(code),
            "weather_id": code,
            "wind_speed": round(current.get("wind_speed_10m", 0), 1),
            "wind_deg": current.get("wind_direction_10m", 0),
        }

    def reverse_place_name(self, lat: float, lon: float, fallback: str) -> str:
        """Reverse geocode a nearby point into a real place name."""
        params = {
            "lat": lat,
            "lon": lon,
            "format": "jsonv2",
            "zoom": 10,
            "addressdetails": 1,
            "namedetails": 1,
        }
        headers = {
            "User-Agent": Config.MAP_USER_AGENT,
            "Accept-Language": "en",
        }
        resp = requests.get(Config.REVERSE_GEOCODE_URL, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        raw = resp.json()
        namedetails = raw.get("namedetails", {})
        for key in ("name:en", "name"):
            value = namedetails.get(key)
            if value:
                return self.english_place_name(value, fallback)
        address = raw.get("address", {})
        for key in ("city", "town", "village", "municipality", "suburb", "county", "state_district"):
            value = address.get(key)
            if value:
                return self.english_place_name(value, fallback)
        display = raw.get("name") or raw.get("display_name", "")
        if display:
            return self.english_place_name(display.split(",")[0], fallback)
        return f"{Config.CITY} {fallback}"

    @staticmethod
    def english_place_name(value: str, fallback: str) -> str:
        ascii_name = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        ascii_name = " ".join(ascii_name.replace("-", " ").split())
        return (ascii_name or fallback).title()[:24]

    def synthetic_observations(self, city: str, temp: float, weather_code: int,
                               wind_speed: float, wind_deg: float) -> list:
        """Create local observation rows centered on the searched city."""
        sectors = [
            ("Central", 0.0, 0, 0, "LOCKED"),
            ("North Ridge", -1.6, -22, 2, "RIDGE"),
            ("East Port", -0.7, 55, 4, "COAST"),
            ("South Gate", 1.4, 148, -1, "URBAN"),
            ("West Relay", 0.8, 235, 3, "RELAY"),
            ("Outer Farms", -2.2, 310, -2, "RURAL"),
            ("High Station", -3.4, 15, 6, "HIGH"),
            ("Low Basin", 2.1, 188, 1, "BASIN"),
        ]
        rows = []
        for idx, (label, delta, wind_shift, speed_delta, signal) in enumerate(sectors):
            code = weather_code
            if idx in (2, 5) and weather_code in (0, 1, 2):
                code = 2
            elif idx in (6,) and weather_code in (61, 63, 65, 80, 81, 82):
                code = 45
            station_name = city if idx == 0 else f"{city} {label}"
            rows.append({
                "city": station_name,
                "temp": round(float(temp) + delta, 1),
                "weather": self.code_to_description(int(code)).title(),
                "wind": self.wind_direction((float(wind_deg) + wind_shift) % 360),
                "speed": max(0, round(float(wind_speed) + speed_delta, 1)),
                "signal": signal,
            })
        return rows

    def refresh_async(self, callback=None, progress_callback=None):
        """
        在背景執行緒中執行 API 呼叫
        callback: 完成後呼叫（傳入 success:bool）
        這是確保 GUI 不卡死的關鍵設計
        """
        def _worker():
            with self._lock:
                self.is_loading = True
                self.error_msg  = ""

            success = False
            try:
                if progress_callback:
                    progress_callback(12, "CONTACTING WEATHER RELAY")
                current  = self.fetch_current_weather()
                if progress_callback:
                    progress_callback(34, "CURRENT CONDITIONS RECEIVED")
                try:
                    if progress_callback:
                        progress_callback(48, "DOWNLOADING DAILY FORECAST")
                    forecast = self.fetch_forecast()
                except Exception:
                    forecast = list(self.forecast)
                try:
                    if progress_callback:
                        progress_callback(62, "DOWNLOADING HOURLY TIMELINE")
                    hourly = self.fetch_hourly_forecast()
                except Exception:
                    hourly = list(self.hourly)
                current["alert"] = self.calculate_alert(current, forecast, hourly)
                current["radar"] = self.calculate_radar_profile(current, hourly)
                if progress_callback:
                    progress_callback(76, "GENERATING OLLAMA SUMMARY")
                current["ai_summary"] = self.generate_weather_summary(current, forecast, hourly)
                try:
                    if progress_callback:
                        progress_callback(90, "SYNCING REGIONAL COMPARISON")
                    comparison = self.fetch_comparison(current)
                except Exception:
                    comparison = list(self.comparison)
                with self._lock:
                    self.current    = current
                    self.forecast   = forecast
                    self.hourly     = hourly
                    self.comparison = comparison
                    self.last_fetch = datetime.datetime.now()
                success = True
            except requests.exceptions.ConnectionError:
                if progress_callback:
                    progress_callback(96, "NETWORK FAILED; SYNTHETIC FEED ONLINE")
                with self._lock:
                    self.error_msg = "Network link failed. Synthetic data online."
                self._load_mock_data()
                success = True  # 用模擬資料繼續運作
            except requests.exceptions.HTTPError as e:
                if progress_callback:
                    progress_callback(96, "API ERROR; SYNTHETIC FEED ONLINE")
                with self._lock:
                    self.error_msg = f"API error {e.response.status_code}. Synthetic data online."
                self._load_mock_data()
                success = True
            except Exception as e:
                if progress_callback:
                    progress_callback(96, "UNKNOWN ERROR; SYNTHETIC FEED ONLINE")
                with self._lock:
                    self.error_msg = f"Unknown error: {str(e)[:30]}"
                self._load_mock_data()
                success = True
            finally:
                with self._lock:
                    self.is_loading = False

            if progress_callback:
                progress_callback(100, "BROADCAST DATA READY")
            if callback:
                callback(success)

        thread = threading.Thread(target=_worker, daemon=True, name="WeatherFetcher")
        thread.start()

    def _load_mock_data(self):
        """
        載入模擬天氣資料（API 無法使用時的備用方案）
        """
        with self._lock:
            self.current = {
                "city"        : Config.CITY,
                "country"     : Config.COUNTRY,
                "temp"        : 26.5,
                "feels_like"  : 29.3,
                "humidity"    : 75,
                "pressure"    : 1013,
                "wind_speed"  : 18.2,
                "wind_deg"    : 135,
                "visibility"  : 8,
                "description" : "PARTLY CLOUDY",
                "weather_id"  : 802,
                "icon"        : "⛅",
                "ascii_art"   : WeatherData.code_to_ascii(802),
                "sunrise"     : "05:48",
                "sunset"      : "18:32",
                "clouds"      : 45,
                "alert"       : {"level": "WATCH", "color": Config.TEXT_YELLOW,
                                 "message": "Synthetic feed active. Supervisor awareness recommended.",
                                 "pop": 42},
                "radar"       : {"pop": 42, "intensity": 0.42, "cell_count": 5,
                                 "source": "SYNTHETIC FORECAST MODEL",
                                 "is_real_radar": False},
                "ai_summary"  : {"text": (
                    f"{Config.CITY} reports synthetic partly cloudy conditions at 26.5{Config.TEMP_UNIT}.\n"
                    "Worker comfort remains acceptable, pending supervisor interpretation.\n"
                    "Rain risk is moderate enough to justify umbrella-related productivity.\n"
                    "Corporate morale recommends calm compliance until the live feed returns."
                ), "source": "LOCAL FALLBACK", "ai_ok": False,
                    "error": "Live weather or Ollama summary was unavailable."},
            }
            self.forecast = [
                {"date":"TOMORROW", "weekday":"TUE", "temp_max":28.0, "temp_min":22.0,
                 "humidity":70, "description":"PARTLY SUNNY",
                 "icon":"🌤", "weather_id":801, "pop":15},
                {"date":"NEXT DAY", "weekday":"WED", "temp_max":25.0, "temp_min":20.0,
                 "humidity":85, "description":"SCATTERED SHOWERS",
                 "icon":"🌧", "weather_id":521, "pop":70},
                {"date":"DAY THREE","weekday":"THU","temp_max":23.0, "temp_min":19.0,
                 "humidity":80, "description":"CLOUDY",
                 "icon":"☁️", "weather_id":804, "pop":30},
            ]
            base = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
            self.hourly = [
                {
                    "time": (base + datetime.timedelta(hours=i)).strftime("%H:%M"),
                    "hour": (base + datetime.timedelta(hours=i)).hour,
                    "temp": round(26.5 + math.sin(i / 2) * 2.3, 1),
                    "pop": max(5, min(85, 20 + i * 4)),
                    "wind": round(12 + math.cos(i / 3) * 4, 1),
                    "weather_id": 2 if i < 5 else 61,
                    "icon": WeatherData.code_to_icon(2 if i < 5 else 61),
                    "description": WeatherData.code_to_description(2 if i < 5 else 61),
                }
                for i in range(12)
            ]
            self.comparison = [
                {"city": Config.CITY, "country": Config.COUNTRY, "temp": 26.5,
                 "weather": "Partly Cloudy", "wind": 18.2, "risk": "WATCH",
                 "risk_color": Config.TEXT_YELLOW},
                {"city": "Los Angeles", "country": "US", "temp": 23.8,
                 "weather": "Clear Sky", "wind": 11.4, "risk": "CLEAR",
                 "risk_color": Config.TEXT_GREEN},
                {"city": "Tokyo", "country": "JP", "temp": 21.1,
                 "weather": "Overcast", "wind": 14.0, "risk": "WATCH",
                 "risk_color": Config.TEXT_YELLOW},
            ]
            self.last_fetch = datetime.datetime.now()

    def wind_direction(self, deg: int) -> str:
        """將風向角度轉換為中文方向"""
        dirs = ["N","NE","E","SE","S","SW","W","NW"]
        return dirs[round(deg / 45) % 8]


# ════════════════════════════════════════════════════════════════
#  音效層 — 背景音樂控制器
# ════════════════════════════════════════════════════════════════
class AudioController:
    """
    背景音樂與復古提示音控制器（依賴 pygame.mixer）
    """
    def __init__(self):
        self.initialized = False
        self.is_playing  = False
        self.sfx_enabled = Config.SFX_ENABLED
        self.generated_bgm_path = ""
        self.bgm_sound = None
        self.bgm_channel = None
        self.cue_sounds = {}
        if not PYGAME_AVAILABLE:
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.initialized = True
            self._prepare_cues()
        except Exception as e:
            print(f"[音效] pygame 初始化失敗：{e}")

    def load_and_play(self, path: str):
        """載入並播放背景音樂（循環播放）；路徑留空時改播放內建合成器 loop"""
        if not self.initialized:
            return
        try:
            if path:
                if not os.path.exists(path):
                    print(f"[Audio] Music file not found: {path}. Falling back to generated synth loop.")
                    path = ""
            if path:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(Config.BGM_VOLUME)
                pygame.mixer.music.play(loops=-1)  # -1 = 無限循環
                self.bgm_channel = None
            else:
                if not self.generated_bgm_path:
                    self.generated_bgm_path = self._make_synth_loop()
                self.bgm_sound = pygame.mixer.Sound(self.generated_bgm_path)
                self.bgm_sound.set_volume(Config.BGM_VOLUME)
                self.bgm_channel = self.bgm_sound.play(loops=-1)
            self.is_playing = True
        except Exception as e:
            print(f"[音效] 載入音樂失敗：{e}（請確認檔案路徑：{path}）")

    def set_music_volume(self, volume: float):
        """Set current background music volume for ducking / restore."""
        if not self.initialized:
            return
        volume = max(0.0, min(1.0, float(volume)))
        try:
            if self.bgm_channel:
                self.bgm_channel.set_volume(volume)
            else:
                pygame.mixer.music.set_volume(volume)
        except Exception:
            pass

    def duck_music(self, volume: float = 0.2):
        self.set_music_volume(volume)

    def restore_music(self, volume: float = 1.0):
        self.set_music_volume(volume)

    def toggle(self) -> bool:
        """切換播放/暫停，返回新的播放狀態"""
        if not self.initialized:
            return False
        if self.is_playing:
            if self.bgm_channel:
                self.bgm_channel.pause()
            else:
                pygame.mixer.music.pause()
            self.is_playing = False
        else:
            if self.bgm_channel:
                self.bgm_channel.unpause()
            elif Config.BGM_PATH:
                pygame.mixer.music.unpause()
            else:
                self.load_and_play("")
            self.is_playing = True
        return self.is_playing

    def toggle_sfx(self) -> bool:
        """Toggle short terminal cue sounds."""
        self.sfx_enabled = not self.sfx_enabled
        if self.sfx_enabled:
            self.play_cue("enable")
        return self.sfx_enabled

    def play_cue(self, cue_name: str = "slide"):
        """播放短促的復古終端提示音。"""
        if not self.initialized or not self.sfx_enabled:
            return
        sound = self.cue_sounds.get(cue_name) or self.cue_sounds.get("slide")
        if sound:
            sound.play()

    def announce(self, text: str, cue_name: str = "slide"):
        """Compatibility wrapper: use a short cue only, no voice synthesis."""
        self.play_cue(cue_name)

    def play_file(self, path: str, volume: float = 0.85):
        """Play a one-shot audio file such as the terminal boot sound."""
        if not self.initialized or not path or not os.path.exists(path):
            return
        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(max(0.0, min(1.0, volume)))
            sound.play()
        except Exception as e:
            print(f"[Audio] Failed to play {path}: {e}")

    def stop(self):
        """停止播放"""
        if self.initialized:
            pygame.mixer.music.stop()
            if self.bgm_channel:
                self.bgm_channel.stop()
                self.bgm_channel = None
            self.is_playing = False

    def cleanup(self):
        """清理 pygame 資源"""
        if self.initialized:
            pygame.mixer.quit()
        if self.generated_bgm_path and os.path.exists(self.generated_bgm_path):
            try:
                os.remove(self.generated_bgm_path)
            except OSError:
                pass

    def _prepare_cues(self):
        cues = {
            "slide": [(620, 0.045), (880, 0.055), (740, 0.07)],
            "refresh": [(420, 0.055), (560, 0.055), (760, 0.09)],
            "alert": [(260, 0.08), (260, 0.08), (520, 0.12)],
            "enable": [(900, 0.05), (1180, 0.08)],
        }
        for name, tones in cues.items():
            path = self._make_tone_file(name, tones)
            snd = pygame.mixer.Sound(path)
            snd.set_volume(Config.CUE_VOLUME)
            self.cue_sounds[name] = snd

    def _make_tone_file(self, name: str, tones: list) -> str:
        path = os.path.join(tempfile.gettempdir(), f"retrocast_{name}.wav")
        samples = []
        sample_rate = 44100
        for freq, duration in tones:
            count = int(sample_rate * duration)
            for i in range(count):
                env = min(1.0, i / 240) * min(1.0, (count - i) / 900)
                wave_a = math.sin(2 * math.pi * freq * i / sample_rate)
                wave_b = 0.45 * math.sin(2 * math.pi * (freq * 1.99) * i / sample_rate)
                samples.append(int(13000 * env * (wave_a + wave_b) / 1.45))
            samples.extend([0] * int(sample_rate * 0.025))
        self._write_wav(path, samples, sample_rate)
        return path

    def _make_synth_loop(self) -> str:
        """生成一段低調循環的復古未來合成器背景音。"""
        path = os.path.join(tempfile.gettempdir(), "retrocast_synth_loop.wav")
        sample_rate = 44100
        seconds = 12
        notes = [55.0, 65.41, 73.42, 98.0, 82.41, 73.42, 65.41, 49.0]
        lead = [220.0, 246.94, 293.66, 329.63, 293.66, 246.94]
        samples = []
        for i in range(sample_rate * seconds):
            t = i / sample_rate
            beat = int(t * 2) % len(notes)
            bass = math.sin(2 * math.pi * notes[beat] * t)
            pad = math.sin(2 * math.pi * notes[(beat + 2) % len(notes)] * 0.5 * t)
            pulse = 1.0 if (int(t * 8) % 2 == 0) else 0.62
            lead_freq = lead[int(t / 1.5) % len(lead)]
            lead_wave = math.sin(2 * math.pi * lead_freq * t) if int(t * 4) % 8 in (1, 2) else 0
            hiss = (random.random() - 0.5) * 0.025
            value = (0.34 * bass + 0.18 * pad + 0.10 * lead_wave) * pulse + hiss
            samples.append(int(max(-1, min(1, value)) * 10000))
        self._write_wav(path, samples, sample_rate)
        return path

    @staticmethod
    def _write_wav(path: str, samples: list, sample_rate: int):
        with wave.open(path, "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"".join(struct.pack("<h", s) for s in samples))


# ════════════════════════════════════════════════════════════════
#  視圖層 — 各個看板畫面的繪製邏輯
# ════════════════════════════════════════════════════════════════
class SlideRenderer:
    """
    看板渲染器基底類別
    所有看板繼承此類，實作 render(canvas, data) 方法
    """
    def __init__(self, canvas: tk.Canvas, config: Config):
        self.canvas = canvas
        self.config = config
        self.W = Config.WIN_WIDTH
        self.H = Config.WIN_HEIGHT - Config.MARQUEE_HEIGHT - Config.CONTROL_HEIGHT

    def clear(self):
        """清除畫布"""
        self.canvas.delete("slide_content")
        self.draw_backdrop()

    def draw_backdrop(self):
        """Draw a simple rounded black CRT frame around the weather screen."""
        self.draw_rect(0, 0, self.W, self.H, fill="#030405", outline="", tag="slide_content")
        bezel = Config.BEZEL_SIZE
        # Freepik-style old TV frame impression: just a thick rounded black screen rim.
        self.canvas.create_oval(
            -88, -66, self.W + 88, self.H + 66,
            fill="#020202", outline="#171717", width=10,
            tags="slide_content"
        )
        self.canvas.create_oval(
            -58, -38, self.W + 58, self.H + 38,
            fill="#080A0B", outline="#262626", width=6,
            tags="slide_content"
        )
        self.canvas.create_rectangle(
            bezel, bezel, self.W - bezel, self.H - bezel,
            fill=Config.BG_DARK, outline="#050505", width=2,
            tags="slide_content"
        )
        # Subtle inner shadow and curved-screen highlight.
        self.canvas.create_arc(
            bezel + 4, bezel + 4, self.W - bezel - 4, self.H - bezel - 4,
            start=28, extent=124, outline="#183138", width=1,
            style="arc", tags="slide_content"
        )
        self.canvas.create_arc(
            bezel + 4, bezel + 4, self.W - bezel - 4, self.H - bezel - 4,
            start=208, extent=124, outline="#010203", width=2,
            style="arc", tags="slide_content"
        )
        for x in range(bezel, self.W - bezel + 1, 56):
            self.canvas.create_line(x, bezel, x, self.H - bezel, fill="#0B1B20", width=1, tags="slide_content")
        for y in range(bezel, self.H - bezel + 1, 44):
            self.canvas.create_line(bezel, y, self.W - bezel, y, fill="#0C1A24", width=1, tags="slide_content")
        for y in range(bezel + 6, self.H - bezel, Config.SCANLINE_STEP):
            self.canvas.create_line(bezel + 6, y, self.W - bezel - 6, y, fill="#091119", width=1, tags="slide_content")
        # Corporate terminal corner brackets.
        bracket = 34
        inset = bezel + 9
        for sx, sy, hx, vy in (
            (inset, inset, 1, 1),
            (self.W - inset, inset, -1, 1),
            (inset, self.H - inset, 1, -1),
            (self.W - inset, self.H - inset, -1, -1),
        ):
            self.canvas.create_line(sx, sy, sx + hx * bracket, sy, fill=Config.TEXT_ORANGE, width=2, tags="slide_content")
            self.canvas.create_line(sx, sy, sx, sy + vy * bracket, fill=Config.TEXT_ORANGE, width=2, tags="slide_content")
        self.canvas.create_text(
            self.W // 2, self.H - bezel - 4,
            text="HALCYON HOLDINGS WEATHER TERMINAL // PROPERTY CONTROLLED",
            fill="#6E7D5F", font=(Config.FONT_FAMILY, 7, "bold"),
            tags="slide_content"
        )

    def draw_text(self, x, y, text, color=None, size=12, bold=False,
                  anchor="center", tag="slide_content", font_family=None):
        """統一的文字繪製方法"""
        weight = "bold" if bold else "normal"
        font_family = font_family or Config.FONT_FAMILY
        f = (font_family, size, weight)
        self.canvas.create_text(
            x, y, text=text, fill=color or Config.TEXT_WHITE,
            font=f, anchor=anchor,
            justify="center" if anchor == "center" else "left",
            tags=(tag, "slide_content")
        )

    def apply_display_scale(self, tag: str = "slide_content"):
        """Scale Canvas items created in base 800x600 coordinates."""
        scale = self._current_display_scale()
        if abs(scale - 1.0) < 0.01:
            return
        for item in self.canvas.find_withtag(tag):
            tags = self.canvas.gettags(item)
            if "display_scaled" in tags:
                continue
            self.canvas.scale(item, 0, 0, scale, scale)
            self._scale_item_style(item, scale)
            self.canvas.addtag_withtag("display_scaled", item)

    def _current_display_scale(self) -> float:
        """Return the configured canvas scale, avoiding transient geometry jitter."""
        try:
            configured_w = float(self.canvas.cget("width"))
            configured_h = float(self.canvas.cget("height"))
        except (tk.TclError, ValueError):
            return 1.0
        if configured_w <= 0 or configured_h <= 0:
            return 1.0
        return max(1.0, min(configured_w / Config.WIN_WIDTH, configured_h / self.H))

    def _scale_item_style(self, item, scale: float):
        item_type = self.canvas.type(item)
        if item_type == "text":
            try:
                font_spec = self.canvas.itemcget(item, "font")
                font_obj = tkfont.Font(root=self.canvas.winfo_toplevel(), font=font_spec)
                family = font_obj.actual("family")
                size = abs(int(font_obj.actual("size") or 10))
                weight = font_obj.actual("weight")
                slant = font_obj.actual("slant")
                self.canvas.itemconfig(item, font=(family, max(6, int(round(size * scale))), weight, slant))
            except Exception:
                pass
        try:
            width = self.canvas.itemcget(item, "width")
            if width not in ("", None):
                self.canvas.itemconfig(item, width=max(1, float(width) * scale))
        except Exception:
            pass

    def draw_rect(self, x1, y1, x2, y2, fill="", outline="", width=1,
                  tag="slide_content"):
        """統一的矩形繪製方法"""
        return self.canvas.create_rectangle(
            x1, y1, x2, y2, fill=fill, outline=outline,
            width=width, tags=(tag, "slide_content")
        )

    def draw_header(self, title: str, subtitle: str = ""):
        """繪製復古風格標題列"""
        # 標題背景條
        self.draw_rect(24, 24, self.W - 24, 62, fill=Config.BG_PANEL,
                       outline=Config.BORDER_COL, width=2)
        # 左側彩色裝飾條
        self.canvas.create_rectangle(
            24, 24, 34, 62, fill=Config.TEXT_CYAN, outline="",
            tags="slide_content"
        )
        self.canvas.create_rectangle(
            34, 24, 44, 62, fill=Config.TEXT_ORANGE, outline="",
            tags="slide_content"
        )
        self.canvas.create_rectangle(
            44, 24, 54, 62, fill=Config.TEXT_RED, outline="",
            tags="slide_content"
        )

        # 標題文字
        self.draw_text(self.W//2, 37, title,
                       color=Config.TEXT_YELLOW, size=16, bold=True)
        if subtitle:
            self.draw_text(self.W//2, 55, subtitle,
                           color=Config.TEXT_CYAN, size=10)

        self.draw_text(64, 36, "HALCYON", color=Config.TEXT_WHITE, size=10, bold=True, anchor="w")
        self.draw_text(64, 54, "ARCADIA TERMINAL", color=Config.TEXT_ORANGE, size=8, anchor="w")


class CurrentWeatherSlide(SlideRenderer):
    """
    看板一：目前天氣
    顯示當前溫度、天氣狀況、風速、濕度等完整資訊
    """
    def render(self, data: dict):
        self.clear()
        if not data:
            self.draw_text(self.W//2, self.H//2,
                           "LOADING DATA...", color=Config.TEXT_YELLOW, size=18)
            return

        # ── 標題列 ────────────────────────────────────────────
        city_name = f"{data.get('city','').upper()}, {data.get('country','')}"
        self.draw_header("CURRENT CONDITIONS", city_name)

        # ── 復古終端機天氣符號（左上區域）────────────────────
        self.draw_rect(34, 76, 190, 178, fill="#061015", outline=Config.TEXT_CYAN, width=1)
        self._draw_terminal_weather_glyph(data.get("weather_id", 3))
        self.draw_text(112, 166, "ATMOSPHERIC GLYPH", color="#93A8A2", size=7, bold=True)

        # ── 主溫度顯示（中央大字）────────────────────────────
        temp = data.get("temp", "--")
        self.draw_text(self.W//2 + 30, 95,
                       f"{temp}{Config.TEMP_UNIT}",
                       color=Config.TEXT_YELLOW, size=52, bold=True)

        feels = data.get("feels_like", "--")
        self.draw_text(self.W//2 + 30, 152,
                       f"FEELS LIKE  {feels}{Config.TEMP_UNIT}",
                       color=Config.TEXT_CYAN, size=13)

        # ── 天氣描述 ──────────────────────────────────────────
        desc  = data.get("description", "")
        icon  = data.get("icon", "")
        self.draw_text(self.W//2, 180,
                       desc,
                       color=Config.TEXT_WHITE, size=14, bold=True)
        self.draw_text(self.W//2 - 156, 180, icon,
                       color=Config.TEXT_WHITE, size=18, bold=True,
                       font_family=Config.ICON_FONT_FAMILY)
        self.draw_text(self.W//2 + 156, 180, icon,
                       color=Config.TEXT_WHITE, size=18, bold=True,
                       font_family=Config.ICON_FONT_FAMILY)

        alert = data.get("alert", {})
        alert_level = alert.get("level", "CLEAR")
        alert_color = alert.get("color", Config.TEXT_GREEN)
        self.draw_rect(self.W - 250, 76, self.W - 38, 136,
                       fill="#17110C", outline=alert_color, width=2)
        self.draw_text(self.W - 144, 94, "CORPORATE ALERT",
                       color=Config.TEXT_ORANGE, size=9, bold=True)
        self.draw_text(self.W - 144, 116, alert_level,
                       color=alert_color, size=16, bold=True)

        # ── 分隔線 ────────────────────────────────────────────
        self.canvas.create_line(
            20, 200, self.W - 20, 200,
            fill=Config.BORDER_COL, width=2, tags="slide_content"
        )

        # ── 資訊格線（下半部 2x3 排列）────────────────────────
        metrics = [
            ("HUMIDITY",    f"{data.get('humidity','--')} %"),
            ("WIND SPEED",  f"{data.get('wind_speed','--')} km/h"),
            ("WIND DIR",    WeatherData().wind_direction(data.get("wind_deg",0))),
            ("VISIBILITY",  f"{data.get('visibility','--')} km"),
            ("PRESSURE",    f"{data.get('pressure','--')} hPa"),
            ("CLOUD COVER", f"{data.get('clouds','--')} %"),
        ]

        cols = 3
        cell_w = (self.W - 40) // cols
        for idx, (label, value) in enumerate(metrics):
            col = idx % cols
            row = idx // cols
            cx  = 20 + cell_w * col + cell_w // 2
            cy  = 230 + row * 80

            # 格子背景
            self.draw_rect(
                20 + cell_w * col + 5, cy - 30,
                20 + cell_w * (col+1) - 5, cy + 30,
                fill=Config.BG_PANEL, outline=Config.BORDER_COL, width=1
            )
            self.draw_text(cx, cy - 12, label,
                           color=Config.TEXT_CYAN, size=11)
            self.draw_text(cx, cy + 12, value,
                           color=Config.TEXT_YELLOW, size=15, bold=True)

        # ── 日出日落資訊 ──────────────────────────────────────
        y_bottom = self.H - 30
        self.draw_text(self.W//4, y_bottom,
                       f"SUNRISE  {data.get('sunrise','--')}",
                       color=Config.TEXT_ORANGE, size=12)
        self.draw_text(3*self.W//4, y_bottom,
                       f"SUNSET  {data.get('sunset','--')}",
                       color=Config.TEXT_ORANGE, size=12)

    def _draw_terminal_weather_glyph(self, weather_id: int):
        """Draw a stable Canvas weather glyph instead of fragile ASCII art."""
        cx, cy = 112, 119
        tags = ("slide_content",)
        glow = "#123A36"
        cyan = "#76D7C4"
        amber = Config.TEXT_YELLOW
        rain = Config.TEXT_CYAN
        snow = Config.TEXT_WHITE

        def line(x1, y1, x2, y2, color=cyan, width=2):
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags=tags)

        def oval(x1, y1, x2, y2, outline=cyan, width=2, fill=""):
            self.canvas.create_oval(x1, y1, x2, y2, outline=outline, width=width, fill=fill, tags=tags)

        def rect(x1, y1, x2, y2, outline=cyan, width=2, fill=""):
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline, width=width, fill=fill, tags=tags)

        def cloud():
            oval(cx - 48, cy - 3, cx - 18, cy + 27, outline=glow, width=5)
            oval(cx - 30, cy - 18, cx + 10, cy + 27, outline=glow, width=5)
            oval(cx - 2, cy - 8, cx + 40, cy + 28, outline=glow, width=5)
            line(cx - 46, cy + 24, cx + 42, cy + 24, glow, 5)
            oval(cx - 48, cy - 3, cx - 18, cy + 27)
            oval(cx - 30, cy - 18, cx + 10, cy + 27)
            oval(cx - 2, cy - 8, cx + 40, cy + 28)
            line(cx - 46, cy + 24, cx + 42, cy + 24)

        if weather_id == 0:
            oval(cx - 24, cy - 24, cx + 24, cy + 24, outline=amber, width=3)
            for angle in range(0, 360, 45):
                r1, r2 = 34, 46
                x1 = cx + math.cos(math.radians(angle)) * r1
                y1 = cy + math.sin(math.radians(angle)) * r1
                x2 = cx + math.cos(math.radians(angle)) * r2
                y2 = cy + math.sin(math.radians(angle)) * r2
                line(x1, y1, x2, y2, amber, 2)
            self.draw_text(cx, cy, "SOL", color=amber, size=10, bold=True)
        elif weather_id in (1, 2):
            oval(cx - 46, cy - 38, cx - 6, cy + 2, outline=amber, width=2)
            cloud()
        else:
            cloud()

        if weather_id in (45, 48):
            for offset in (34, 44, 54):
                line(cx - 46, cy + offset - 12, cx + 46, cy + offset - 12, rain, 2)
        elif weather_id in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            for x in (cx - 32, cx - 12, cx + 8, cx + 28):
                line(x, cy + 36, x - 8, cy + 52, rain, 2)
        elif weather_id in (71, 73, 75, 77, 85, 86):
            for x in (cx - 30, cx - 8, cx + 14, cx + 34):
                line(x - 5, cy + 42, x + 5, cy + 42, snow, 2)
                line(x, cy + 37, x, cy + 47, snow, 2)
        elif weather_id in (95, 96, 99):
            points = [cx - 5, cy + 32, cx - 20, cy + 58, cx + 0, cy + 52, cx - 10, cy + 74, cx + 22, cy + 42, cx + 4, cy + 48]
            self.canvas.create_line(*points, fill=Config.TEXT_RED, width=3, tags=tags)

        rect(54, 88, 170, 150, outline="#24414A", width=1)


class ForecastSlide(SlideRenderer):
    """
    看板二：三日天氣預報
    以直式卡片形式並排顯示 3 天預報
    """
    def render(self, forecast: list):
        self.clear()

        self.draw_header("THREE DAY FORECAST",
                         f"{Config.CITY.upper()} EXTENDED FORECAST")

        if not forecast:
            self.draw_text(self.W//2, self.H//2,
                           "FORECAST DATA LOADING...",
                           color=Config.TEXT_YELLOW, size=18)
            return

        # ── 三欄預報卡片 ──────────────────────────────────────
        card_w = (self.W - 60) // 3
        card_h = self.H - 120
        pad    = 15

        for idx, day in enumerate(forecast[:3]):
            x1 = 20 + idx * (card_w + 10)
            y1 = 70
            x2 = x1 + card_w
            y2 = y1 + card_h

            # 卡片背景（深藍底）
            self.draw_rect(x1, y1, x2, y2,
                           fill=Config.BG_PANEL, outline=Config.BORDER_COL, width=2)

            # 星期標題條
            self.draw_rect(x1, y1, x2, y1 + 40,
                           fill=Config.BG_MEDIUM, outline=Config.BORDER_COL, width=1)
            cx = (x1 + x2) // 2

            self.draw_text(cx, y1 + 14,
                           day.get("weekday", ""),
                           color=Config.TEXT_YELLOW, size=16, bold=True)
            self.draw_text(cx, y1 + 30,
                           day.get("date", ""),
                           color=Config.TEXT_CYAN, size=10)

            # 天氣圖示（大字）
            self.draw_text(cx, y1 + 80,
                           day.get("icon", "☁️"),
                           color=Config.TEXT_WHITE, size=28, bold=True,
                           font_family=Config.ICON_FONT_FAMILY)

            # 天氣描述
            self.draw_text(cx, y1 + 130,
                           day.get("description", ""),
                           color=Config.TEXT_WHITE, size=11)

            # 最高/最低溫度
            self.draw_text(cx, y1 + 165,
                           f"HIGH  {day.get('temp_max','--')}{Config.TEMP_UNIT}",
                           color=Config.TEXT_RED, size=15, bold=True)
            self.draw_text(cx, y1 + 192,
                           f"LOW   {day.get('temp_min','--')}{Config.TEMP_UNIT}",
                           color="#88AAFF", size=15, bold=True)

            # 降雨機率 bar
            pop     = day.get("pop", 0)
            bar_x1  = x1 + pad
            bar_x2  = x2 - pad
            bar_y   = y1 + 230
            bar_w   = bar_x2 - bar_x1

            self.draw_text(cx, bar_y - 15,
                           f"PRECIP CHANCE  {pop}%",
                           color=Config.TEXT_CYAN, size=10)

            # 底色
            self.draw_rect(bar_x1, bar_y, bar_x2, bar_y + 14,
                           fill=Config.BG_DARK, outline=Config.BORDER_COL, width=1)
            # 進度條
            fill_w = int(bar_w * pop / 100)
            bar_color = (Config.TEXT_RED    if pop >= 70
                         else Config.TEXT_YELLOW if pop >= 40
                         else Config.TEXT_GREEN)
            if fill_w > 0:
                self.draw_rect(bar_x1, bar_y, bar_x1 + fill_w, bar_y + 14,
                               fill=bar_color, outline="")

            # 濕度
            self.draw_text(cx, y1 + 265,
                           f"HUMIDITY  {day.get('humidity','--')}%",
                           color=Config.TEXT_CYAN, size=11)


class HourlyTimelineSlide(SlideRenderer):
    """12-hour operations timeline with temperature, rain chance, and wind."""
    def render(self, hourly: list, current: dict = None):
        self.clear()
        self.draw_header("12-HOUR OPERATIONS TIMELINE", f"{Config.CITY.upper()} SHORT-RANGE FORECAST")
        if not hourly:
            self.draw_text(self.W//2, self.H//2,
                           "HOURLY TELEMETRY LOADING...",
                           color=Config.TEXT_YELLOW, size=18, bold=True)
            return

        alert = (current or {}).get("alert", {})
        alert_color = alert.get("color", Config.TEXT_GREEN)
        alert_level = alert.get("level", "CLEAR")
        alert_msg = alert.get("message", "Atmospheric conditions are within profitable tolerance.")
        self.draw_rect(34, 78, self.W - 34, 124, fill="#15100C", outline=alert_color, width=2)
        self.draw_text(54, 100, f"RISK TIER: {alert_level}", color=alert_color, size=14, bold=True, anchor="w")
        self.draw_text(248, 100, alert_msg[:68], color=Config.TEXT_WHITE, size=10, anchor="w")

        chart_x1, chart_y1 = 42, 154
        chart_x2, chart_y2 = self.W - 42, 374
        slot_w = (chart_x2 - chart_x1) / 12
        temps = [h.get("temp", 0) for h in hourly[:12]]
        min_t, max_t = min(temps), max(temps)
        temp_span = max(1, max_t - min_t)

        self.draw_rect(chart_x1 - 8, chart_y1 - 22, chart_x2 + 8, chart_y2 + 48,
                       fill="#0B100D", outline=Config.BORDER_COL, width=2)
        for i in range(13):
            x = chart_x1 + i * slot_w
            self.canvas.create_line(x, chart_y1 - 16, x, chart_y2,
                                    fill="#1E332C", width=1, tags="slide_content")
        for j in range(4):
            y = chart_y1 + j * (chart_y2 - chart_y1) / 3
            self.canvas.create_line(chart_x1, y, chart_x2, y,
                                    fill="#263421", width=1, tags="slide_content")

        points = []
        temp_labels = []
        for idx, hour in enumerate(hourly[:12]):
            x = chart_x1 + idx * slot_w + slot_w / 2
            temp = hour.get("temp", 0)
            y = chart_y2 - ((temp - min_t) / temp_span) * (chart_y2 - chart_y1 - 34) - 14
            points.extend([x, y])

            pop = hour.get("pop", 0)
            bar_h = int((chart_y2 - chart_y1) * 0.72 * pop / 100)
            bar_col = Config.TEXT_RED if pop >= 70 else Config.TEXT_YELLOW if pop >= 40 else Config.TEXT_GREEN
            self.draw_rect(x - slot_w * 0.22, chart_y2 - bar_h, x + slot_w * 0.22, chart_y2,
                           fill=bar_col, outline="")
            label_y = chart_y2 + (14 if idx % 2 == 0 else 31)
            self.draw_text(x, label_y, hour.get("time", "--"),
                           color=Config.TEXT_CYAN, size=8, bold=True)
            self.draw_text(x, chart_y1 - 8, hour.get("icon", ""),
                           color=Config.TEXT_WHITE, size=13, bold=True,
                           font_family=Config.ICON_FONT_FAMILY)
            label_y = max(chart_y1 + 14, y - 22)
            temp_labels.append((x, label_y, f"{temp}{Config.TEMP_UNIT}"))

        if len(points) >= 4:
            self.canvas.create_line(*points, fill=Config.TEXT_ORANGE, width=2,
                                    smooth=True, tags="slide_content")
            for px, py in zip(points[0::2], points[1::2]):
                self.canvas.create_oval(px - 3, py - 3, px + 3, py + 3,
                                        fill=Config.TEXT_YELLOW, outline=Config.BG_DARK,
                                        tags="slide_content")
        for x, label_y, label in temp_labels:
            self.draw_rect(x - 19, label_y - 8, x + 19, label_y + 8,
                           fill="#0B100D", outline="")
            self.draw_text(x, label_y, label,
                           color=Config.TEXT_YELLOW, size=8, bold=True)

        info_y = self.H - 96
        self.draw_rect(38, info_y - 14, self.W - 38, self.H - 46,
                       fill="#0D130F", outline="#263421", width=1)
        self.draw_text(54, info_y, "AMBER LINE: TEMPERATURE", color=Config.TEXT_ORANGE, size=9, bold=True, anchor="w")
        self.draw_text(270, info_y, "BARS: PRECIPITATION PROBABILITY", color=Config.TEXT_CYAN, size=9, bold=True, anchor="w")
        self.draw_text(54, info_y + 24,
                       "Wind: " + "  ".join(f"{h.get('time')} {h.get('wind')}km/h" for h in hourly[:4]),
                       color="#93A8A2", size=8, anchor="w")
        self.draw_text(420, info_y + 24,
                       "Humidity: " + "  ".join(f"{h.get('time')} {h.get('humidity','--')}%" for h in hourly[:3]),
                       color="#93A8A2", size=8, anchor="w")


class LocalObservationsSlide(SlideRenderer):
    """
    看板：區域觀測表
    參考 weather.com/retro 的城市、溫度、天氣與風向資料表。
    """
    def render(self, current: dict):
        self.clear()
        self.draw_header("LOCAL OBSERVATIONS", f"{Config.CITY.upper()} REGIONAL WEATHER ROUNDUP")
        observations = current.get("observations", []) if current else []
        if not observations:
            self.draw_text(self.W//2, self.H//2,
                           "REGIONAL OBSERVATION FEED LOADING...",
                           color=Config.TEXT_YELLOW, size=16, bold=True)
            return

        x = 42
        y = 86
        cols = [x, x + 210, x + 330, x + 500, x + 640]
        headers = ["City", f"{Config.TEMP_UNIT} Temp", "Weather", "Wind", "Signal"]
        self.draw_rect(30, 70, self.W - 30, 112, fill=Config.BG_WARM, outline=Config.BORDER_COL, width=2)
        for i, header in enumerate(headers):
            self.draw_text(cols[i], y, header, color=Config.TEXT_YELLOW, size=12, bold=True, anchor="w")

        for idx, station in enumerate(observations[:8]):
            row_y = 126 + idx * 42
            fill = "#111F2D" if idx % 2 == 0 else "#0C1720"
            if idx == 0:
                fill = "#182820"
            city = station.get("city", Config.CITY)
            temp = station.get("temp", "--")
            weather = station.get("weather", "--")
            wind = station.get("wind", "--")
            speed = station.get("speed", "--")
            signal = station.get("signal", "CLEAR")
            self.draw_rect(30, row_y - 17, self.W - 30, row_y + 17, fill=fill, outline="#253C42", width=1)
            self.draw_text(cols[0], row_y, city, color=Config.TEXT_WHITE, size=13, bold=True, anchor="w")
            self.draw_text(cols[1], row_y, f"{temp:>4}{Config.TEMP_UNIT}", color=Config.TEXT_YELLOW, size=13, bold=True, anchor="w")
            self.draw_text(cols[2], row_y, weather[:16], color=Config.TEXT_CYAN, size=12, anchor="w")
            self.draw_text(cols[3], row_y, f"{wind} {speed:>2} km/h", color=Config.TEXT_WHITE, size=12, anchor="w")
            sig_col = Config.TEXT_GREEN if signal in ("LOCKED", "LIVE") else Config.TEXT_ORANGE
            self.draw_text(cols[4], row_y, signal, color=sig_col, size=12, bold=True, anchor="w")

        self.draw_rect(30, self.H - 86, self.W - 30, self.H - 46, fill=Config.BG_PANEL, outline=Config.BORDER_COL, width=1)
        self.draw_text(
            self.W // 2, self.H - 66,
            "REAL NEARBY POINT WEATHER: OPEN-METEO + OSM NOMINATIM PLACE NAMES",
            color="#93A8A2", size=10, bold=True
        )


class CityComparisonSlide(SlideRenderer):
    """Global colony/city comparison board using real Open-Meteo readings."""
    def render(self, comparison: list):
        self.clear()
        self.draw_header("COLONY COMPARISON BOARD", "REAL-TIME GLOBAL OPERATIONS SNAPSHOT")
        if not comparison:
            self.draw_text(self.W//2, self.H//2, "COMPARISON TELEMETRY LOADING...",
                           color=Config.TEXT_YELLOW, size=17, bold=True)
            return

        x = 42
        y = 92
        cols = [x, x + 190, x + 300, x + 465, x + 585, x + 680]
        headers = ["Station", "Temp", "Weather", "Wind", "Risk", "Link"]
        self.draw_rect(30, 72, self.W - 30, 114, fill=Config.BG_WARM, outline=Config.BORDER_COL, width=2)
        for i, header in enumerate(headers):
            self.draw_text(cols[i], y, header, color=Config.TEXT_YELLOW, size=11, bold=True, anchor="w")

        for idx, row in enumerate(comparison[:7]):
            row_y = 132 + idx * 48
            fill = "#11160F" if idx % 2 == 0 else "#0B100D"
            if idx == 0:
                fill = "#1D2618"
            self.draw_rect(30, row_y - 19, self.W - 30, row_y + 19,
                           fill=fill, outline="#29331F", width=1)
            name = f"{row.get('city','--')}, {row.get('country','')}"[:22]
            self.draw_text(cols[0], row_y, name, color=Config.TEXT_WHITE, size=12, bold=True, anchor="w")
            self.draw_text(cols[1], row_y, f"{row.get('temp','--')}{Config.TEMP_UNIT}",
                           color=Config.TEXT_YELLOW, size=13, bold=True, anchor="w")
            self.draw_text(cols[2], row_y, str(row.get("weather", "--"))[:18],
                           color=Config.TEXT_CYAN, size=11, anchor="w")
            self.draw_text(cols[3], row_y, f"{row.get('wind','--')} km/h",
                           color=Config.TEXT_WHITE, size=11, anchor="w")
            risk = row.get("risk", "CLEAR")
            self.draw_text(cols[4], row_y, risk,
                           color=row.get("risk_color", Config.TEXT_GREEN), size=11, bold=True, anchor="w")
            link = "PRIMARY" if idx == 0 else "REMOTE"
            self.draw_text(cols[5], row_y, link, color=Config.TEXT_ORANGE, size=10, bold=True, anchor="w")

        self.draw_rect(30, self.H - 74, self.W - 30, self.H - 42,
                       fill=Config.BG_PANEL, outline=Config.BORDER_COL, width=1)
        self.draw_text(self.W//2, self.H - 58,
                       "REMOTE STATIONS USE OPEN-METEO CURRENT WEATHER; RISK MATRIX IS LOCAL TO ARCADIA 5000.",
                       color="#93A8A2", size=9, bold=True)


class AIWeatherSummarySlide(SlideRenderer):
    """Generated text weather summary using live city weather data."""
    def __init__(self, canvas: tk.Canvas, config: Config):
        super().__init__(canvas, config)
        self.scroll_offset = 0
        self.max_scroll = 0
        self.current_data = {}

    def render(self, current: dict):
        self.clear()
        current = current or {}
        self.current_data = dict(current)
        self.draw_header("CORPORATE WEATHER BRIEF", f"{Config.CITY.upper()} AUTHORIZED TERMINAL SUMMARY")

        summary = current.get("ai_summary") or {}
        text = summary.get("text", "WEATHER BRIEFING LOADING...")
        source = summary.get("source", "PENDING")
        ai_ok = summary.get("ai_ok", source.startswith("OLLAMA"))
        error = summary.get("error", "")
        alert = current.get("alert", {})
        source_color = Config.TEXT_CYAN if ai_ok else Config.TEXT_RED

        self.draw_rect(34, 78, self.W - 34, 136, fill=Config.BG_PANEL, outline=Config.BORDER_COL, width=2)
        self.draw_text(58, 100, "TERMINAL BRIEFING", color=Config.TEXT_YELLOW, size=13, bold=True, anchor="w")
        self.draw_text(self.W - 58, 100, source, color=source_color, size=10, bold=True, anchor="e")
        detail = (
            f"{current.get('description','--')}  |  "
            f"{current.get('temp','--')}{Config.TEMP_UNIT}  |  "
            f"ALERT {alert.get('level','CLEAR')}"
        )
        self.draw_text(58, 122,
                       detail[:76],
                       color=Config.TEXT_WHITE, size=10, anchor="w")

        panel_top = 164
        if not ai_ok:
            self.draw_rect(44, 148, self.W - 44, 190, fill="#2A1010", outline=Config.TEXT_RED, width=2)
            self.draw_text(66, 164, "OLLAMA SUMMARY OFFLINE", color=Config.TEXT_RED, size=12, bold=True, anchor="w")
            self.draw_text(66, 180,
                           f"USING LOCAL FALLBACK. CHECK OLLAMA SERVER/MODEL. {error}"[:96],
                           color=Config.TEXT_YELLOW, size=8, bold=True, anchor="w")
            panel_top = 206

        panel_bottom = self.H - 92
        self.draw_rect(44, panel_top, self.W - 44, panel_bottom, fill="#0B141B", outline=Config.BORDER_COL, width=2)
        lines = self._wrap_lines(text, max_chars=74)
        visible_count = max(3, int((panel_bottom - panel_top - 48) // 28))
        self.max_scroll = max(0, len(lines) - visible_count)
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
        visible_lines = lines[self.scroll_offset:self.scroll_offset + visible_count]
        y = panel_top + 38
        for idx, line in enumerate(visible_lines):
            actual_idx = self.scroll_offset + idx
            color = Config.TEXT_YELLOW if actual_idx == 0 else Config.TEXT_WHITE
            self.draw_text(72, y, line, color=color, size=11,
                           bold=(actual_idx == 0), anchor="w")
            y += 28
        if self.max_scroll > 0:
            self._draw_scrollbar(panel_top, panel_bottom, visible_count, len(lines))

        self.draw_rect(62, self.H - 72, self.W - 62, self.H - 44, fill=Config.BG_WARM,
                       outline=Config.BORDER_COL, width=1)
        self.draw_text(self.W // 2, self.H - 58,
                       "SCROLL BRIEFING WITH MOUSE WHEEL / TRACKPAD. LIVE NUMBERS REMAIN COMPANY PROPERTY.",
                       color=Config.TEXT_YELLOW, size=8, bold=True)

    def bind_scroll(self):
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", lambda _e: self._scroll(-1))
        self.canvas.bind("<Button-5>", lambda _e: self._scroll(1))

    def _on_mousewheel(self, event):
        delta = -1 if event.delta > 0 else 1
        self._scroll(delta)

    def _scroll(self, delta: int):
        if self.max_scroll <= 0:
            return
        new_offset = max(0, min(self.max_scroll, self.scroll_offset + delta))
        if new_offset != self.scroll_offset:
            self.scroll_offset = new_offset
            self.render(self.current_data)

    def _draw_scrollbar(self, panel_top: int, panel_bottom: int, visible_count: int, total_lines: int):
        track_x = self.W - 68
        track_top = panel_top + 20
        track_bottom = panel_bottom - 20
        track_h = max(1, track_bottom - track_top)
        thumb_h = max(24, int(track_h * visible_count / max(visible_count, total_lines)))
        travel = max(1, track_h - thumb_h)
        thumb_y = track_top + int(travel * self.scroll_offset / max(1, self.max_scroll))
        self.draw_rect(track_x, track_top, track_x + 8, track_bottom, fill="#061015", outline="#24414A", width=1)
        self.draw_rect(track_x, thumb_y, track_x + 8, thumb_y + thumb_h,
                       fill=Config.TEXT_CYAN, outline="")
        self.draw_text(track_x + 4, track_top - 10, "▲", color=Config.TEXT_CYAN, size=7, bold=True)
        self.draw_text(track_x + 4, track_bottom + 10, "▼", color=Config.TEXT_CYAN, size=7, bold=True)

    @staticmethod
    def _wrap_lines(text: str, max_chars: int = 72) -> list:
        raw_lines = []
        for part in str(text).replace("\r", "").split("\n"):
            part = " ".join(part.split())
            if part:
                raw_lines.append(part)
        lines = []
        for raw in raw_lines:
            words = raw.split()
            current = ""
            for word in words:
                if len(current) + len(word) + 1 > max_chars:
                    lines.append(current)
                    current = word
                else:
                    current = f"{current} {word}".strip()
            if current:
                lines.append(current)
        return lines or ["WEATHER BRIEFING LOADING..."]


class CorporateAdSlide(SlideRenderer):
    """Retro-future corporate advertisement interstitial."""
    def __init__(self, canvas: tk.Canvas, config: Config):
        super().__init__(canvas, config)
        self.ad_index = 0
        self.ad_photo = None
        self.cache = {}

    def render(self):
        self.clear()
        self.draw_header("SPONSORED CORPORATE MESSAGE", "AUTHORIZED COLONY COMMERCE BREAK")

        ad_path = self._next_available_ad()
        photo = self._load_ad_photo(ad_path) if ad_path else None
        panel_x1, panel_y1 = 42, 86
        panel_x2, panel_y2 = self.W - 42, self.H - 92
        self.draw_rect(panel_x1, panel_y1, panel_x2, panel_y2,
                       fill="#0B0E0A", outline=Config.BORDER_COL, width=2)
        self.canvas.create_rectangle(panel_x1 + 8, panel_y1 + 8, panel_x2 - 8, panel_y2 - 8,
                                     outline="#3D2A18", width=1, tags="slide_content")

        if photo:
            self.ad_photo = photo
            self.canvas.create_image(self.W // 2, (panel_y1 + panel_y2) // 2,
                                     image=self.ad_photo, tags="slide_content")
        else:
            self.draw_text(self.W // 2, self.H // 2, "ADVERTISEMENT FEED UNAVAILABLE",
                           color=Config.TEXT_YELLOW, size=18, bold=True)

        # Keep the CRT effect outside the artwork so printed text stays readable.
        for x, y, sx, sy in (
            (panel_x1 + 18, panel_y1 + 18, 1, 1),
            (panel_x2 - 18, panel_y1 + 18, -1, 1),
            (panel_x1 + 18, panel_y2 - 18, 1, -1),
            (panel_x2 - 18, panel_y2 - 18, -1, -1),
        ):
            self.canvas.create_line(x, y, x + sx * 42, y, fill="#694A28", width=2, tags="slide_content")
            self.canvas.create_line(x, y, x, y + sy * 28, fill="#694A28", width=2, tags="slide_content")
        slogan = self._slogan_for(ad_path)
        self.draw_rect(70, self.H - 76, self.W - 70, self.H - 46,
                       fill=Config.BG_WARM, outline=Config.BORDER_COL, width=1)
        self.draw_text(self.W // 2, self.H - 61,
                       slogan,
                       color=Config.TEXT_YELLOW, size=9, bold=True)

    def _next_available_ad(self):
        supported = (".png", ".jpg", ".jpeg", ".webp", ".gif")
        paths = [
            p for p in Config.AD_IMAGE_PATHS
            if os.path.exists(p) and p.lower().endswith(supported)
        ]
        if not paths:
            return None
        path = paths[self.ad_index % len(paths)]
        self.ad_index += 1
        return path

    def _load_ad_photo(self, path: str):
        if not PIL_AVAILABLE or not path:
            return None
        if path in self.cache:
            return self.cache[path]
        try:
            image = Image.open(path)
            if getattr(image, "is_animated", False):
                image.seek(0)
            image = image.convert("RGBA")
            max_w, max_h = self.W - 112, self.H - 180
            image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
            x = (max_w - image.width) // 2
            y = (max_h - image.height) // 2
            canvas.alpha_composite(image, (x, y))
            photo = ImageTk.PhotoImage(canvas)
            self.cache[path] = photo
            if len(self.cache) > 8:
                self.cache.pop(next(iter(self.cache)))
            return photo
        except Exception as exc:
            print(f"[Ad] Could not load ad asset {path}: {exc}")
            return None

    def _slogan_for(self, path: str) -> str:
        if not path:
            return "THIS WEATHERCAST BROUGHT TO YOU BY CERTIFIED COLONY COMMERCE."
        name = os.path.basename(path)
        for key, slogan in Config.AD_SLOGANS.items():
            if key in name:
                return slogan
        return "THIS WEATHERCAST BROUGHT TO YOU BY CERTIFIED COLONY COMMERCE."


class CreditsSlide(SlideRenderer):
    """Project credits and data source explainer for demos."""
    def render(self):
        self.clear()
        self.draw_header("SYSTEM CREDITS", "AUTHORIZED DATA SOURCES AND TERMINAL MODULES")
        rows = [
            ("WEATHER DATA", "Open-Meteo forecast, hourly, daily, and geocoding APIs"),
            ("MAP DISPLAY", "OpenStreetMap tile layer centered on searched city coordinates"),
            ("RADAR OVERLAY", "RainViewer public weather maps when live radar is available"),
            ("LOCAL BRIEFING", "Ollama localhost model; fallback summary if offline"),
            ("INTERFACE", "Python Tkinter Canvas with pygame audio and Pillow image handling"),
            ("ASSETS", "Bundled audio, font, ad images, and logo files from project assets"),
        ]
        self.draw_rect(42, 84, self.W - 42, self.H - 86, fill="#0B141B", outline=Config.BORDER_COL, width=2)
        for idx, (label, value) in enumerate(rows):
            y = 126 + idx * 52
            fill = "#111F2D" if idx % 2 == 0 else "#0C1720"
            self.draw_rect(62, y - 20, self.W - 62, y + 20, fill=fill, outline="#253C42", width=1)
            self.draw_text(86, y, label, color=Config.TEXT_YELLOW, size=12, bold=True, anchor="w")
            self.draw_text(258, y, value[:62], color=Config.TEXT_WHITE, size=10, anchor="w")

        self.draw_rect(72, self.H - 70, self.W - 72, self.H - 42,
                       fill=Config.BG_WARM, outline=Config.BORDER_COL, width=1)
        self.draw_text(self.W // 2, self.H - 56,
                       "DEMO TIP: PRESS PAUSE ON ANY PAGE TO EXPLAIN THE MODULE CURRENTLY ON SCREEN.",
                       color=Config.TEXT_YELLOW, size=8, bold=True)


class RadarSlide(SlideRenderer):
    """
    看板三：降雨雷達圖（模擬動畫）
    使用數學函數生成擬真的雷達掃描動畫效果
    """
    def __init__(self, canvas: tk.Canvas, config: Config):
        super().__init__(canvas, config)
        self.frame      = 0       # 動畫幀數計數器
        self.anim_id    = None    # after() 的 ID，用於取消動畫
        self.is_active  = False
        self.data       = {}
        self.map_cache  = {}
        self.map_loading = set()
        self.map_photo  = None
        self.radar_cache = {}
        self.radar_photo = None
        self.radar_status = "RADAR STANDBY"

    def clear_location_cache(self):
        """Clear map/radar assets after a city lock so old maps cannot linger."""
        self.map_cache.clear()
        self.map_loading.clear()
        self.radar_cache.clear()
        self.map_photo = None
        self.radar_photo = None

    def render(self, data: dict = None):
        self.clear()
        self.is_active = True
        self.frame     = 0
        self.data      = data or {}
        lat = self.data.get("lat", Config.LATITUDE)
        lon = self.data.get("lon", Config.LONGITUDE)
        self.draw_header("LIVE MAP RADAR", f"{Config.CITY.upper()}  {lat:.2f}, {lon:.2f}")
        self._animate()

    def stop(self):
        """停止雷達動畫（切換看板時呼叫）"""
        self.is_active = False
        if self.anim_id:
            self.canvas.after_cancel(self.anim_id)
            self.anim_id = None

    def _animate(self):
        """雷達動畫主迴圈"""
        if not self.is_active:
            return
        self._draw_radar_frame()
        self.frame  += 1
        self.anim_id = self.canvas.after(80, self._animate)  # ~12 FPS

    def _draw_radar_frame(self):
        """繪製單一雷達幀"""
        self.canvas.delete("radar")

        display_scale = self._current_display_scale()
        sx = lambda value: int(round(value * display_scale))
        sw = lambda value: max(1, int(round(value * display_scale)))
        font = lambda size, weight="normal": (
            Config.FONT_FAMILY,
            max(6, int(round(size * display_scale))),
            weight,
        )

        cx = sx(self.W // 2)
        cy = sx((self.H - 60) // 2 + 60)
        R  = sx(min(self.W, self.H - 80) // 2 - 20)
        scaled_W = sx(self.W)
        scaled_H = sx(self.H)

        # ── 背景圓形雷達底盤 ──────────────────────────────────
        self.canvas.create_oval(
            cx - R, cy - R, cx + R, cy + R,
            fill="#06130F", outline=Config.TEXT_GREEN, width=sw(2),
            tags=("radar", "slide_content", "display_scaled")
        )

        self._draw_map_layer(cx, cy, R)
        rv_radar = self._get_rainviewer_radar_photo(
            float(self.data.get("lat", Config.LATITUDE)),
            float(self.data.get("lon", Config.LONGITUDE)),
            R,
        )
        real_radar = bool(rv_radar)
        if rv_radar:
            self.radar_photo = rv_radar["photo"]
            self.canvas.create_image(cx, cy, image=self.radar_photo,
                                     tags=("radar","slide_content", "display_scaled"))
            self.radar_status = "RAINVIEWER LIVE RADAR" if rv_radar.get("has_echo") else "RAINVIEWER LIVE RADAR: CLEAR"
            if not rv_radar.get("has_echo"):
                self._draw_clear_radar_pattern(cx, cy, R)
        else:
            self.radar_status = "OPEN-METEO PRECIP MODEL"

        # ── 同心圓刻度環 ──────────────────────────────────────
        for ratio in (0.25, 0.50, 0.75, 1.0):
            r = int(R * ratio)
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill="", outline="#004400", width=sw(1),
                tags=("radar", "slide_content", "display_scaled")
            )

        # ── 十字準星 ──────────────────────────────────────────
        self.canvas.create_line(
            cx - R, cy, cx + R, cy,
            fill="#004400", width=sw(1), tags=("radar","slide_content", "display_scaled")
        )
        self.canvas.create_line(
            cx, cy - R, cx, cy + R,
            fill="#004400", width=sw(1), tags=("radar","slide_content", "display_scaled")
        )

        # ── Forecast-driven precipitation overlay/fallback ────
        lat = float(self.data.get("lat", Config.LATITUDE))
        lon = float(self.data.get("lon", Config.LONGITUDE))
        random.seed(int((lat + 90) * 1200) ^ int((lon + 180) * 900))
        t = self.frame * 0.05
        radar_profile = self.data.get("radar", {})
        model_intensity = max(0.0, min(1.0, float(radar_profile.get("intensity", 0.0))))
        cell_count = int(radar_profile.get("cell_count", 0))
        display_cell_count = max(cell_count, 4)
        visual_intensity_floor = 0.18 if real_radar else 0.14

        rain_cells = []
        for seed in range(1, display_cell_count + 1):
            rain_cells.append((random.random() * math.tau, 0.25 + random.random() * 0.52, seed))
        rain_colors = ["#004400","#006600","#00AA00","#FFFF00","#FF8800","#FF0000"]

        # The colored circular cells are a readable terminal overlay. They remain
        # visible even when live RainViewer tiles load, so the radar always feels active.
        overlay_stipple = {"stipple": "gray50"} if real_radar else {}
        for (base_angle, r_ratio, seed) in rain_cells:
            # 讓斑塊緩慢飄移
            angle  = base_angle + t * 0.3 + seed * 0.1
            r_dist = R * (r_ratio + math.sin(t + seed) * 0.05)
            px     = cx + int(r_dist * math.cos(angle))
            py     = cy + int(r_dist * math.sin(angle))

            # 如果超出雷達圓圈則跳過
            if (px - cx)**2 + (py - cy)**2 > R**2:
                continue

            # 強度隨時間脈動
            intensity = max(visual_intensity_floor, model_intensity * (0.72 + 0.28 * math.sin(t * 2 + seed)))
            size      = int(sw(12) + sw(44) * intensity)
            col_idx   = min(int(intensity * len(rain_colors)), len(rain_colors)-1)

            # 由外到內繪製多層漸層斑塊（模擬真實雷達回波）
            for layer in range(4, 0, -1):
                layer_r   = size * layer // 4
                layer_col = rain_colors[min(col_idx + (4-layer), len(rain_colors)-1)]
                self.canvas.create_oval(
                    px - layer_r, py - layer_r,
                    px + layer_r, py + layer_r,
                    fill=layer_col, outline="",
                    tags=("radar","slide_content", "display_scaled"),
                    **overlay_stipple
                )

        # ── 旋轉掃描線（雷達掃描效果）────────────────────────
        sweep_angle = (self.frame * 6) % 360
        rad = math.radians(sweep_angle)

        # 掃描線主體（亮綠色）
        ex = cx + int(R * math.cos(rad))
        ey = cy + int(R * math.sin(rad))
        self.canvas.create_line(
            cx, cy, ex, ey,
            fill="#00FF00", width=sw(2),
            tags=("radar","slide_content", "display_scaled")
        )

        # 掃描殘影（拖尾效果，多條遞減透明的線）
        for trail in range(1, 12):
            trail_angle = math.radians(sweep_angle - trail * 4)
            tx  = cx + int(R * math.cos(trail_angle))
            ty  = cy + int(R * math.sin(trail_angle))
            # 顏色由亮到暗
            g_val = max(0, 255 - trail * 22)
            trail_col = f"#00{g_val:02X}00"
            self.canvas.create_line(
                cx, cy, tx, ty,
                fill=trail_col, width=sw(1),
                tags=("radar","slide_content", "display_scaled")
            )

        # ── 城市標記 ──────────────────────────────────────────
        self.canvas.create_oval(
            cx-sw(4), cy-sw(4), cx+sw(4), cy+sw(4),
            fill="#C9C2A5", outline=Config.TEXT_ORANGE,
            tags=("radar","slide_content", "display_scaled")
        )
        info_y = min(cy + R + sw(18), scaled_H - sw(64))
        self.canvas.create_text(
            cx, info_y,
            text=f"{Config.CITY.upper()} STATION  {lat:+.3f}/{lon:+.3f}",
            fill=Config.TEXT_WHITE, font=font(9, "bold"),
            anchor="center", tags=("radar","slide_content", "display_scaled")
        )
        self.canvas.create_text(
            cx, info_y + sw(16),
            text=(f"{self.radar_status} // {radar_profile.get('pop', 0)}% MODEL"
                  if real_radar else
                  f"PRECIP MODEL {radar_profile.get('pop', 0)}% // {radar_profile.get('source', 'FORECAST MODEL')}"),
            fill=Config.TEXT_YELLOW, font=font(8, "bold"),
            anchor="center", tags=("radar","slide_content", "display_scaled")
        )

        # ── 圖例 ──────────────────────────────────────────────
        legend_labels = ["LIGHT","RAIN","MOD","HEAVY","STORM","SEVERE"]
        legend_colors = rain_colors
        lx = sw(30)
        ly = scaled_H - sw(80)
        self.canvas.create_text(
            lx, ly - sw(15), text="RADAR ECHO INTENSITY",
            fill=Config.TEXT_WHITE, font=font(9, "bold"),
            anchor="w", tags=("radar","slide_content", "display_scaled")
        )
        for i, (lbl, col) in enumerate(zip(legend_labels, legend_colors)):
            bx = lx + i * sw(60)
            self.canvas.create_rectangle(
                bx, ly, bx+sw(12), ly+sw(12),
                fill=col, outline="", tags=("radar","slide_content", "display_scaled")
            )
            self.canvas.create_text(
                bx+sw(15), ly+sw(6), text=lbl,
                fill=Config.TEXT_WHITE, font=font(8),
                anchor="w", tags=("radar","slide_content", "display_scaled")
            )

        # ── 時間戳記 ──────────────────────────────────────────
        ts = datetime.datetime.now().strftime("UPDATED: %H:%M:%S")
        self.canvas.create_text(
            scaled_W - sw(20), scaled_H - sw(60),
            text=ts, fill=Config.TEXT_GREEN,
            font=font(9), anchor="e",
            tags=("radar","slide_content", "display_scaled")
        )

    def _draw_map_layer(self, cx: int, cy: int, R: int):
        """Draw a real OpenStreetMap tile layer centered on the searched city."""
        lat = float(self.data.get("lat", Config.LATITUDE))
        lon = float(self.data.get("lon", Config.LONGITUDE))
        photo = self._get_osm_map_photo(lat, lon, R)
        if photo:
            self.map_photo = photo
            self.canvas.create_image(cx, cy, image=self.map_photo, tags=("radar","slide_content", "display_scaled"))
            return

        self._draw_fallback_map_layer(cx, cy, R, lat, lon)

    def _get_rainviewer_radar_photo(self, lat: float, lon: float, R: int):
        """Fetch a real recent RainViewer radar tile centered on lat/lon."""
        if not PIL_AVAILABLE:
            return None
        zoom = Config.RAINVIEWER_ZOOM
        size = 512
        cache_key = (round(lat, 3), round(lon, 3), zoom, R)
        if cache_key in self.radar_cache:
            return self.radar_cache[cache_key]
        try:
            meta_resp = requests.get(
                Config.RAINVIEWER_API_URL,
                timeout=3,
                headers={"User-Agent": Config.MAP_USER_AGENT},
            )
            meta_resp.raise_for_status()
            meta = meta_resp.json()
            frames = meta.get("radar", {}).get("past", [])
            if not frames:
                return None
            frame = frames[-1]
            host = meta.get("host", "https://tilecache.rainviewer.com")
            path = frame.get("path")
            if not path:
                return None
            url = f"{host}{path}/{size}/{zoom}/{lat:.4f}/{lon:.4f}/2/1_1.png"
            resp = requests.get(url, timeout=3, headers={"User-Agent": Config.MAP_USER_AGENT})
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content)).convert("RGBA")
            has_echo = image.getchannel("A").getbbox() is not None
            image = image.resize((R * 2, R * 2), Image.Resampling.BILINEAR)
            image = self._style_radar_overlay(image, R)
            photo = ImageTk.PhotoImage(image)
            self.radar_cache[cache_key] = {"photo": photo, "has_echo": has_echo, "url": url}
            if len(self.radar_cache) > 6:
                self.radar_cache.pop(next(iter(self.radar_cache)))
            return self.radar_cache[cache_key]
        except Exception as e:
            print(f"[Radar] RainViewer radar unavailable: {e}")
            return None

    def _draw_clear_radar_pattern(self, cx: int, cy: int, R: int):
        """Show that live radar loaded successfully even when no rain echo exists."""
        display_scale = self._current_display_scale()
        sw = lambda value: max(1, int(round(value * display_scale)))
        for r in range(36, R, 34):
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                outline="#0D3B2A", width=sw(1),
                tags=("radar", "slide_content", "display_scaled")
            )
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + int(R * 0.14 * math.cos(rad))
            y1 = cy + int(R * 0.14 * math.sin(rad))
            x2 = cx + int(R * 0.92 * math.cos(rad))
            y2 = cy + int(R * 0.92 * math.sin(rad))
            self.canvas.create_line(
                x1, y1, x2, y2,
                fill="#0A2E24", width=sw(1),
                tags=("radar", "slide_content", "display_scaled")
            )

    def _style_radar_overlay(self, image, R: int):
        """Clip and slightly tint RainViewer radar into the terminal style."""
        rgba = image.convert("RGBA")
        # RainViewer tiles can be subtle against the dark map; lift the echo only.
        rgba = ImageEnhance.Color(rgba).enhance(1.35)
        rgba = ImageEnhance.Brightness(rgba).enhance(1.18)
        rgba = ImageEnhance.Contrast(rgba).enhance(1.12)
        mask = Image.new("L", rgba.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, R * 2 - 1, R * 2 - 1), fill=190)
        alpha = rgba.getchannel("A")
        alpha = ImageChops.multiply(alpha, mask) if "ImageChops" in globals() else Image.eval(alpha, lambda p: min(p, 190))
        rgba.putalpha(alpha)
        return rgba

    def _get_osm_map_photo(self, lat: float, lon: float, R: int):
        """Download and crop OpenStreetMap tiles around an exact lat/lon center."""
        if not PIL_AVAILABLE:
            return None
        zoom = Config.MAP_ZOOM
        size = R * 2
        cache_key = (round(lat, 4), round(lon, 4), zoom, size)
        if cache_key in self.map_cache:
            return self.map_cache[cache_key]
        if cache_key not in self.map_loading:
            self.map_loading.add(cache_key)
            threading.Thread(
                target=self._load_osm_map_async,
                args=(cache_key, lat, lon, R, zoom, size),
                daemon=True,
                name="OSMMapLoader",
            ).start()
        return None

    def _load_osm_map_async(self, cache_key, lat: float, lon: float, R: int, zoom: int, size: int):
        try:
            image = self._fetch_osm_map_image(lat, lon, R, zoom, size)
            def _store():
                self.map_loading.discard(cache_key)
                if image is None:
                    return
                try:
                    photo = ImageTk.PhotoImage(image)
                except Exception as exc:
                    print(f"[Map] PhotoImage creation failed: {exc}")
                    return
                self.map_cache[cache_key] = photo
                if len(self.map_cache) > 6:
                    self.map_cache.pop(next(iter(self.map_cache)))
            self.canvas.after(0, _store)
        except Exception as e:
            self.map_loading.discard(cache_key)
            print(f"[Map] OpenStreetMap async load failed: {e}")

    def _fetch_osm_map_image(self, lat: float, lon: float, R: int, zoom: int, size: int):
        try:
            world_px = 256 * (2 ** zoom)
            center_x, center_y = self._latlon_to_pixel(lat, lon, zoom)
            left = int(center_x - size / 2)
            top = int(center_y - size / 2)
            right = left + size
            bottom = top + size

            tile_x1 = math.floor(left / 256)
            tile_y1 = math.floor(top / 256)
            tile_x2 = math.floor((right - 1) / 256)
            tile_y2 = math.floor((bottom - 1) / 256)
            tiles_per_axis = 2 ** zoom

            composite = Image.new("RGB", ((tile_x2 - tile_x1 + 1) * 256,
                                          (tile_y2 - tile_y1 + 1) * 256), "#0B141B")
            headers = {"User-Agent": Config.MAP_USER_AGENT}
            for tx in range(tile_x1, tile_x2 + 1):
                for ty in range(tile_y1, tile_y2 + 1):
                    if ty < 0 or ty >= tiles_per_axis:
                        continue
                    wrapped_tx = tx % tiles_per_axis
                    url = Config.MAP_TILE_URL.format(z=zoom, x=wrapped_tx, y=ty)
                    resp = requests.get(url, headers=headers, timeout=3)
                    resp.raise_for_status()
                    tile = Image.open(BytesIO(resp.content)).convert("RGB")
                    composite.paste(tile, ((tx - tile_x1) * 256, (ty - tile_y1) * 256))

            crop_left = left - tile_x1 * 256
            crop_top = top - tile_y1 * 256
            cropped = composite.crop((crop_left, crop_top, crop_left + size, crop_top + size))
            return self._style_map_image(cropped, R)
        except Exception as e:
            print(f"[Map] OpenStreetMap tile load failed: {e}")
            return None

    @staticmethod
    def _latlon_to_pixel(lat: float, lon: float, zoom: int):
        lat = max(min(lat, 85.05112878), -85.05112878)
        sin_lat = math.sin(math.radians(lat))
        scale = 256 * (2 ** zoom)
        x = (lon + 180.0) / 360.0 * scale
        y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
        return x, y

    def _style_map_image(self, image, R: int):
        """Tint map tiles into the retro CRT palette and clip them to radar circle."""
        image = image.convert("RGB")
        image = image.filter(ImageFilter.MedianFilter(size=5))
        image = image.filter(ImageFilter.GaussianBlur(radius=0.9))
        gray = ImageOps.grayscale(image)
        gray = ImageOps.autocontrast(gray, cutoff=7)
        gray = gray.point(lambda p: 38 if p < 82 else 108 if p < 160 else 190)
        image = ImageOps.colorize(gray, black="#071016", white="#9CB88D", mid="#304D39")
        image = ImageEnhance.Contrast(image).enhance(1.18)
        image = ImageEnhance.Brightness(image).enhance(0.64)
        image = image.filter(ImageFilter.SMOOTH_MORE)

        shade = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(shade)
        w, h = image.size
        for y in range(0, h, Config.SCANLINE_STEP):
            draw.line((0, y, w, y), fill=(0, 0, 0, 46), width=1)
        for x in range(0, w, 48):
            draw.line((x, 0, x, h), fill=(89, 211, 200, 28), width=1)
        for y in range(0, h, 48):
            draw.line((0, y, w, y), fill=(89, 211, 200, 22), width=1)

        # CRT vignette and amber frame inside the radar circle.
        for radius in range(R, 0, -10):
            alpha = int(90 * (1 - radius / R) ** 1.7)
            if alpha:
                draw.ellipse((R - radius, R - radius, R + radius, R + radius),
                             outline=(0, 0, 0, alpha), width=10)
        draw.ellipse((2, 2, R * 2 - 3, R * 2 - 3), outline=(232, 212, 106, 95), width=3)
        draw.rectangle((10, 10, w - 10, 34), fill=(7, 16, 22, 150), outline=(143, 115, 66, 120))

        mask = Image.new("L", image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, R * 2 - 1, R * 2 - 1), fill=255)
        rgba = image.convert("RGBA")
        rgba.alpha_composite(shade)
        rgba.putalpha(mask)
        return rgba

    def _draw_fallback_map_layer(self, cx: int, cy: int, R: int, lat: float, lon: float):
        """Fallback map when tiles or Pillow are unavailable."""
        display_scale = self._current_display_scale()
        sw = lambda value: max(1, int(round(value * display_scale)))
        font = lambda size, weight="normal": (
            Config.FONT_FAMILY,
            max(6, int(round(size * display_scale))),
            weight,
        )
        random.seed(int((lat + 90) * 1000) ^ int((lon + 180) * 1000))

        for offset in range(-3, 4):
            x = cx + int(offset * R / 4)
            y = cy + int(offset * R / 4)
            self.canvas.create_line(x, cy - R, x, cy + R, fill="#123429", width=sw(1), tags=("radar","slide_content", "display_scaled"))
            self.canvas.create_line(cx - R, y, cx + R, y, fill="#123429", width=sw(1), tags=("radar","slide_content", "display_scaled"))

        # Pseudo terrain / coast contours keyed to coordinates, so each searched city looks distinct.
        for band in range(3):
            pts = []
            phase = (lon * 0.035) + band * 1.7
            amp = R * (0.18 + band * 0.05)
            for step in range(34):
                x = cx - R + int(step * (2 * R / 33))
                wave = math.sin(step * 0.55 + phase) + 0.45 * math.sin(step * 1.17 + lat * 0.04)
                y = cy + int(wave * amp) + (band - 1) * int(R * 0.28)
                if (x - cx) ** 2 + (y - cy) ** 2 <= (R - 8) ** 2:
                    pts.extend([x, y])
            if len(pts) >= 4:
                self.canvas.create_line(
                    *pts, fill=["#35634C", "#284D61", "#5F5936"][band],
                    width=sw(2), smooth=True, tags=("radar","slide_content", "display_scaled")
                )

        for idx in range(10):
            angle = random.random() * math.tau
            dist = random.random() * R * 0.82
            px = cx + int(math.cos(angle) * dist)
            py = cy + int(math.sin(angle) * dist)
            if (px - cx) ** 2 + (py - cy) ** 2 <= (R - 10) ** 2:
                self.canvas.create_rectangle(px - sw(2), py - sw(2), px + sw(2), py + sw(2), fill="#6C7F66", outline="", tags=("radar","slide_content", "display_scaled"))

        self.canvas.create_text(
            cx - R + sw(12), cy - R + sw(16),
            text=f"MAP CENTER {lat:+.2f} / {lon:+.2f}",
            fill="#93A8A2", font=font(8, "bold"),
            anchor="w", tags=("radar","slide_content", "display_scaled")
        )


# ════════════════════════════════════════════════════════════════
#  主應用程式 — 整合所有模組
# ════════════════════════════════════════════════════════════════
class RetroCastApp:
    """
    Arcadia 5000 主應用程式
    職責：
    1. 初始化 Tkinter 視窗與 Canvas
    2. 管理看板輪播排程
    3. 繪製 CRT 掃描線濾鏡
    4. 控制跑馬燈動畫
    5. 協調 WeatherData 與各 SlideRenderer
    """

    # 看板順序定義（可自由調整）
    SLIDES = ["current", "summary", "hourly", "ad", "comparison", "observations", "forecast", "radar", "credits"]
    SLIDE_NAMES = {
        "current"     : "Current",
        "summary"     : "Summary",
        "hourly"      : "Hourly",
        "comparison"  : "Comparison",
        "ad"          : "Ad",
        "observations": "Observations",
        "forecast"    : "Forecast",
        "radar"       : "Radar",
        "credits"      : "Credits",
    }

    def __init__(self):
        Config.load_from_json()
        # ── 初始化子系統 ──────────────────────────────────────
        self.data_manager   = WeatherData()
        self.audio          = AudioController()
        self.current_slide  = 0
        self.slide_after_id = None
        self.clock_after_id = None
        self.api_after_id   = None
        self.crt_after_id   = None
        self.marquee_after_id = None
        self.city_choice_dialog = None
        self.city_search_token = 0
        self.logo_cache = {}
        self.marquee_logo_refs = []
        self.crt_phase      = 0
        self.app_started    = False
        self._did_initial_announce = False
        self._reset_to_first_after_refresh = False
        self.rotation_paused = False
        self.is_fullscreen = False
        self.display_scale = 1.0
        self.loading_active = False
        self.loading_percent = 0
        self.loading_status = ""
        self.loading_clear_after_id = None
        self.start_widgets  = []
        self._setup_window()
        self._setup_custom_font()
        self._setup_canvas()
        self._setup_slide_renderers()
        self._show_boot_sequence()

    # ── 視窗設定 ──────────────────────────────────────────────
    def _setup_window(self):
        self.root = tk.Tk()
        self.root.title("Arcadia 5000 — Halcyon Weather Terminal")
        self.root.geometry(f"{Config.WIN_WIDTH}x{Config.WIN_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=Config.BG_DARK)
        # 綁定 ESC 鍵退出
        self.root.bind("<Escape>", lambda e: self.quit())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

    def _setup_custom_font(self):
        """Register and activate the bundled Belgrad TTF when available."""
        Config.FONT_FAMILY = Config.FONT_FALLBACK
        font_path = Config.FONT_PATH
        if not os.path.exists(font_path):
            print(f"[Font] Custom font not found: {font_path}")
            self._apply_named_tk_fonts()
            return

        if sys.platform == "darwin":
            self._register_font_macos(font_path)

        self.root.update_idletasks()
        family_guess = os.path.splitext(os.path.basename(font_path))[0]
        available = {name.lower(): name for name in tkfont.families(self.root)}
        Config.ICON_FONT_FAMILY = available.get("apple color emoji", Config.FONT_FALLBACK)
        for candidate in (family_guess, "Belgrad", "Belgrad Regular"):
            found = available.get(candidate.lower())
            if found:
                Config.FONT_FAMILY = found
                self._apply_named_tk_fonts()
                print(f"[Font] Using custom font: {Config.FONT_FAMILY}")
                return

        # If CoreText registered the font but Tk has not refreshed families yet,
        # the family name usually still resolves by the file stem on macOS.
        Config.FONT_FAMILY = family_guess
        self._apply_named_tk_fonts()
        print(f"[Font] Trying custom font family: {Config.FONT_FAMILY}")

    def _apply_named_tk_fonts(self):
        """Make Tk widgets use the same family as Canvas text where possible."""
        for name in (
            "TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont",
            "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont",
            "TkIconFont", "TkTooltipFont",
        ):
            try:
                tkfont.nametofont(name).configure(family=Config.FONT_FAMILY)
            except tk.TclError:
                continue

    def _register_font_macos(self, font_path: str) -> bool:
        """Temporarily register a TTF for this process on macOS."""
        try:
            core_foundation = ctypes.CDLL(find_library("CoreFoundation"))
            core_text = ctypes.CDLL(find_library("CoreText"))

            core_foundation.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
            core_foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
            core_foundation.CFURLCreateWithFileSystemPath.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_bool]
            core_foundation.CFURLCreateWithFileSystemPath.restype = ctypes.c_void_p
            core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
            core_text.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
            core_text.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool

            k_cf_string_encoding_utf8 = 0x08000100
            k_cfurl_posix_path_style = 0
            k_ct_font_manager_scope_process = 1

            cf_path = core_foundation.CFStringCreateWithCString(
                None, font_path.encode("utf-8"), k_cf_string_encoding_utf8
            )
            if not cf_path:
                return False
            url = core_foundation.CFURLCreateWithFileSystemPath(
                None, cf_path, k_cfurl_posix_path_style, False
            )
            if not url:
                core_foundation.CFRelease(cf_path)
                return False

            error = ctypes.c_void_p()
            ok = bool(core_text.CTFontManagerRegisterFontsForURL(
                url, k_ct_font_manager_scope_process, ctypes.byref(error)
            ))
            core_foundation.CFRelease(url)
            core_foundation.CFRelease(cf_path)
            return ok
        except Exception as exc:
            print(f"[Font] macOS font registration failed: {exc}")
            return False

    # ── Canvas 設定 ────────────────────────────────────────────
    def _setup_canvas(self):
        """主畫布（去掉跑馬燈高度）"""
        canvas_h = Config.WIN_HEIGHT - Config.MARQUEE_HEIGHT - Config.CONTROL_HEIGHT
        self.canvas = tk.Canvas(
            self.root,
            width=Config.WIN_WIDTH,
            height=canvas_h,
            bg=Config.BG_DARK,
            highlightthickness=0
        )
        self.canvas.pack(side="top")

    def _canvas_height(self):
        return Config.WIN_HEIGHT - Config.MARQUEE_HEIGHT - Config.CONTROL_HEIGHT

    def _scaled(self, value: float) -> int:
        return int(round(value * self.display_scale))

    def _configure_scaled_layout(self):
        """Resize the visible shell while keeping the original 800x600 ratio."""
        canvas_h = Config.WIN_HEIGHT - Config.MARQUEE_HEIGHT - Config.CONTROL_HEIGHT
        self.canvas.configure(
            width=self._scaled(Config.WIN_WIDTH),
            height=self._scaled(canvas_h),
        )
        if hasattr(self, "control_frame"):
            self.control_frame.configure(height=self._scaled(Config.CONTROL_HEIGHT))
        if hasattr(self, "marquee_frame"):
            self.marquee_frame.configure(height=self._scaled(Config.MARQUEE_HEIGHT))
        if hasattr(self, "marquee_canvas"):
            self.marquee_canvas.configure(height=self._scaled(Config.MARQUEE_HEIGHT))
            self._refresh_marquee_text()
        self._configure_control_fonts()

    def _configure_control_fonts(self):
        if not hasattr(self, "control_frame"):
            return
        for child in self.control_frame.winfo_children():
            try:
                if isinstance(child, tk.Entry):
                    child.configure(font=(Config.FONT_FAMILY, self._scaled(9), "bold"), width=16)
                elif isinstance(child, tk.Label):
                    child.configure(font=(Config.FONT_FAMILY, self._scaled(8), "bold"))
                elif isinstance(child, tk.Button):
                    child.configure(font=(Config.FONT_FAMILY, self._scaled(9), "bold"))
            except tk.TclError:
                pass

    def _scale_canvas_items_for_display(self):
        """Scale newly drawn Canvas items for fullscreen demo mode."""
        scale = self.display_scale
        if abs(scale - 1.0) < 0.01 or not hasattr(self, "canvas"):
            return
        for item in self.canvas.find_all():
            tags = self.canvas.gettags(item)
            if "display_scaled" in tags:
                continue
            self.canvas.scale(item, 0, 0, scale, scale)
            if self.canvas.type(item) == "text":
                self._scale_canvas_text_item(item, scale)
            self._scale_canvas_width_item(item, scale)
            self.canvas.addtag_withtag("display_scaled", item)

    def _scale_canvas_text_item(self, item, scale: float):
        try:
            font_spec = self.canvas.itemcget(item, "font")
            font_obj = tkfont.Font(root=self.root, font=font_spec)
            family = font_obj.actual("family")
            size = abs(int(font_obj.actual("size") or 10))
            weight = font_obj.actual("weight")
            slant = font_obj.actual("slant")
            scaled_size = max(6, int(round(size * scale)))
            self.canvas.itemconfig(item, font=(family, scaled_size, weight, slant))
        except Exception:
            pass

    def _scale_canvas_width_item(self, item, scale: float):
        try:
            width = self.canvas.itemcget(item, "width")
            if width not in ("", None):
                self.canvas.itemconfig(item, width=max(1, float(width) * scale))
        except Exception:
            pass

    def _load_logo_photo(self, key: str, max_size=(80, 44), opacity: float = 1.0):
        """Load a branded logo asset as a Tk image with optional sizing."""
        cache_key = (key, int(max_size[0]), int(max_size[1]), round(opacity, 2))
        if cache_key in self.logo_cache:
            return self.logo_cache[cache_key]
        path = Config.LOGO_PATHS.get(key, "")
        if not PIL_AVAILABLE or not path or not os.path.exists(path):
            return None
        try:
            image = Image.open(path).convert("RGBA")
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            if opacity < 1.0:
                alpha = image.getchannel("A")
                alpha = ImageEnhance.Brightness(alpha).enhance(max(0.0, min(1.0, opacity)))
                image.putalpha(alpha)
            photo = ImageTk.PhotoImage(image)
            self.logo_cache[cache_key] = photo
            return photo
        except Exception as exc:
            print(f"[Logo] Could not load {key}: {exc}")
            return None

    def _draw_canvas_logo(self, key: str, x: int, y: int, max_size=(80, 44),
                          opacity: float = 1.0, anchor: str = "center", tag="slide_content"):
        photo = self._load_logo_photo(key, max_size=max_size, opacity=opacity)
        if not photo:
            return None
        return self.canvas.create_image(x, y, image=photo, anchor=anchor, tags=(tag, "slide_content"))

    def _show_boot_sequence(self):
        """Short Halcyon terminal boot animation before city selection."""
        self.audio.play_file(Config.BOOT_SOUND_PATH, volume=0.9)
        renderer = SlideRenderer(self.canvas, Config)
        renderer.clear()
        self.boot_lines = [
            "HALCYON HOLDINGS BIOS REV. 5.00",
            "VALIDATING WEATHERBAND LICENSE...",
            "CALIBRATING PHOSPHOR GRID...",
            "OPEN-METEO RELAY: READY",
            "CORPORATE ALERT MATRIX: ARMED",
            "AWAITING AUTHORIZED CITY LOCK",
        ]
        self.boot_index = 0
        self._draw_boot_frame()

    def _draw_boot_frame(self):
        renderer = SlideRenderer(self.canvas, Config)
        renderer.clear()
        renderer.draw_text(self.WIN_CENTER_X, 82, "ARCADIA 5000",
                           color=Config.TEXT_YELLOW, size=28, bold=True)
        self._draw_canvas_logo("halcyon", 96, 72, max_size=(62, 62), opacity=0.72)
        self._draw_canvas_logo("flaw", Config.WIN_WIDTH - 104, 78, max_size=(72, 54), opacity=0.58)
        renderer.draw_text(self.WIN_CENTER_X, 116, "HALCYON WEATHERBAND BOOT SEQUENCE",
                           color=Config.TEXT_CYAN, size=12, bold=True)
        renderer.draw_rect(128, 158, Config.WIN_WIDTH - 128, 398,
                           fill="#0A0F0A", outline=Config.BORDER_COL, width=2)
        self._draw_crt_ambience(standby=True)
        for i, line in enumerate(self.boot_lines[:self.boot_index]):
            renderer.draw_text(158, 194 + i * 30, f"> {line}",
                               color=Config.TEXT_GREEN if i < self.boot_index - 1 else Config.TEXT_YELLOW,
                               size=11, bold=True, anchor="w")
        cursor = "█" if self.boot_index % 2 == 0 else "_"
        if self.boot_index < len(self.boot_lines):
            renderer.draw_text(158, 194 + self.boot_index * 30, f"> {cursor}",
                               color=Config.TEXT_ORANGE, size=11, bold=True, anchor="w")
            self.audio.play_cue("slide")
            self.boot_index += 1
            self.root.after(360, self._draw_boot_frame)
        else:
            renderer.draw_text(self.WIN_CENTER_X, 438, "TERMINAL READY",
                               color=Config.TEXT_YELLOW, size=13, bold=True)
            self.audio.play_cue("enable")
            self.root.after(650, self._show_start_screen)

    @property
    def WIN_CENTER_X(self):
        return Config.WIN_WIDTH // 2

    def _show_start_screen(self):
        """Initial city-lock screen before the broadcast starts."""
        renderer = SlideRenderer(self.canvas, Config)
        renderer.clear()
        renderer.draw_text(self.canvas.winfo_reqwidth() // 2, 92,
                           "ARCADIA 5000", color=Config.TEXT_YELLOW, size=28, bold=True)
        self._draw_canvas_logo("halcyon", 154, 92, max_size=(68, 68), opacity=0.76)
        self._draw_canvas_logo("flaw", Config.WIN_WIDTH - 154, 96, max_size=(78, 58), opacity=0.62)
        renderer.draw_text(self.canvas.winfo_reqwidth() // 2, 128,
                           "A HALCYON-CERTIFIED WEATHER TERMINAL", color=Config.TEXT_CYAN, size=13, bold=True)
        renderer.draw_rect(170, 170, Config.WIN_WIDTH - 170, 356,
                           fill=Config.BG_PANEL, outline=Config.BORDER_COL, width=2)
        renderer.draw_text(Config.WIN_WIDTH // 2, 206,
                           "SELECT BROADCAST CITY", color=Config.TEXT_ORANGE, size=15, bold=True)
        renderer.draw_text(Config.WIN_WIDTH // 2, 238,
                           "Type a city name, then press ENTER or START.",
                           color=Config.TEXT_WHITE, size=11)
        renderer.draw_text(Config.WIN_WIDTH // 2, 398,
                           "Operational feed by Open-Meteo. Compliance is appreciated.",
                           color="#93A8A2", size=10, bold=True)
        self._draw_crt_ambience(standby=True)
        self._start_crt_ambience(standby=True)

        self.start_var = tk.StringVar(value=Config.CITY)
        entry = tk.Entry(
            self.root,
            textvariable=self.start_var,
            bg="#071016", fg=Config.TEXT_WHITE,
            insertbackground=Config.TEXT_YELLOW,
            highlightthickness=2,
            highlightbackground=Config.BORDER_COL,
            highlightcolor=Config.TEXT_CYAN,
            relief="flat",
            font=(Config.FONT_FAMILY, 16, "bold"),
            justify="center",
            width=22,
        )
        entry.place(x=Config.WIN_WIDTH // 2, y=270, anchor="center")
        entry.bind("<Return>", lambda _e: self._start_from_search())
        entry.focus_set()

        btn_cfg = dict(
            bg="#172A2D", fg=Config.TEXT_YELLOW,
            activebackground="#27484C",
            activeforeground=Config.TEXT_WHITE,
            font=(Config.FONT_FAMILY, 12, "bold"),
            relief="flat", bd=1, padx=16, pady=7,
            cursor="hand2"
        )
        start_btn = tk.Button(self.root, text="START BROADCAST", command=self._start_from_search, **btn_cfg)
        start_btn.place(x=Config.WIN_WIDTH // 2, y=320, anchor="center")

        self.start_status = tk.Label(
            self.root,
            text="AWAITING CITY LOCK",
            bg=Config.BG_DARK, fg=Config.TEXT_GREEN,
            font=(Config.FONT_FAMILY, 10, "bold")
        )
        self.start_status.place(x=Config.WIN_WIDTH // 2, y=374, anchor="center")
        self.start_widgets = [entry, start_btn, self.start_status]

    def _start_from_search(self):
        """Resolve the startup city, fetch data, then enter broadcast mode."""
        query = self.start_var.get().strip()
        if not query:
            return
        self.start_status.config(text=f"SEARCHING {query.upper()}...", fg=Config.TEXT_CYAN)
        self._set_loading_progress(8, "CITY LOCK REQUESTED")
        self._request_city_selection(
            query,
            self._load_startup_city,
            status_callback=lambda msg, color=Config.TEXT_CYAN: self.start_status.config(text=msg, fg=color),
            progress_callback=self._make_loading_progress_callback(),
        )

    def _load_startup_city(self, place: dict):
        if hasattr(self, "start_status"):
            self.start_status.config(
                text=f"LOCKING {place.get('city', Config.CITY).upper()}...",
                fg=Config.TEXT_CYAN
            )
        progress = self._make_loading_progress_callback()
        progress(38, f"LOCKING {place.get('city', Config.CITY)}")
        def _worker():
            try:
                self.data_manager.set_location(place["city"], place["country"], place["lat"], place["lon"])
                if hasattr(self, "renderers") and "radar" in self.renderers:
                    self.renderers["radar"].clear_location_cache()
                progress(48, "CONTACTING WEATHER RELAY")
                current = self.data_manager.fetch_current_weather()
                progress(58, "CURRENT CONDITIONS RECEIVED")
                forecast = self.data_manager.fetch_forecast()
                progress(68, "DAILY FORECAST RECEIVED")
                hourly = self.data_manager.fetch_hourly_forecast()
                progress(76, "HOURLY TIMELINE RECEIVED")
                current["alert"] = self.data_manager.calculate_alert(current, forecast, hourly)
                current["radar"] = self.data_manager.calculate_radar_profile(current, hourly)
                progress(84, "GENERATING OLLAMA SUMMARY")
                current["ai_summary"] = self.data_manager.generate_weather_summary(current, forecast, hourly)
                try:
                    progress(94, "SYNCING REGIONAL COMPARISON")
                    comparison = self.data_manager.fetch_comparison(current)
                except Exception:
                    comparison = [current]
                with self.data_manager._lock:
                    self.data_manager.current = current
                    self.data_manager.forecast = forecast
                    self.data_manager.hourly = hourly
                    self.data_manager.comparison = comparison
                    self.data_manager.last_fetch = datetime.datetime.now()
                    self.data_manager.error_msg = ""

                progress(100, "BROADCAST DATA READY")
                self.root.after(0, lambda: self._enter_broadcast(place))
            except Exception as e:
                msg = f"LOCK FAILED: {str(e)[:52]}"
                progress(100, "LOCK FAILED")
                self.root.after(0, lambda: self.start_status.config(text=msg.upper(), fg=Config.TEXT_RED))

        threading.Thread(target=_worker, daemon=True, name="StartupCitySearch").start()

    def _format_place_label(self, place: dict) -> str:
        admin = f", {place.get('admin')}" if place.get("admin") else ""
        pop = place.get("population") or 0
        pop_text = f"  POP {pop:,}" if pop else ""
        return (
            f"{place.get('city','--')}{admin}, {place.get('country','')}  "
            f"{place.get('lat', 0):+.2f}/{place.get('lon', 0):+.2f}{pop_text}"
        )

    def _request_city_selection(self, query: str, on_select, status_callback=None, progress_callback=None):
        """Fetch city candidates; show a chooser when more than one result exists."""
        self._close_city_choice_dialog()
        self.city_search_token += 1
        search_token = self.city_search_token
        if progress_callback:
            progress_callback(18, "QUERYING CITY INDEX")
        def _worker():
            try:
                places = self.data_manager.search_cities(query, count=7)
                def _ready():
                    if search_token != self.city_search_token:
                        return
                    if progress_callback:
                        progress_callback(32, "CITY CANDIDATES RECEIVED")
                    if status_callback:
                        status_callback("SELECT CITY LOCK", Config.TEXT_YELLOW)
                    if len(places) == 1:
                        on_select(places[0])
                    else:
                        self._show_city_choice_dialog(places, on_select)
                self.root.after(0, _ready)
            except Exception as e:
                msg = f"SEARCH FAILED: {str(e)[:48]}"
                if progress_callback:
                    self.root.after(0, lambda: progress_callback(100, "CITY SEARCH FAILED") if search_token == self.city_search_token else None)
                if status_callback:
                    self.root.after(0, lambda: status_callback(msg, Config.TEXT_RED) if search_token == self.city_search_token else None)
                elif hasattr(self, "slide_label"):
                    def _err():
                        if search_token != self.city_search_token:
                            return
                        self.slide_label.config(text="ERR")
                        if hasattr(self, "marquee_messages"):
                            self.marquee_messages.insert(0, ("halcyon", f"WARN: {msg}"))
                            self._refresh_marquee_text()
                        self.audio.announce(msg, "alert")
                    self.root.after(0, _err)
        threading.Thread(target=_worker, daemon=True, name="CityCandidateSearch").start()

    def _close_city_choice_dialog(self):
        """Close any previous city chooser and release its modal grab."""
        dialog = getattr(self, "city_choice_dialog", None)
        exists = False
        if dialog:
            try:
                exists = bool(dialog.winfo_exists())
            except tk.TclError:
                exists = False
        if exists:
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            try:
                dialog.destroy()
            except tk.TclError:
                pass
        self.city_choice_dialog = None

    def _show_city_choice_dialog(self, places: list, on_select):
        """Small Tkinter selector for ambiguous city searches."""
        self._close_city_choice_dialog()
        if not self.root.winfo_exists():
            return
        dialog = tk.Toplevel(self.root)
        self.city_choice_dialog = dialog
        dialog.title("Select City Lock")
        dialog.geometry("560x310")
        dialog.configure(bg=Config.BG_DARK)
        dialog.resizable(False, False)
        dialog.transient(self.root)

        title = tk.Label(
            dialog, text="SELECT CITY LOCK",
            bg=Config.BG_DARK, fg=Config.TEXT_YELLOW,
            font=(Config.FONT_FAMILY, 16, "bold")
        )
        title.pack(pady=(14, 6))

        listbox = tk.Listbox(
            dialog, bg="#071016", fg=Config.TEXT_WHITE,
            selectbackground=Config.TEXT_ORANGE, selectforeground="#050505",
            highlightthickness=1, highlightbackground=Config.BORDER_COL,
            activestyle="none", font=(Config.FONT_FAMILY, 11, "bold"),
            height=7, width=62
        )
        listbox.pack(padx=18, pady=6, fill="x")
        for place in places:
            listbox.insert("end", self._format_place_label(place))
        listbox.selection_set(0)

        btn_frame = tk.Frame(dialog, bg=Config.BG_DARK)
        btn_frame.pack(pady=12)
        btn_cfg = dict(
            bg="#172A2D", fg=Config.TEXT_YELLOW,
            activebackground="#27484C", activeforeground=Config.TEXT_WHITE,
            font=(Config.FONT_FAMILY, 11, "bold"),
            relief="flat", bd=1, padx=14, pady=6,
            cursor="hand2"
        )

        def _choose():
            selection = listbox.curselection()
            if not selection:
                return
            place = places[selection[0]]
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()
            self.city_choice_dialog = None
            on_select(place)

        def _cancel():
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()
            self.city_choice_dialog = None
            self._clear_loading_progress()
            if getattr(self, "app_started", False) and hasattr(self, "slide_label"):
                self.slide_label.config(text=f"{self.current_slide+1}/{len(self.SLIDES)}")
            elif hasattr(self, "start_status"):
                self.start_status.config(text="AWAITING CITY LOCK", fg=Config.TEXT_GREEN)

        tk.Button(btn_frame, text="LOCK", command=_choose, **btn_cfg).pack(side="left", padx=8)
        tk.Button(btn_frame, text="CANCEL", command=_cancel, **btn_cfg).pack(side="left", padx=8)
        listbox.bind("<Double-Button-1>", lambda _e: _choose())
        listbox.bind("<Return>", lambda _e: _choose())
        dialog.protocol("WM_DELETE_WINDOW", _cancel)
        dialog.grab_set()
        listbox.focus_set()

    def _enter_broadcast(self, place: dict):
        """Destroy startup UI and begin the normal weather broadcast."""
        for widget in self.start_widgets:
            widget.destroy()
        self.start_widgets = []
        self.app_started = True
        self._did_initial_announce = False
        self._setup_marquee()
        self._setup_controls()
        self.search_var.set(place.get("city", Config.CITY))
        self._setup_scanlines()
        self._setup_progress_bar()
        self._start_crt_ambience()
        self.show_slide(0)
        self._schedule_next_slide()
        self._update_clock()
        if Config.MUSIC_ENABLED:
            self.audio.load_and_play(Config.BGM_PATH)
        self._schedule_api_refresh()
        self.audio.play_cue("enable")

    # ── CRT 掃描線覆蓋層 ──────────────────────────────────────
    def _setup_scanlines(self):
        """
        保留此方法供主流程呼叫；掃描線已改由背景層繪製，
        避免線條蓋在文字與資料表上影響閱讀。
        """
        self.canvas.delete("scanline")

    def _start_crt_ambience(self, standby: bool = False):
        """Start a lightweight CRT ambience loop that keeps text readable."""
        if self.crt_after_id:
            self.root.after_cancel(self.crt_after_id)
            self.crt_after_id = None
        self.crt_phase = 0
        self._animate_crt_ambience(standby=standby)

    def _animate_crt_ambience(self, standby: bool = False):
        self._draw_crt_ambience(standby=standby)
        self.crt_phase = (self.crt_phase + 1) % 240
        if standby or self.app_started:
            self.crt_after_id = self.root.after(
                Config.CRT_AMBIENCE_MS,
                lambda: self._animate_crt_ambience(standby=standby and not self.app_started)
            )

    def _draw_crt_ambience(self, standby: bool = False):
        """
        Draw subtle CRT motion above the screen: edge haze, sync drift, and a
        narrow scan sweep. It avoids dense noise over the data area.
        """
        self.canvas.delete("crt_ambience")
        scale = self.display_scale
        h = self._scaled(self._canvas_height())
        w = self._scaled(Config.WIN_WIDTH)
        phase = self.crt_phase
        margin = self._scaled(Config.BEZEL_SIZE + 8)
        scan_step = max(6, self._scaled(Config.CRT_SCAN_STEP))
        edge_scan_len = self._scaled(72)

        # Soft edge brackets, not full rectangles; full outlines become intrusive
        # when macOS fullscreen scales the terminal.
        bracket = self._scaled(88)
        for inset, color, width in (
            (self._scaled(7), "#020403", 5),
            (self._scaled(18), "#050806", 3),
        ):
            line_w = max(1, int(round(width * scale)))
            corners = (
                (inset, inset, 1, 1),
                (w - inset, inset, -1, 1),
                (inset, h - inset, 1, -1),
                (w - inset, h - inset, -1, -1),
            )
            for x, y, hx, vy in corners:
                self.canvas.create_line(
                    x, y, x + hx * bracket, y,
                    fill=color, width=line_w,
                    tags=("crt_ambience", "display_scaled")
                )
                self.canvas.create_line(
                    x, y, x, y + vy * bracket,
                    fill=color, width=line_w,
                    tags=("crt_ambience", "display_scaled")
                )

        # Sparse phosphor scan hints in the gutters, not across the content.
        for y in range(margin + (phase % scan_step), h - margin, scan_step):
            if y % 3 == 0:
                self.canvas.create_line(
                    margin, y, margin + edge_scan_len, y,
                    fill="#122019", width=max(1, int(round(scale))), tags=("crt_ambience", "display_scaled")
                )
                self.canvas.create_line(
                    w - margin - edge_scan_len, y, w - margin, y,
                    fill="#122019", width=max(1, int(round(scale))), tags=("crt_ambience", "display_scaled")
                )

        # One thin moving scan sweep after startup; the city-lock screen stays calmer.
        if not standby:
            sweep_y = margin + ((phase * 5) % max(1, h - margin * 2))
            self.canvas.create_line(
                margin, sweep_y, w - margin, sweep_y,
                fill="#1B332A", width=max(1, int(round(scale))), tags=("crt_ambience", "display_scaled")
            )

        # Occasional horizontal sync tear, kept near outer thirds to preserve tables.
        if phase % 17 in (0, 1, 2):
            tear_y = margin + ((phase * 19) % max(1, h - margin * 2))
            tear_len = self._scaled(96 if standby else 64)
            self.canvas.create_rectangle(
                margin + self._scaled(16), tear_y,
                margin + self._scaled(16) + tear_len, tear_y + self._scaled(2),
                fill=Config.TEXT_CYAN, outline="", stipple="gray75",
                tags=("crt_ambience", "display_scaled")
            )
            self.canvas.create_rectangle(
                w - margin - self._scaled(16) - tear_len, tear_y + self._scaled(4),
                w - margin - self._scaled(16), tear_y + self._scaled(6),
                fill=Config.TEXT_ORANGE, outline="", stipple="gray75",
                tags=("crt_ambience", "display_scaled")
            )

        # Standby mode only breathes at the corners, without a left-to-right beam.
        if standby and phase % 20 < 10:
            for x, y in ((margin, margin), (w - margin, margin), (margin, h - margin), (w - margin, h - margin)):
                self.canvas.create_oval(
                    x - self._scaled(4), y - self._scaled(4),
                    x + self._scaled(4), y + self._scaled(4),
                    fill="#335F48", outline="", stipple="gray75",
                    tags=("crt_ambience", "display_scaled")
                )

        self.canvas.tag_raise("crt_ambience")
        if hasattr(self, "pb_fg"):
            self.canvas.tag_raise("progress")

    # ── 跑馬燈設定 ────────────────────────────────────────────
    def _setup_marquee(self):
        """底部跑馬燈文字帶"""
        if self.marquee_after_id:
            self.root.after_cancel(self.marquee_after_id)
            self.marquee_after_id = None
        self.marquee_frame = tk.Frame(
            self.root,
            bg="#341617",  # 暗紅色背景，符合緊急警報風格
            height=Config.MARQUEE_HEIGHT
        )
        self.marquee_frame.pack(side="bottom", fill="x")
        self.marquee_frame.pack_propagate(False)

        # 跑馬燈 Canvas（用 Canvas 而非 Label，方便精確控制位置）
        self.marquee_canvas = tk.Canvas(
            self.marquee_frame,
            bg="#341617",
            height=Config.MARQUEE_HEIGHT,
            highlightthickness=0
        )
        self.marquee_canvas.pack(fill="both", expand=True)

        # 跑馬燈文字內容（可在此新增更多氣象資訊）
        with self.data_manager._lock:
            alert = dict(self.data_manager.current.get("alert", {}))
        alert_level = alert.get("level", "CLEAR")
        alert_message = alert.get("message", "Atmospheric conditions are within profitable tolerance.")
        self.marquee_messages = [
            ("halcyon", f"CORPORATE ALERT {alert_level}: {alert_message}"),
            ("sub_rosa", "ARCADIA 5000 / RETROCAST NOW RELAY  |  DATA SOURCE: OPEN-METEO"),
            ("order", f"MONITORING STATION: {Config.CITY}, {Config.COUNTRY}  |  FEED AUTO-REFRESHES EVERY {Config.API_REFRESH//60} MINUTES"),
            ("spacers_choice", "All Spacer's Choice weapons are now thirty percent less likely to malfunction!"),
            ("auntie_cleo", "When life gives you lemons, consider it a free trial from your friends at Spacer's Choice."),
        ]

        self.marquee_x   = Config.WIN_WIDTH   # 從右邊開始
        self._rebuild_marquee_items()
        self._animate_marquee()

    def _animate_marquee(self):
        """跑馬燈動畫（持續向左移動）"""
        self.marquee_after_id = None
        try:
            canvas_ready = (
                hasattr(self, "marquee_canvas")
                and self.marquee_canvas.winfo_exists()
                and hasattr(self, "marquee_items")
            )
        except tk.TclError:
            canvas_ready = False
        if not canvas_ready:
            self.marquee_after_id = None
            return

        try:
            speed = max(1, self._scaled(Config.MARQUEE_SPEED))
            self.marquee_x -= speed
            self.marquee_canvas.move("marquee_item", -speed, 0)
            # 取得文字寬度，超出左邊後重置
            bbox = self.marquee_canvas.bbox("marquee_item")
            if bbox and bbox[2] < 0:  # 文字完全移出左側
                dx = self._scaled(Config.WIN_WIDTH) - bbox[0]
                self.marquee_canvas.move("marquee_item", dx, 0)
                self.marquee_x = self._scaled(Config.WIN_WIDTH)
        except tk.TclError:
            self.marquee_after_id = None
            return

        self.marquee_after_id = self.root.after(Config.MARQUEE_INTERVAL, self._animate_marquee)

    def _refresh_marquee_text(self):
        if not hasattr(self, "marquee_canvas"):
            return
        try:
            self._rebuild_marquee_items()
        except tk.TclError:
            self.marquee_after_id = None
            return
        if not self.marquee_after_id:
            self.marquee_after_id = self.root.after(Config.MARQUEE_INTERVAL, self._animate_marquee)

    def _rebuild_marquee_items(self):
        self.marquee_canvas.delete("marquee_item")
        self.marquee_logo_refs = []
        self.marquee_items = []
        x = self._scaled(Config.WIN_WIDTH)
        y = self._scaled(Config.MARQUEE_HEIGHT // 2)
        for _ in range(2):
            for logo_key, text in self.marquee_messages:
                photo = self._load_logo_photo(
                    logo_key,
                    max_size=(self._scaled(26), self._scaled(20)),
                    opacity=0.92
                )
                if photo:
                    self.marquee_logo_refs.append(photo)
                    item = self.marquee_canvas.create_image(x, y, image=photo, anchor="w", tags=("marquee_item",))
                    self.marquee_items.append(item)
                    x += self._scaled(31)
                text_item = self.marquee_canvas.create_text(
                    x, y,
                    text=text,
                    fill=Config.TEXT_YELLOW,
                    font=(Config.FONT_FAMILY, self._scaled(12), "bold"),
                    anchor="w",
                    tags=("marquee_item",)
                )
                self.marquee_items.append(text_item)
                bbox = self.marquee_canvas.bbox(text_item)
                x = (bbox[2] if bbox else x + len(text) * self._scaled(8)) + self._scaled(34)
                sep = self.marquee_canvas.create_text(
                    x, y, text="//", fill=Config.TEXT_ORANGE,
                    font=(Config.FONT_FAMILY, self._scaled(11), "bold"), anchor="w",
                    tags=("marquee_item",)
                )
                self.marquee_items.append(sep)
                bbox = self.marquee_canvas.bbox(sep)
                x = (bbox[2] if bbox else x + self._scaled(18)) + self._scaled(34)
        self.marquee_x = self._scaled(Config.WIN_WIDTH)

    # ── 控制列設定 ────────────────────────────────────────────
    def _setup_controls(self):
        """左上角控制按鈕（音效、手動切換）"""
        self.control_frame = tk.Frame(
            self.root,
            bg="#070A08",
            height=Config.CONTROL_HEIGHT,
            highlightthickness=1,
            highlightbackground=Config.BORDER_COL,
        )
        self.control_frame.pack(side="bottom", fill="x", before=self.marquee_frame)
        self.control_frame.pack_propagate(False)

        btn_cfg = dict(
            bg="#172A2D", fg=Config.TEXT_YELLOW,
            activebackground="#27484C",
            activeforeground=Config.TEXT_WHITE,
            font=(Config.FONT_FAMILY, 9, "bold"),
            relief="flat", bd=1, padx=5, pady=2,
            cursor="hand2"
        )

        # 音效切換按鈕
        self.audio_btn = tk.Button(
            self.control_frame, text="MUSIC", command=self._toggle_audio, **btn_cfg
        )
        self.audio_btn.grid(row=0, column=0, padx=(10, 5), pady=9, sticky="w")

        self.sfx_btn = tk.Button(
            self.control_frame, text="SFX", command=self._toggle_sfx, **btn_cfg
        )
        self.sfx_btn.grid(row=0, column=1, padx=5, pady=9, sticky="w")

        # 手動上一張
        prev_btn = tk.Button(
            self.control_frame, text="PREV", command=self._prev_slide, **btn_cfg
        )
        prev_btn.grid(row=0, column=2, padx=(18, 5), pady=9, sticky="w")

        # 手動下一張
        next_btn = tk.Button(
            self.control_frame, text="NEXT", command=self._next_slide, **btn_cfg
        )
        next_btn.grid(row=0, column=3, padx=5, pady=9, sticky="w")

        self.pause_btn = tk.Button(
            self.control_frame, text="PAUSE", command=self._toggle_rotation_pause, **btn_cfg
        )
        self.pause_btn.grid(row=0, column=4, padx=5, pady=9, sticky="w")

        self.fullscreen_btn = tk.Button(
            self.control_frame, text="FULL", command=self._toggle_fullscreen, **btn_cfg
        )
        self.fullscreen_btn.grid(row=0, column=5, padx=5, pady=9, sticky="w")

        # 強制重新整理 API
        refresh_btn = tk.Button(
            self.control_frame, text="REFRESH", command=self._manual_refresh, **btn_cfg
        )
        refresh_btn.grid(row=0, column=6, padx=5, pady=9, sticky="w")

        self.search_var = tk.StringVar(value=Config.CITY)
        search_label = tk.Label(
            self.control_frame, text="CITY:",
            bg="#070A08", fg=Config.TEXT_ORANGE,
            font=(Config.FONT_FAMILY, 9, "bold")
        )
        search_label.grid(row=0, column=7, padx=(10, 4), pady=9, sticky="e")

        self.search_entry = tk.Entry(
            self.control_frame,
            textvariable=self.search_var,
            bg="#071016", fg=Config.TEXT_WHITE,
            insertbackground=Config.TEXT_YELLOW,
            highlightthickness=1,
            highlightbackground=Config.BORDER_COL,
            highlightcolor=Config.TEXT_CYAN,
            relief="flat",
            font=(Config.FONT_FAMILY, 9, "bold"),
            width=16,
        )
        self.search_entry.grid(row=0, column=8, padx=4, pady=9, sticky="w")
        self.search_entry.bind("<Return>", lambda _e: self._search_city())

        search_btn = tk.Button(
            self.control_frame, text="GO", command=self._search_city, **btn_cfg
        )
        search_btn.grid(row=0, column=9, padx=(4, 10), pady=9, sticky="w")

        # 看板名稱指示器
        self.slide_label = tk.Label(
            self.control_frame, text="",
            bg="#070A08", fg=Config.TEXT_CYAN,
            font=(Config.FONT_FAMILY, 8, "bold"),
            width=7,
            anchor="e"
        )
        self.slide_label.grid(row=0, column=10, padx=(6, 18), pady=9, sticky="e")
        self.control_frame.grid_columnconfigure(10, weight=1)

    # ── 真實載入進度 ──────────────────────────────────────────
    def _make_loading_progress_callback(self):
        """Return a thread-safe callback for real data-loading progress."""
        def _progress(percent: int, status: str):
            self.root.after(0, lambda p=percent, s=status: self._set_loading_progress(p, s))
        return _progress

    def _set_loading_progress(self, percent: int, status: str):
        """Draw progress tied to search/fetch stages, not the slide timer."""
        if self.loading_clear_after_id:
            self.root.after_cancel(self.loading_clear_after_id)
            self.loading_clear_after_id = None
        self.loading_active = True
        self.loading_percent = max(0, min(100, int(percent)))
        self.loading_status = status
        self._draw_loading_progress()
        if self.loading_percent >= 100:
            self.loading_clear_after_id = self.root.after(900, self._clear_loading_progress)

    def _clear_loading_progress(self):
        self.loading_active = False
        self.loading_clear_after_id = None
        if hasattr(self, "canvas"):
            self.canvas.delete("load_progress")

    def _draw_loading_progress(self):
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("load_progress")
        canvas_h = self._canvas_height()
        x1, x2 = 92, Config.WIN_WIDTH - 92
        y1 = 420 if not self.app_started else canvas_h - 58
        y2 = y1 + 42
        pct = self.loading_percent
        status = self.loading_status or "PROCESSING"
        is_error = any(word in status.upper() for word in ("FAILED", "ERROR"))
        outline = Config.TEXT_RED if is_error else (Config.TEXT_CYAN if pct < 100 else Config.TEXT_GREEN)
        bar_x1, bar_y1 = x1 + 18, y1 + 24
        bar_x2, bar_y2 = x2 - 18, y1 + 34
        fill_w = int((bar_x2 - bar_x1) * pct / 100)

        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill="#091015", outline=outline,
            width=2, tags="load_progress"
        )
        self.canvas.create_text(
            x1 + 18, y1 + 13,
            text=status.upper(),
            fill=Config.TEXT_YELLOW,
            font=(Config.FONT_FAMILY, 9, "bold"),
            anchor="w", tags="load_progress"
        )
        self.canvas.create_text(
            x2 - 18, y1 + 13,
            text=f"{pct:03d}%",
            fill=Config.TEXT_WHITE,
            font=(Config.FONT_FAMILY, 9, "bold"),
            anchor="e", tags="load_progress"
        )
        self.canvas.create_rectangle(
            bar_x1, bar_y1, bar_x2, bar_y2,
            fill="#061015", outline="#24414A", width=1, tags="load_progress"
        )
        if fill_w > 0:
            color = Config.TEXT_RED if is_error else (Config.TEXT_GREEN if pct >= 100 else Config.TEXT_CYAN)
            self.canvas.create_rectangle(
                bar_x1, bar_y1, bar_x1 + fill_w, bar_y2,
                fill=color, outline="", tags="load_progress"
            )
        self.canvas.tag_raise("load_progress")

    # ── 進度條設定 ────────────────────────────────────────────
    def _setup_progress_bar(self):
        """底部進度條，顯示距離下次切換的剩餘時間"""
        pb_y = Config.WIN_HEIGHT - Config.MARQUEE_HEIGHT - Config.CONTROL_HEIGHT - 6
        self.pb_bg = self.canvas.create_rectangle(
            0, self._scaled(pb_y), self._scaled(Config.WIN_WIDTH), self._scaled(pb_y + 4),
            fill=Config.BG_PANEL, outline="", tags="progress"
        )
        self.pb_fg = self.canvas.create_rectangle(
            0, self._scaled(pb_y), 0, self._scaled(pb_y + 4),
            fill=Config.TEXT_CYAN, outline="", tags="progress"
        )
        self.canvas.addtag_withtag("display_scaled", self.pb_bg)
        self.canvas.addtag_withtag("display_scaled", self.pb_fg)
        self.pb_start  = time.time()
        self._update_progress_bar()

    def _update_progress_bar(self):
        """更新進度條動畫"""
        if self.rotation_paused:
            self.canvas.itemconfig(self.pb_fg, fill=Config.TEXT_GREEN)
            self.root.after(100, self._update_progress_bar)
            return
        elapsed = time.time() - self.pb_start
        ratio   = min(elapsed / Config.SLIDE_INTERVAL, 1.0)
        pb_w    = int(Config.WIN_WIDTH * ratio * self.display_scale)
        pb_y    = Config.WIN_HEIGHT - Config.MARQUEE_HEIGHT - Config.CONTROL_HEIGHT - 6
        self.canvas.coords(self.pb_fg, 0, self._scaled(pb_y), pb_w, self._scaled(pb_y + 4))
        # 顏色隨進度漸變：青→黃→橙
        if ratio < 0.5:
            col = Config.TEXT_CYAN
        elif ratio < 0.8:
            col = Config.TEXT_YELLOW
        else:
            col = Config.TEXT_ORANGE
        self.canvas.itemconfig(self.pb_fg, fill=col)
        self.root.after(100, self._update_progress_bar)

    # ── 看板渲染器初始化 ──────────────────────────────────────
    def _setup_slide_renderers(self):
        self.renderers = {
            "current"     : CurrentWeatherSlide(self.canvas, Config),
            "summary"     : AIWeatherSummarySlide(self.canvas, Config),
            "hourly"      : HourlyTimelineSlide(self.canvas, Config),
            "ad"          : CorporateAdSlide(self.canvas, Config),
            "comparison"  : CityComparisonSlide(self.canvas, Config),
            "observations": LocalObservationsSlide(self.canvas, Config),
            "forecast"    : ForecastSlide(self.canvas, Config),
            "radar"       : RadarSlide(self.canvas, Config),
            "credits"      : CreditsSlide(self.canvas, Config),
        }

    # ── 看板顯示邏輯 ──────────────────────────────────────────
    def show_slide(self, idx: int):
        """切換到指定索引的看板"""
        # 停止雷達動畫（若正在執行）
        if hasattr(self, 'renderers'):
            self.renderers["radar"].stop()
        self.canvas.unbind("<MouseWheel>")
        self.canvas.unbind("<Button-4>")
        self.canvas.unbind("<Button-5>")

        self.current_slide = idx % len(self.SLIDES)
        slide_key = self.SLIDES[self.current_slide]

        # 更新看板指示標籤
        total = len(self.SLIDES)
        self.slide_label.config(
            text=f"{self.current_slide+1}/{total}"
        )

        # 取得資料並渲染
        with self.data_manager._lock:
            current  = dict(self.data_manager.current)
            forecast = list(self.data_manager.forecast)
            hourly   = list(self.data_manager.hourly)
            comparison = list(self.data_manager.comparison)

        renderer = self.renderers[slide_key]
        if slide_key == "current":
            renderer.render(current)
        elif slide_key == "summary":
            renderer.render(current)
            renderer.bind_scroll()
        elif slide_key == "hourly":
            renderer.render(hourly, current)
        elif slide_key == "ad":
            renderer.render()
        elif slide_key == "comparison":
            renderer.render(comparison)
        elif slide_key == "observations":
            renderer.render(current)
        elif slide_key == "forecast":
            renderer.render(forecast)
        elif slide_key == "radar":
            renderer.render(current)
        elif slide_key == "credits":
            renderer.render()

        self._draw_live_clock()
        self._play_transition_effect()
        # Keep progress visible without putting CRT texture over text.
        self.canvas.tag_raise("progress")
        if self.loading_active:
            self._draw_loading_progress()
        self._scale_canvas_items_for_display()

        # 重置進度條
        self.pb_start = time.time()

        if self._did_initial_announce:
            self.audio.announce(self._announcement_for(slide_key, current), "slide")
        else:
            self._did_initial_announce = True

    def _play_transition_effect(self):
        """Short retro terminal glitch/wipe between boards."""
        if not getattr(self, "app_started", False):
            return
        self.canvas.delete("transition")
        self._terminal_transition_step(0)
        self.root.after(260, lambda: self.canvas.delete("transition"))

    def _terminal_transition_step(self, step: int):
        """Natural CRT terminal signal lock transition."""
        if step > 9:
            self.canvas.delete("transition_step")
            return
        h = Config.WIN_HEIGHT - Config.MARQUEE_HEIGHT - Config.CONTROL_HEIGHT
        bezel = Config.BEZEL_SIZE + 8
        self.canvas.delete("transition_step")
        pulse_w = int((Config.WIN_WIDTH - bezel * 2) * (step + 1) / 10)
        left = Config.WIN_WIDTH // 2 - pulse_w // 2
        right = Config.WIN_WIDTH // 2 + pulse_w // 2
        colors = ["#17382E", "#255A49", "#D7B45F"]

        for offset, color in ((0, colors[step % 3]), (h - 28, "#17382E")):
            self.canvas.create_rectangle(
                max(bezel, left), 26 + offset, min(Config.WIN_WIDTH - bezel, right), 29 + offset,
                fill=color, outline="", stipple="gray75",
                tags=("transition", "transition_step")
            )

        # Small terminal raster slips, aligned to the screen edges.
        for i in range(3):
            y = 70 + ((step * 31 + i * 83) % max(1, h - 140))
            side_left = i % 2 == 0
            x1 = bezel if side_left else Config.WIN_WIDTH - bezel - 112
            self.canvas.create_rectangle(
                x1, y, x1 + 112, y + 2,
                fill=colors[(step + i) % len(colors)], outline="", stipple="gray75",
                tags=("transition", "transition_step")
            )

        # A thin phosphor gate closes and opens around the center line.
        gate = max(4, 32 - step * 3)
        self.canvas.create_rectangle(
            bezel, h // 2 - gate, Config.WIN_WIDTH - bezel, h // 2 + gate,
            fill="#0E1E18", outline="", stipple="gray75",
            tags=("transition", "transition_step")
        )
        self.canvas.tag_raise("transition")
        self.root.after(22, lambda: self._terminal_transition_step(step + 1))

    def _schedule_next_slide(self):
        """排程下一次自動換頁"""
        if self.slide_after_id:
            self.root.after_cancel(self.slide_after_id)
            self.slide_after_id = None
        if self.rotation_paused:
            return
        self.slide_after_id = self.root.after(
            Config.SLIDE_INTERVAL * 1000,
            self._auto_next_slide
        )

    def _auto_next_slide(self):
        """自動輪播：切換到下一張"""
        if self.rotation_paused:
            self.slide_after_id = None
            return
        self.show_slide(self.current_slide + 1)
        self._schedule_next_slide()

    def _next_slide(self):
        """手動：下一張"""
        if self.slide_after_id:
            self.root.after_cancel(self.slide_after_id)
            self.slide_after_id = None
        self.show_slide(self.current_slide + 1)
        self._schedule_next_slide()

    def _prev_slide(self):
        """手動：上一張"""
        if self.slide_after_id:
            self.root.after_cancel(self.slide_after_id)
            self.slide_after_id = None
        self.show_slide(self.current_slide - 1)
        self._schedule_next_slide()

    def _toggle_rotation_pause(self):
        """Pause/resume automatic slide rotation for live demos."""
        self.rotation_paused = not self.rotation_paused
        if self.rotation_paused:
            if self.slide_after_id:
                self.root.after_cancel(self.slide_after_id)
                self.slide_after_id = None
            self.pause_btn.config(text="RESUME")
            self.slide_label.config(text="PAUSED")
            self.audio.announce("Slide rotation paused.", "enable")
        else:
            self.pause_btn.config(text="PAUSE")
            self.slide_label.config(text=f"{self.current_slide+1}/{len(self.SLIDES)}")
            self._schedule_next_slide()
            self.audio.announce("Slide rotation resumed.", "enable")

    def _toggle_fullscreen(self):
        """Toggle fullscreen display mode for classroom demos."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            self.display_scale = max(1.0, min(screen_w / Config.WIN_WIDTH, screen_h / Config.WIN_HEIGHT))
            self.root.attributes("-fullscreen", True)
        else:
            self.display_scale = 1.0
            self.root.attributes("-fullscreen", False)
            self.root.geometry(f"{Config.WIN_WIDTH}x{Config.WIN_HEIGHT}")
        self._configure_scaled_layout()
        if hasattr(self, "fullscreen_btn"):
            self.fullscreen_btn.config(text="WINDOW" if self.is_fullscreen else "FULL")
        if getattr(self, "app_started", False):
            self.canvas.delete("display_scaled")
            self._setup_progress_bar()
            self.show_slide(self.current_slide)
        self.audio.announce(
            "Fullscreen enabled." if self.is_fullscreen else "Windowed mode enabled.",
            "enable"
        )

    # ── 時鐘更新 ──────────────────────────────────────────────
    def _update_clock(self):
        """每秒重繪標題列的時鐘（讓時間實時更新）"""
        if self.app_started:
            self._draw_live_clock()
        self.clock_after_id = self.root.after(1000, self._update_clock)

    def _draw_live_clock(self):
        """Redraw only the clock text so time keeps moving between slides."""
        if not hasattr(self, "canvas"):
            return
        self.canvas.delete("clock_text")
        now = datetime.datetime.now().strftime("%H:%M:%S")
        date_str = datetime.datetime.now().strftime("%Y/%m/%d")
        self.canvas.create_text(
            Config.WIN_WIDTH - 34, 36,
            text=now, fill=Config.TEXT_WHITE,
            font=(Config.FONT_FAMILY, 12, "bold"), anchor="e",
            tags=("clock_text", "slide_content")
        )
        self.canvas.create_text(
            Config.WIN_WIDTH - 34, 54,
            text=date_str, fill=Config.TEXT_CYAN,
            font=(Config.FONT_FAMILY, 10), anchor="e",
            tags=("clock_text", "slide_content")
        )
        self.canvas.tag_raise("clock_text")
        self._scale_canvas_items_for_display()

    # ── API 資料更新 ──────────────────────────────────────────
    def _on_data_refreshed(self, success: bool):
        """API 更新完成的回調（在背景執行緒呼叫，需透過 after 回主執行緒）"""
        def _ui_update():
            self._set_loading_progress(100, "BROADCAST DATA READY")
            # 若資料有錯誤訊息，更新跑馬燈
            if self.data_manager.error_msg:
                self.marquee_messages.insert(0, ("halcyon", f"WARN: {self.data_manager.error_msg}"))
                self._refresh_marquee_text()
                self.audio.announce("Weather feed degraded. Synthetic data online.", "alert")
            else:
                self.audio.announce("Weather data feed updated.", "refresh")
                with self.data_manager._lock:
                    alert = dict(self.data_manager.current.get("alert", {}))
                if alert:
                    self.marquee_messages.insert(
                        0,
                        ("halcyon", f"CORPORATE ALERT {alert.get('level','CLEAR')}: {alert.get('message','Operational tolerance nominal.')}")
                    )
                    self._refresh_marquee_text()
            # 重新渲染當前看板以顯示最新資料
            if self._reset_to_first_after_refresh:
                self._reset_to_first_after_refresh = False
                if self.slide_after_id:
                    self.root.after_cancel(self.slide_after_id)
                self.show_slide(0)
                self._schedule_next_slide()
            else:
                self.show_slide(self.current_slide)
                if not self.rotation_paused and not self.slide_after_id:
                    self._schedule_next_slide()

        self.root.after(0, _ui_update)  # 確保在主執行緒執行 UI 更新

    def _manual_refresh(self):
        """手動觸發 API 資料更新"""
        self.audio.announce("Refreshing weather data feed.", "refresh")
        self._set_loading_progress(8, "MANUAL REFRESH REQUESTED")
        self.data_manager.refresh_async(
            callback=self._on_data_refreshed,
            progress_callback=self._make_loading_progress_callback(),
        )

    def _schedule_api_refresh(self):
        """定期重新整理 API（每 Config.API_REFRESH 秒）"""
        def _refresh_and_reschedule():
            self.data_manager.refresh_async(
                callback=self._on_data_refreshed,
                progress_callback=self._make_loading_progress_callback(),
            )
            # 再次排程
            self.api_after_id = self.root.after(Config.API_REFRESH * 1000, _refresh_and_reschedule)

        self.api_after_id = self.root.after(Config.API_REFRESH * 1000, _refresh_and_reschedule)

    def _search_city(self):
        """Search a city through Open-Meteo Geocoding, then refresh weather."""
        query = self.search_var.get().strip()
        if not query:
            return
        self.audio.announce(f"Searching weather station for {query}.", "refresh")
        self.slide_label.config(text="SCAN")
        self._set_loading_progress(8, "CITY SEARCH REQUESTED")
        self._request_city_selection(
            query,
            self._lock_city_from_toolbar,
            progress_callback=self._make_loading_progress_callback(),
        )

    def _lock_city_from_toolbar(self, place: dict):
        self.data_manager.set_location(
            place["city"], place["country"], place["lat"], place["lon"]
        )
        if hasattr(self, "renderers") and "radar" in self.renderers:
            self.renderers["radar"].clear_location_cache()
        self.search_var.set(f"{place['city']}")
        self.marquee_messages.insert(
            0,
            ("order", f"STATION LOCKED: {place['city']}, {place['country']} "
             f"({place['lat']:.2f}, {place['lon']:.2f})")
        )
        self._refresh_marquee_text()
        self.audio.announce(
            f"Station locked. {place['city']}, {place['country']}.",
            "enable"
        )
        self._reset_to_first_after_refresh = True
        self._set_loading_progress(38, f"STATION LOCKED: {place['city']}")
        self.data_manager.refresh_async(
            callback=self._on_data_refreshed,
            progress_callback=self._make_loading_progress_callback(),
        )

    # ── 音效控制 ──────────────────────────────────────────────
    def _toggle_audio(self):
        is_playing = self.audio.toggle()
        Config.MUSIC_ENABLED = is_playing
        Config.save_to_json()
        self.audio_btn.config(text="MUSIC" if is_playing else "MUSIC OFF")

    def _toggle_sfx(self):
        sfx_on = self.audio.toggle_sfx()
        Config.SFX_ENABLED = sfx_on
        Config.save_to_json()
        self.sfx_btn.config(text="SFX" if sfx_on else "SFX OFF")

    def _announcement_for(self, slide_key: str, current: dict) -> str:
        city = current.get("city", Config.CITY) if current else Config.CITY
        temp = current.get("temp", "--") if current else "--"
        messages = {
            "current": f"Current conditions for {city}. Temperature {temp} degrees.",
            "summary": "Corporate weather brief is now on screen.",
            "ad": "Sponsored corporate message.",
            "observations": "Regional observation table is now on screen.",
            "forecast": "Extended forecast display.",
            "radar": "Simulated radar sweep is now active.",
            "credits": "System credits and data sources.",
        }
        return messages.get(slide_key, "Weather display updated.")

    # ── 啟動與結束 ────────────────────────────────────────────
    def run(self):
        """啟動主事件迴圈"""
        self.root.mainloop()

    def quit(self):
        """優雅地結束程式（清理所有資源）"""
        # 停止所有排程
        if self.slide_after_id:
            self.root.after_cancel(self.slide_after_id)
        if self.clock_after_id:
            self.root.after_cancel(self.clock_after_id)
        if self.api_after_id:
            self.root.after_cancel(self.api_after_id)
        if self.crt_after_id:
            self.root.after_cancel(self.crt_after_id)
        if self.marquee_after_id:
            self.root.after_cancel(self.marquee_after_id)
        self._close_city_choice_dialog()
        # 停止雷達動畫
        if hasattr(self, 'renderers'):
            self.renderers["radar"].stop()
        # 清理音效
        self.audio.stop()
        self.audio.cleanup()
        # 關閉視窗
        self.root.destroy()


# ════════════════════════════════════════════════════════════════
#  程式進入點
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  Arcadia 5000 — Halcyon Weather Terminal")
    print("  Press ESC or close the window to exit.")
    print("=" * 60)

    print("  Weather data: Open-Meteo forecast and geocoding APIs")
    print("  No API key required.\n")

    app = RetroCastApp()
    app.run()
