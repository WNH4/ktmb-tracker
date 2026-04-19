from playwright.sync_api import sync_playwright
import requests
import re
from datetime import datetime
import traceback

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

# ======================

# DEBUG STEP WRAPPER

# ======================

def step(msg):

    print(msg)

    send(msg)

# ======================

# TIME CHECK

# ======================

def in_time_window(train_time):

    fmt = "%H:%M"

    t = datetime.strptime(train_time, fmt)

    target = datetime.strptime(TARGET_TIME, fmt)

    return abs((t - target).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# STEP 1: SELECT STATION

# ======================

def select_station(page, index, value, label):

    step(f"👉 STEP: Selecting {label}")

    containers = page.locator(".select2-container")

    containers.nth(index).click(force=True)

    page.wait_for_timeout(1000)

    page.keyboard.type(value)

    page.wait_for_timeout(1200)

    page.keyboard.press("ArrowDown")

    page.keyboard.press("Enter")

    step(f"✔ {label} selected: {value}")

# ======================

# STEP 2: DATE

# ======================

def select_date(page):

    step("👉 STEP: Selecting DATE")

    page.locator("#OnwardDate").click(force=True)

    page.wait_for_timeout(1500)

    page.click(f"text={TARGET_DATE['day']}", timeout=8000)

    page.keyboard.press("Tab")  # FORCE JS COMMIT

    page.wait_for_timeout(1000)

    step(f"✔ Date selected: {TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}")

# ======================

# STEP 3: PAX

# ======================

def select_pax(page):

    step("👉 STEP: Selecting PAX")

    try:

        page.click("text=Pax", timeout=5000)

        page.wait_for_timeout(500)

        page.keyboard.type("1")

        page.keyboard.press("Enter")

        step("✔ Pax selected: 1")

    except:

        step("⚠️ Pax selection failed (ignored)")

# ======================

# STEP 4: SEARCH

# ======================

def click_search(page):

    step("👉 STEP: Clicking SEARCH")

    page.click("button:has-text('Search')")

    page.wait_for_timeout(12000)  # IMPORTANT: allow backend load

    step("✔ Search clicked + waiting done")

# ======================

# STEP 5: VERIFY PAGE

# ======================

def verify_page(page):

    step("👉 STEP: Verifying results page")

    url = page.url

    step(f"📍 URL: {url}")

    body = page.inner_text("body")[:800]

    step(f"🧾 PAGE SNAPSHOT:\n{body}")

    tables = page.locator("table").count()

    step(f"📊 Tables found: {tables}")

    return tables > 0

# ======================

# STEP 6: SCAN TABLE

# ======================

def scan(page):

    step("👉 STEP: Scanning results")

    rows = page.locator("table tr")

    count = rows.count()

    step(f"Rows found: {count}")

    for i in range(count):

        text = rows.nth(i).inner_text().lower()

        if "departure" in text and "arrival" in text:

            continue

        if "login to view" in text:

            continue

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        seats = re.search(r"(\d+)", text)

        seats = int(seats.group(1)) if seats else 0

        for t in times:

            if in_time_window(t) and seats > 4:

                return f"🚆 MATCH\nTime: {t}\nSeats: {seats}"

    return "❌ No match found"

# ======================

# MAIN

# ======================

def run():

    try:

        step("🚀 BOT STARTED")

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            page = browser.new_page()

            # OPEN SITE

            step("👉 Opening KTMB site")

            page.goto("https://online.ktmb.com.my")

            page.wait_for_timeout(8000)

            # POPUP

            try:

                page.click("text=Accept")

                step("✔ Popup accepted")

            except:

                step("ℹ️ No popup")

            # BOOKING

            try:

                page.click("text=Book Ticket")

                step("✔ Booking page opened")

            except:

                step("⚠️ Booking click failed")

            page.wait_for_timeout(5000)

            # ======================

            # FORM FLOW

            # ======================

            select_station(page, 0, FROM_STATION, "Origin")

            select_station(page, 1, TO_STATION, "Destination")

            select_date(page)

            select_pax(page)

            # ======================

            # SEARCH

            # ======================

            click_search(page)

            # ======================

            # VERIFY

            # ======================

            if not verify_page(page):

                send("❌ NO TABLE FOUND → search failed")

                browser.close()

                return

            # ======================

            # SCAN

            # ======================

            result = scan(page)

            send(result)

            browser.close()

    except Exception as e:

        error = traceback.format_exc()

        send(f"🔥 CRASH\n{str(e)}")

        print(error)

run()
