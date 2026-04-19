import requests
from datetime import datetime

# ======================
# CONFIG
# ======================
BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

FROM_STATION = "JB SENTRAL"

TO_STATION = "KLUANG"

TRAVEL_DATE = "2026-05-21"   # YYYY-MM-DD

TARGET_TIME = "21:05"

TIME_WINDOW_MIN = 15

STATION_MAP = {

    "JB SENTRAL": "41",

    "KLUANG": "45",

}

# this endpoint was previously guessed and returned 404

SEARCH_URL = "https://online.ktmb.com.my/ktmb-api/search"

# ======================

# TELEGRAM

# ======================

def send(msg: str) -> None:

    try:

        requests.post(

            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",

            data={"chat_id": CHAT_ID, "text": msg},

            timeout=20,

        )

    except Exception:

        pass

def step(msg: str) -> None:

    print(msg)

    send(msg)

# ======================

# TIME FILTER

# ======================

def in_window(t: str) -> bool:

    fmt = "%H:%M"

    a = datetime.strptime(t, fmt)

    b = datetime.strptime(TARGET_TIME, fmt)

    return abs((a - b).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# FETCH

# ======================

def fetch_trains():

    payload = {

        "origin": STATION_MAP[FROM_STATION],

        "destination": STATION_MAP[TO_STATION],

        "date": TRAVEL_DATE,

        "passengers": 1,

    }

    headers = {

        "User-Agent": "Mozilla/5.0",

        "Accept": "application/json, text/plain, */*",

        "Referer": "https://online.ktmb.com.my/",

    }

    step("🚀 KTMB diagnostic started")

    step(f"Route: {FROM_STATION} → {TO_STATION}")

    step(f"Date: {TRAVEL_DATE}")

    step(f"Target time: {TARGET_TIME} ± {TIME_WINDOW_MIN} min")

    r = requests.get(

        SEARCH_URL,

        params=payload,

        headers=headers,

        timeout=20,

    )

    step(f"HTTP STATUS: {r.status_code}")

    step(f"FINAL URL: {r.url}")

    return r

# ======================

# PARSE

# ======================

def parse_response(r: requests.Response) -> str:

    if r.status_code == 404:

        return (

            "❌ Endpoint returned 404.\n"

            "This means the current script is calling a guessed KTMB endpoint, not a real public API.\n"

            "This tracker will not work until the real request is captured."

        )

    if r.status_code != 200:

        return f"❌ Unexpected HTTP status: {r.status_code}"

    content_type = r.headers.get("content-type", "").lower()

    if "json" in content_type:

        try:

            data = r.json()

        except Exception as e:

            return f"❌ Response claimed JSON but could not parse: {e}"

        return f"ℹ️ JSON received.\nTop-level keys: {list(data)[:10]}"

    text = r.text[:1200]

    return (

        "ℹ️ Non-JSON response received.\n"

        f"Content-Type: {content_type or 'unknown'}\n\n"

        f"Body preview:\n{text}"

    )

# ======================

# MAIN

# ======================

def run():

    try:

        response = fetch_trains()

        result = parse_response(response)

        step(result)

    except Exception as e:

        step(f"🔥 ERROR\n{str(e)}")

run()
