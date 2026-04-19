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

# ======================

# TELEGRAM

# ======================

def send(msg):

    try:

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

    except:

        pass

# ======================

# TIME CHECK

# ======================

def in_time_window(train_time):

    fmt = "%H:%M"

    t = datetime.strptime(train_time, fmt)

    target = datetime.strptime(TARGET_TIME, fmt)

    return abs((t - target).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# SELECT STATION (SELECT2)

# ======================

def select_station(page, index, value):

    try:

        containers = page.locator(".select2-container")

        containers.nth(index).click(force=True)

        page.wait_for_timeout(1000)

        page.keyboard.type(value)

        page.wait_for_timeout(1000)

        page.keyboard.press("ArrowDown")

        page.keyboard.press("Enter")

    except:

        pass

# ======================

# SELECT DATE (CRITICAL FIX)

# ======================

def select_date(page):

    try:

        # click date field

        page.locator("#OnwardDate").click(force=True)

        page.wait_for_timeout(1500)

        # click day in calendar

        page.click(f"text={TARGET_DATE['day']}", timeout=8000)

        send(f"📅 Date selected: {TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}")

    except Exception as e:

        send(f"⚠️ Date selection failed: {str(e)}")

# ======================

# SELECT PAX

# ======================

def select_pax(page):

    try:

        page.click("text=Pax", timeout=5000)

        page.wait_for_timeout(500)

        page.keyboard.type("1")

        page.keyboard.press("ArrowDown")

        page.keyboard.press("Enter")

    except:

        pass

# ======================

# SCAN TABLE

# ======================

def scan(page):

    try:

        tables = page.locator("table")

        if tables.count() == 0:

            return "⚠️ No table found (not on results page)"

        rows = page.locator("table tr")

        count = rows.count()

        for i in range(count):

            row = rows.nth(i)

            text = row.inner_text().lower()

            if "departure" in text and "arrival" in text:

                continue

            if "login to view" in text:

                continue

            times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

            seats_match = re.search(r"(\d+)", text)

            seats = int(seats_match.group(1)) if seats_match else 0

            for t in times:

                if in_time_window(t) and seats > 4:

                    return f"🚆 MATCH FOUND\nTime: {t}\nSeats: {seats}"

        return "❌ No matching trains found"

    except Exception as e:

        return f"❌ Scan error: {str(e)}"

# ======================

# MAIN

# ======================

def run():

    try:

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            page = browser.new_page()

            send("🚀 BOT STARTED")

            # open site

            page.goto("https://online.ktmb.com.my")

            page.wait_for_timeout(8000)

            # popup

            try:

                page.click("text=Accept", timeout=3000)

            except:

                pass

            # booking

            try:

                page.click("text=Book Ticket", timeout=5000)

            except:

                pass

            page.wait_for_timeout(5000)

            # ======================

            # FORM (NOW COMPLETE)

            # ======================

            select_station(page, 0, FROM_STATION)

            select_station(page, 1, TO_STATION)

            select_date(page)

            select_pax(page)

            page.wait_for_timeout(2000)

            # ======================

            # SEARCH

            # ======================

            try:

                page.click("button:has-text('Search')", timeout=5000)

                page.wait_for_timeout(8000)

                send("🔍 Search triggered")

            except:

                send("⚠️ Search click failed")

            # ======================

            # SCAN

            # ======================

            result = scan(page)

            send(result)

            browser.close()

    except Exception as e:

        send(f"🔥 BOT ERROR\n{str(e)}")

# ======================

# RUN

# ======================

run()
