import requests
import time
from datetime import datetime

# ======================
# CONFIG
# ======================
BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

FROM_STATION = "JB Sentral"
TO_STATION = "Kluang"

FROM_STATION = "JB SENTRAL"

TO_STATION = "KLUANG"

TRAVEL_DATE = "2026-05-21"   # YYYY-MM-DD format (IMPORTANT)

TARGET_TIME = "21:05"

TIME_WINDOW_MIN = 15

BASE_URL = "https://online.ktmb.com.my/api"  # inferred endpoint pattern

# ======================

# TELEGRAM

# ======================

def send(msg):

    try:

        requests.post(

            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",

            data={"chat_id": CHAT_ID, "text": msg}

        )

    except:

        pass

def step(msg):

    print(msg)

    send(msg)

# ======================

# TIME FILTER

# ======================

def in_window(t):

    fmt = "%H:%M"

    a = datetime.strptime(t, fmt)

    b = datetime.strptime(TARGET_TIME, fmt)

    return abs((a - b).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# MAP STATION NAME → ID (YOU MAY NEED ADJUSTMENT ONCE)

# ======================

STATION_MAP = {

    "JB SENTRAL": "41",

    "KLUANG": "45"

}

# ======================

# CORE API CALL (SNIPER MODE)

# ======================

def fetch_trains():

    step("🚀 Fetching KTMB API data (sniper mode)")

    payload = {

        "origin": STATION_MAP[FROM_STATION],

        "destination": STATION_MAP[TO_STATION],

        "date": TRAVEL_DATE,

        "passengers": 1

    }

    headers = {

        "User-Agent": "Mozilla/5.0",

        "Accept": "application/json, text/plain, */*",

        "Referer": "https://online.ktmb.com.my/"

    }

    # ⚠️ This endpoint may differ slightly — adjust if needed

    r = requests.get(

        "https://online.ktmb.com.my/ktmb-api/search",

        params=payload,

        headers=headers,

        timeout=20

    )

    step(f"HTTP STATUS: {r.status_code}")

    if r.status_code != 200:

        return None

    try:

        return r.json()

    except:

        step("❌ Response not JSON")

        return None

# ======================

# PARSE RESULTS

# ======================

def parse(data):

    step("👉 Parsing results")

    if not data:

        return "❌ NO DATA"

    results = data.get("trains", []) or data.get("data", [])

    matches = []

    for t in results:

        try:

            dep = t.get("departure_time")

            seats = int(t.get("available_seats", 0))

            if dep and seats:

                if in_window(dep) and seats > 4:

                    matches.append(f"{dep} | seats: {seats}")

        except:

            continue

    if not matches:

        return "❌ No match"

    return "🚆 MATCH FOUND\n" + "\n".join(matches)

# ======================

# MAIN LOOP (TRACKER MODE)

# ======================

def run():

    step("🔥 KTMB API SNIPER STARTED")

    while True:

        try:

            data = fetch_trains()

            result = parse(data)

            step(result)

            if "MATCH" in result:

                send(result)

            time.sleep(60)  # poll every 60 seconds

        except Exception as e:

            send(f"🔥 ERROR\n{str(e)}")

            time.sleep(30)

run()
