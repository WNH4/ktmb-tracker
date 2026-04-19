from playwright.sync_api import sync_playwright
import requests
import re
from datetime import datetime

# ======================
# CONFIG
# ======================
BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

FROM_STATION = "JB Sentral"
TO_STATION = "Kluang"

TARGET_DATE = {
    "day": "21",
    "month": "May",
    "year": "2026"
}

TARGET_TIME = "21:05"

TIME_WINDOW_MIN = 15

15

