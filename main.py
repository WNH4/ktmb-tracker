import re
import requests
from playwright.sync_api import sync_playwright

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

URL = "https://online.ktmb.com.my"

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

        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(6000)

        text = page.content().lower()
        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        for t in times:
            if in_range(t):
                if "available" in text or "select" in text:
                    send(f"🚆 KTMB ALERT: Seat found at {t}")

        browser.close()

if __name__ == "__main__":
    run()
