he from playwright.sync_api import sync_playwright

import requests

import re

import time

BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

FROM_STATION = "JB Sentral"

TO_STATION = "Kluang"

DATE = "21 May"

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

        # ------------------------

        # LOAD SITE

        # ------------------------

        page.goto("https://online.ktmb.com.my")

        page.wait_for_timeout(5000)

        # ------------------------

        # INPUT FLOW (locked)

        # ------------------------

        page.fill("input[placeholder*='From']", FROM)

        page.keyboard.press("Enter")

        page.fill("input[placeholder*='To']", TO)

        page.keyboard.press("Enter")

        page.click("input[type='date'], input[placeholder*='Date']")

        page.keyboard.type(DATE)

        page.keyboard.press("Enter")

        page.click("button:has-text('Search')")

        # WAIT UNTIL REAL RESULTS EXIST

        page.wait_for_selector("text=Select, text=Book, text=RM", timeout=20000)

        # ------------------------

        # LOCKED EXTRACTION MODE

        # ------------------------

        rows = page.query_selector_all("div")

        seen = set()

        for r in rows:

            try:

                text = r.inner_text().lower()

                # must contain time

                times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

                if not times:

                    continue

                # MUST contain price OR action button

                has_action = (

                    r.query_selector("text=Select") or

                    r.query_selector("text=Book") or

                    "rm" in text

                )

                if not has_action:

                    continue

                for t in times:

                    if in_range(t) and t not in seen:

                        send(

                            "🚆 KTMB v4 LOCKED ALERT\n"

                            f"{FROM} → {TO}\n"

                            f"Date: {DATE}\n"

                            f"Time: {t}\n"

                            f"Status: CONFIRMED AVAILABLE SLOT"

                        )

                        seen.add(t)

            except:

                continue

        browser.close()

run()
