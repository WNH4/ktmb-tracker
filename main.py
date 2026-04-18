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

TARGET_DATE = {
    "day": "21",
    "month": "May",
    "year": "2026"
}

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

# SELECT2 (KTMB DROPDOWN FIX)

# ======================

def select_station(page, index, value):

    dropdowns = page.locator(".select2-container")

    dropdowns.nth(index).click()

    page.wait_for_timeout(1200)

    page.keyboard.type(value)

    page.wait_for_timeout(1500)

    page.keyboard.press("ArrowDown")

    page.keyboard.press("Enter")

# ======================

# DATE SELECT (FIXED - NO INPUT CLICKING)

# ======================

def select_date(page, day):

    # click the visible date field (NOT hidden input)

    date_field = page.locator(".form-control:visible").first

    date_field.click()

    page.wait_for_timeout(1500)

    # select day in calendar popup

    page.click(f"text={day}", timeout=8000)

# ======================

# PAX SELECT

# ======================

def select_pax(page, value="1"):

    page.click("text=Pax", timeout=10000)

    page.wait_for_timeout(1200)

    page.keyboard.type(value)

    page.wait_for_timeout(800)

    page.keyboard.press("ArrowDown")

    page.keyboard.press("Enter")

# ======================

# SEARCH BUTTON

# ======================

def click_search(page):

    page.wait_for_timeout(2000)

    btn = page.locator("button:has-text('Search')")

    btn.wait_for(state="visible", timeout=10000)

    btn.click()

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

        # close popup if exists

        try:

            page.click("text=Accept", timeout=3000)

        except:

            pass

        # open booking panel

        try:

            page.click("text=Book Ticket", timeout=5000)

        except:

            pass

        page.wait_for_timeout(4000)

        # ======================

        # FORM FLOW (STRICT ORDER)

        # ======================

        select_station(page, 0, FROM_STATION)

        select_station(page, 1, TO_STATION)

        select_date(page, TARGET_DATE["day"])

        select_pax(page, "1")

        page.wait_for_timeout(2500)

        # ======================

        # SEARCH

        # ======================

        click_search(page)

        # ======================

        # WAIT RESULTS

        # ======================

        page.wait_for_timeout(12000)

        try:

            page.wait_for_selector("text=Select, text=Book", timeout=20000)

        except:

            print("No results loaded")

            browser.close()

            return

        # ======================

        # SCAN RESULTS

        # ======================

        text = page.inner_text("body").lower()

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        found = False

        for t in times:

            if in_range(t):

                if "select" in text or "book" in text or "rm" in text:

                    send(

                        "🚆 KTMB SNIPER v17 ALERT\n"

                        f"{FROM_STATION} → {TO_STATION}\n"

                        f"Date: {TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}\n"

                        f"Pax: 1\n"

                        f"Time: {t}\n"

                        f"Status: AVAILABLE SEAT DETECTED"

                    )

                    found = True

        if not found:

            print("No matching trains found")

        browser.close()

run()
