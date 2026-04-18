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

# TIME FILTER

# ======================

def in_range(t):

    return TIME_START <= t <= TIME_END

# ======================

# MAIN BOT

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

        # ----------------------

        # HANDLE POPUPS (if any)

        # ----------------------

        try:

            page.click("text=Accept", timeout=3000)

        except:

            pass

        # ----------------------

        # FROM (dropdown select)

        # ----------------------

        from_input = page.get_by_placeholder("From")

        from_input.click()

        from_input.fill(FROM_STATION)

        page.wait_for_timeout(1500)

        page.keyboard.press("ArrowDown")

        page.keyboard.press("Enter")

        # ----------------------

        # TO (dropdown select)

        # ----------------------

        to_input = page.get_by_placeholder("To")

        to_input.click()

        to_input.fill(TO_STATION)

        page.wait_for_timeout(1500)

        page.keyboard.press("ArrowDown")

        page.keyboard.press("Enter")

        # ----------------------

        # DATE

        # ----------------------

        try:

            date_input = page.locator("input[type='date']")

            date_input.click()

            date_input.fill("2025-07-03")  # safer ISO format

        except:

            page.keyboard.type(DATE)

        # ----------------------

        # SEARCH

        # ----------------------

        page.click("button:has-text('Search')")

        page.wait_for_timeout(10000)

        # wait for results

        page.wait_for_selector("text=Select, text=Book, timeout=20000")

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

                        "🚆 KTMB SNIPER ALERT\n"

                        f"{FROM_STATION} → {TO_STATION}\n"

                        f"Date: {DATE}\n"

                        f"Time: {t}\n"

                        f"Status: AVAILABLE SLOT DETECTED"

                    )

                    found = True

        if not found:

            print("No matching trains found")

        browser.close()

run()
