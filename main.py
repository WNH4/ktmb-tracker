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

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# ======================

# TIME CHECK (±15 min)

# ======================

def in_time_window(train_time):

    fmt = "%H:%M"

    t = datetime.strptime(train_time, fmt)

    target = datetime.strptime(TARGET_TIME, fmt)

    return abs((t - target).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# SELECT2 FIX

# ======================

def select_station(page, index, value):

    containers = page.locator(".select2-container")

    containers.nth(index).click(force=True)

    page.wait_for_timeout(1000)

    page.keyboard.type(value)

    page.wait_for_timeout(1200)

    page.keyboard.press("ArrowDown")

    page.keyboard.press("Enter")

# ======================

# DATE SELECT

# ======================

def select_date(page):

    page.locator(".form-control:visible").first.click(force=True)

    page.wait_for_timeout(1500)

    page.click(f"text={TARGET_DATE['day']}", timeout=8000)

# ======================

# PAX

# ======================

def select_pax(page):

    page.click("text=Pax", timeout=10000)

    page.wait_for_timeout(800)

    page.keyboard.type("1")

    page.keyboard.press("ArrowDown")

    page.keyboard.press("Enter")

# ======================

# SEARCH

# ======================

def click_search(page):

    btn = page.locator("button:has-text('Search')")

    btn.wait_for(state="visible", timeout=10000)

    btn.click()

# ======================

# WAIT FOR TABLE

# ======================

def wait_for_trips(page):

    page.wait_for_selector("table", timeout=30000)

    page.wait_for_timeout(5000)

# ======================

# SEAT PARSER

# ======================

def extract_seats(text):

    match = re.search(r"available seats?\s*[:\-]?\s*(\d+)", text.lower())

    return int(match.group(1)) if match else 0

# ======================

# ROW-BASED SCANNER

# ======================

def scan(page):

    rows = page.locator("table tr")

    count = rows.count()

    for i in range(count):

        row = rows.nth(i)

        text = row.inner_text().lower()

        # skip headers

        if "departure" in text and "arrival" in text:

            continue

        # skip locked rows

        if "login to view" in text:

            continue

        # extract departure time

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        seats = extract_seats(text)

        for t in times:

            if in_time_window(t):

                if seats > 4:

                    return {

                        "time": t,

                        "seats": seats,

                        "row": text[:120]

                    }

    return None

# ======================

# MAIN

# ======================

def run():

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        # OPEN SITE

        page.goto("https://online.ktmb.com.my", wait_until="domcontentloaded")

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

        page.wait_for_timeout(4000)

        # ======================

        # FORM FLOW

        # ======================

        select_station(page, 0, FROM_STATION)

        select_station(page, 1, TO_STATION)

        select_date(page)

        select_pax(page)

        page.wait_for_timeout(2000)

        click_search(page)

        # ======================

        # WAIT TABLE

        # ======================

        wait_for_trips(page)

        # ======================

        # SCAN RESULTS

        # ======================

        result = scan(page)

        if result:

            send(

                "🚆 KTMB SNIPER v27 ALERT\n"

                f"{FROM_STATION} → {TO_STATION}\n"

                f"Date: {TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}\n"

                f"Target Time: {TARGET_TIME} ±{TIME_WINDOW_MIN}min\n"

                f"Detected Time: {result['time']}\n"

                f"Available Seats: {result['seats']}\n"

                f"Status: MATCH FOUND\n"

                f"Row: {result['row']}"

            )

        else:

            print("No valid trains found")

        browser.close()

run()
