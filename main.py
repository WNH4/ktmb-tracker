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

# SAFE SCAN (TABLE BASED)

# ======================

def scan(page):

    try:

        tables = page.locator("table")

        if tables.count() == 0:

            return "⚠️ No table found (likely not on results page)"

        rows = page.locator("table tr")

        count = rows.count()

        if count == 0:

            return "⚠️ Table found but no rows"

        for i in range(count):

            row = rows.nth(i)

            text = row.inner_text().lower()

            if "departure" in text and "arrival" in text:

                continue

            if "login to view" in text:

                continue

            # extract time

            times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

            # extract seats (simple)

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

            # ======================

            # OPEN SITE

            # ======================

            page.goto("https://online.ktmb.com.my")

            page.wait_for_timeout(8000)

            # accept popup

            try:

                page.click("text=Accept", timeout=3000)

            except:

                pass

            # go to booking

            try:

                page.click("text=Book Ticket", timeout=5000)

            except:

                pass

            page.wait_for_timeout(5000)

            # ======================

            # DEBUG INFO

            # ======================

            current_url = page.url

            page_text = page.inner_text("body")[:500]

            send(f"📍 URL: {current_url}")

            send(f"🧾 Page Preview:\n{page_text}")

            # ======================

            # TRY SEARCH (fallback only)

            # ======================

            try:

                page.click("button:has-text('Search')", timeout=5000)

                page.wait_for_timeout(8000)

                send("🔍 Search clicked")

            except:

                send("⚠️ Search button not clicked")

            # ======================

            # SCAN

            # ======================

            result = scan(page)

            send(result)

            browser.close()

    except Exception as e:

        send(f"🔥 BOT ERROR\n{str(e)}")

        print("ERROR:", e)

# ======================

# RUN

# ======================

run()

