from playwright.sync_api import sync_playwright
import requests
import traceback
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

# STATION SELECT

# ======================

def select_station(page, value, label):

    step(f"👉 Selecting {label}")

    page.keyboard.press("Escape")

    page.wait_for_timeout(500)

    if label == "Origin":

        page.locator("#select2-FromStationId-container").click()

    else:

        page.locator("#select2-ToStationId-container").click()

    page.wait_for_timeout(800)

    page.locator("input.select2-search__field").fill(value)

    page.wait_for_timeout(1200)

    page.locator(".select2-results__option").first.click()

    page.wait_for_timeout(1000)

# ======================

# DATE FIX (IMPORTANT)

# ======================

def select_date(page):

    step("👉 Selecting DATE")

    date_text = f"{TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}"

    # open calendar

    page.locator("#OnwardDate").click(force=True)

    page.wait_for_timeout(1200)

    # click day

    page.click(f"text={TARGET_DATE['day']}")

    page.wait_for_timeout(800)

    # IMPORTANT: force blur so value commits

    page.keyboard.press("Tab")

    page.wait_for_timeout(1000)

    # verify

    val = page.locator("#OnwardDate").input_value()

    step(f"✔ Date selected: {val}")

# ======================

# SEARCH

# ======================

def search(page):

    step("👉 Clicking SEARCH")

    page.click("button:has-text('Search')")

    page.wait_for_load_state("networkidle", timeout=30000)

    page.wait_for_timeout(5000)

    step("✔ Search completed")

# ======================

# SCAN

# ======================

def scan(page):

    step("👉 Scanning results")

    selectors = [

        "table tbody tr",

        ".table tr",

        ".trip",

        ".result",

        "div[class*='trip']",

        "div[class*='result']"

    ]

    rows = None

    for sel in selectors:

        loc = page.locator(sel)

        if loc.count() > 0:

            rows = loc

            step(f"✔ Using selector: {sel}")

            break

    if rows is None:

        step("❌ No results rendered")

        step(page.inner_text("body")[:2000])

        return "❌ NO RESULTS"

    step(f"Rows found: {rows.count()}")

    for i in range(rows.count()):

        text = rows.nth(i).inner_text().lower()

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        seats = re.search(r"(\d+)", text)

        seats = int(seats.group(1)) if seats else 0

        for t in times:

            if in_window(t) and seats > 4:

                return f"🚆 MATCH\nTime: {t}\nSeats: {seats}"

    return "❌ No match"

# ======================

# MAIN

# ======================

def run():

    try:

        step("🚀 BOT STARTED")

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            page = browser.new_page()

            page.goto("https://online.ktmb.com.my")

            page.wait_for_timeout(8000)

            try:

                page.click("text=Accept")

            except:

                pass

            try:

                page.click("text=Book Ticket")

            except:

                pass

            page.wait_for_timeout(5000)

            select_station(page, FROM_STATION, "Origin")

            select_station(page, TO_STATION, "Destination")

            # ✅ DATE (FIXED PROPERLY)

            select_date(page)

            search(page)

            result = scan(page)

            send(result)

            browser.close()

    except Exception:

        send("🔥 CRASH\n" + traceback.format_exc())

run()
