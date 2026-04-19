import requests

# ======================
# CONFIG
# ======================
BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

FROM_STATION = "JB SENTRAL"

TO_STATION = "KLUANG"

TRAVEL_DATE = "2026-05-21"

TARGET_TIME = "21:05"

TIME_WINDOW_MIN = 15

SEARCH_URL = "https://online.ktmb.com.my/ktmb-api/search"

def send(msg: str) -> None:

    try:

        requests.post(

            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",

            data={"chat_id": CHAT_ID, "text": msg},

            timeout=20,

        )

    except Exception:

        pass

def run():

    try:

        send("🚀 KTMB diagnostic started")

        payload = {

            "origin": "41",

            "destination": "45",

            "date": TRAVEL_DATE,

            "passengers": 1,

        }

        headers = {

            "User-Agent": "Mozilla/5.0",

            "Accept": "application/json, text/plain, */*",

            "Referer": "https://online.ktmb.com.my/",

        }

        r = requests.get(

            SEARCH_URL,

            params=payload,

            headers=headers,

            timeout=20,

        )

        msg = (

            f"HTTP STATUS: {r.status_code}\n"

            f"URL: {r.url}\n\n"

        )

        if r.status_code == 404:

            msg += (

                "❌ The current script is using a guessed KTMB endpoint.\n"

                "It is not a real public API endpoint.\n"

                "This repo cannot become a working tracker until the real browser request is captured."

            )

        else:

            msg += f"Response preview:\n{r.text[:800]}"

        send(msg)

    except Exception as e:

        send(f"🔥 ERROR\n{str(e)}")

run()
