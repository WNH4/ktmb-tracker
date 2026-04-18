from playwright.sync_api import sync_playwright
import requests
import re

# ======================
# CONFIG
# ======================
BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

FROM_STATION = "JB Sentral"
TO_STATION = "Kluang"
DATE = "21 May"

TIME_START = "21:00"
TIME_END = "21:20"

# ======================

# TELEGRAM

# ======================

def send(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ======================

# TIME CHECK

# ======================

def in_range(t):

    return TIME_START <= t <= TIME_END

# ======================

# SAFE SELECT (REAL USER FLOW)

# ======================

def select_station(page, label_text, value):

    # click field by visible label text

    page.click(f"text={label_text}", timeout=10000)

    page.wait_for_timeout(1500)

    # type station name

    page.keyboard.type(value)

    page.wait_for_timeout(1500)

    # select first suggestion

    page.keyboard.press("ArrowDown")

    page.keyboard.press("Enter")

# ======================

# MAIN

# ======================

def run():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        # ----------------------

        # OPEN KTMB

        # ----------------------

        page.goto("https://online.ktmb.com.my", wait_until="domcontentloaded")

        page.wait_for_timeout(8000)

        # close popup if exists

        try:

            page.click("text=Accept", timeout=3000)

        except:

            pass

        # ----------------------

        # OPEN BOOKING UI

        # ----------------------

        try:

            page.click("text=Book Ticket", timeout=5000)

        except:

            pass

        page.wait_for_timeout(3000)

        # ======================

        # INPUT FLOW (FIXED)

        # ======================

        select_station(page, "From", FROM_STATION)

        select_station(page, "To", TO_STATION)

        # ----------------------

        # DATE

        # ----------------------

        try:

            page.keyboard.type(DATE)

            page.keyboard.press("Enter")

        except:

            pass

        # ----------------------

        # SEARCH

        # ----------------------

        try:

            page.click("button:has-text('Search')")

        except:

            page.keyboard.press("Enter")

        page.wait_for_timeout(12000)

        # wait results

        try:

            page.wait_for_selector("text=Select, text=Book", timeout=20000)

        except:

            print("No results loaded")

            browser.close()

            return

        # ----------------------

        # SCAN RESULTS

        # ----------------------

        text = page.inner_text("body").lower()

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        found = False

        for t in times:

            if in_range(t):

                if "select" in text or "book" in text or "rm" in text:

                    send(

                        "🚆 KTMB SNIPER v6 ALERT\n"

                        f"{FROM_STATION} → {TO_STATION}\n"

                        f"Date: {DATE}\n"

                        f"Time: {t}\n"

                        f"Status: SEAT AVAILABLE"

                    )

                    found = True

        if not found:

            print("No match found")

        browser.close()

run()
