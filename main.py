from playwright.sync_api import sync_playwright

import requests

import re

import time

BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

FROM_STATION = "JB Sentral"

TO_STATION = "Kluang"

DATE = "3 Jul"

TIME_START = "21:00"

TIME_END = "21:20"

def send(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def in_range(t):

    return TIME_START <= t <= TIME_END

def run():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        # -------------------------

        # 1. OPEN KTMB

        # -------------------------

        page.goto("https://online.ktmb.com.my")

        page.wait_for_timeout(5000)

        # -------------------------

        # 2. SET ROUTE

        # -------------------------

        page.fill("input[placeholder*='From']", FROM_STATION)

        page.keyboard.press("Enter")

        page.fill("input[placeholder*='To']", TO_STATION)

        page.keyboard.press("Enter")

        # -------------------------

        # 3. SET DATE

        # -------------------------

        page.click("input[type='date'], input[placeholder*='Date']")

        page.keyboard.type(DATE)

        page.keyboard.press("Enter")

        # -------------------------

        # 4. SEARCH

        # -------------------------

        page.click("button:has-text('Search')")

        page.wait_for_timeout(8000)

        # -------------------------

        # 5. FIND TRAIN CARDS

        # -------------------------

        cards = page.query_selector_all("div")

        found = False

        for card in cards:

            try:

                text = card.inner_text().lower()

                # extract time

                times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

                # REAL SEAT VALIDATION (IMPORTANT)

                has_select_button = card.query_selector("text=Select") is not None

                has_book_button = card.query_selector("text=Book") is not None

                is_available = has_select_button or has_book_button

                for t in times:

                    if in_range(t) and is_available:

                        send(

                            "🚆 KTMB SNIPER ALERT v2\n"

                            f"{FROM_STATION} → {TO_STATION}\n"

                            f"Date: {DATE}\n"

                            f"Time: {t}\n"

                            f"Status: REAL SEAT AVAILABLE"

                        )

                        found = True

            except:

                continue

        if not found:

            print("No valid train matches")

        browser.close()

run()
