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

# SEAT PARSER

# ======================

def extract_seats(text):

    match = re.search(r"available seats?\s*[:\-]?\s*(\d+)", text.lower())

    return int(match.group(1)) if match else 0

# ======================

# SELECT2 HANDLER

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

# 🔥 TRIP LOADER (FIXED CORE)

# ======================

def wait_for_trips(page):

    # wait for ANY table or trip container

    page.wait_for_selector("table, tr, .trip, .results", timeout=30000)

    # allow JS to finish populating data

    page.wait_for_timeout(5000)

# ======================

# SCANNER (REAL LOGIC)

# ======================

def scan(page):

    text = page.inner_text("body").lower()

    times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

    seats = extract_seats(text)

    for t in times:

        if in_time_window(t):

            if seats > 4:

                return {

                    "time": t,

                    "seats": seats

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

        # FORM

        # ======================

        select_station(page, 0, FROM_STATION)

        select_station(page, 1, TO_STATION)

        select_date(page)

        select_pax(page)

        page.wait_for_timeout(2000)

        click_search(page)

        # ======================

        # 🔥 WAIT FOR REAL TRIPS

        # ======================

        wait_for_trips(page)

        # ======================

        # SCAN

        # ======================

        result = scan(page)

        if result:

            send(

                "🚆 KTMB SNIPER v24 ALERT\n"

                f"{FROM_STATION} → {TO_STATION}\n"

                f"Date: {TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}\n"

                f"Time Window: {TARGET_TIME} ±15 min\n"

                f"Detected Time: {result['time']}\n"

                f"Available Seats: {result['seats']}\n"

                f"Status: MATCH FOUND"

            )

        else:

            print("No valid trips found")

        browser.close()

run()
