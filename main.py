from playwright.sync_api import sync_playwright

import requests

import re

BOT_TOKEN = "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM"
CHAT_ID = "8240067274"

TIME_START = "21:00"

TIME_END = "21:20"

URL = "https://online.ktmb.com.my"

def send(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def in_range(t):

    return TIME_START <= t <= TIME_END

def run():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        page.goto(URL, wait_until="networkidle")

        page.wait_for_timeout(8000)

        # IMPORTANT: get rendered text (not raw HTML)

        text = page.inner_text("body").lower()

        # extract times properly

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        found = False

        for t in times:

            if in_range(t):

                # better availability detection

                if any(k in text for k in [

                    "available",

                    "select seat",

                    "choose seat",

                    "rm"

                ]):

                    send(f"🚆 KTMB ALERT\nTime: {t}\nStatus: POSSIBLE AVAILABILITY")

                    found = True

        if not found:

            print("No matching trains in window")

        browser.close()

run()
