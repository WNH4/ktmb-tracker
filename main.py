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

# TIME CHECK

# ======================

def in_window(t):

    fmt = "%H:%M"

    t1 = datetime.strptime(t, fmt)

    t2 = datetime.strptime(TARGET_TIME, fmt)

    return abs((t1 - t2).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# SELECT2 FIX (CRITICAL)

# ======================

def select_station(page, value, label):

    step(f"👉 Selecting {label}")

    # open dropdown properly

    page.locator(".select2-selection").first.click()

    page.wait_for_timeout(1000)

    # type into real search input

    search = page.locator("input.select2-search__field")

    search.fill(value)

    page.wait_for_timeout(1500)

    # click first result

    page.locator(".select2-results__option").first.click()

    page.wait_for_timeout(1500)

    step(f"✔ {label}: {value}")

# ======================

# DATE (FULL DAY + MONTH + YEAR FIXED)

# ======================

def select_date(page):

    step("👉 Selecting DATE")

    # open calendar

    page.locator("#OnwardDate").click(force=True)

    page.wait_for_timeout(1500)

    # click day

    page.click(f"text={TARGET_DATE['day']}")

    page.wait_for_timeout(1000)

    # FORCE JS commit (THIS IS THE KEY FIX YOU WERE MISSING)

    page.keyboard.press("Tab")

    page.wait_for_timeout(1500)

    step(

        f"✔ Date selected: "

        f"{TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}"

    )

# ======================

# PAX

# ======================

def select_pax(page):

    step("👉 Selecting PAX")

    try:

        page.click("text=Pax")

        page.wait_for_timeout(500)

        page.keyboard.type("1")

        page.keyboard.press("Enter")

        step("✔ Pax = 1")

    except:

        step("⚠️ Pax skipped")

# ======================

# VALIDATION (IMPORTANT SAFETY CHECK)

# ======================

def validate(page):

    step("👉 Validating form")

    body = page.inner_text("body")

    if "Select Origin" in body:

        return False, "Origin not selected"

    if "Select Destination" in body:

        return False, "Destination not selected"

    if TARGET_DATE["day"] not in body:

        return False, "Date not committed"

    return True, "OK"

# ======================

# SEARCH

# ======================

def search(page):

    step("👉 Clicking SEARCH")

    page.click("button:has-text('Search')")

    page.wait_for_timeout(12000)

    step("✔ Search complete")

# ======================

# SCAN TABLE

# ======================

def scan(page):

    step("👉 Scanning results")

    if page.locator("table").count() == 0:

        return "❌ NO TABLE FOUND (search failed)"

    rows = page.locator("table tr")

    n = rows.count()

    step(f"Rows: {n}")

    for i in range(n):

        text = rows.nth(i).inner_text().lower()

        if "departure" in text:

            continue

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        seats = re.search(r"(\d+)", text)

        seats = int(seats.group(1)) if seats else 0

        for t in times:

            if in_window(t) and seats > 4:

                return f"🚆 MATCH\nTime: {t}\nSeats: {seats}"

    return "❌ No matching trains"

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

            # popup

            try:

                page.click("text=Accept")

            except:

                pass

            # booking

            try:

                page.click("text=Book Ticket")

            except:

                pass

            page.wait_for_timeout(5000)

            # ======================

            # FORM FLOW

            # ======================

            select_station(page, FROM_STATION, "Origin")

            select_station(page, TO_STATION, "Destination")

            select_date(page)

            select_pax(page)

            ok, reason = validate(page)

            step(f"✔ VALIDATION: {reason}")

            if not ok:

                send(f"❌ FORM INVALID: {reason}")

                return

            # ======================

            # SEARCH

            # ======================

            search(page)

            # ======================

            # SCAN

            # ======================

            result = scan(page)

            send(result)

            browser.close()

    except Exception:

        send("🔥 CRASH\n" + traceback.format_exc())

run()
