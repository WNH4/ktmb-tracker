from playwright.sync_api import sync_playwright
import requests
import traceback
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

        requests.post(

            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",

            data={"chat_id": CHAT_ID, "text": msg}

        )

    except:

        pass

def step(msg):

    print(msg)

    send(msg)

# ======================

# TIME CHECK

# ======================

def in_window(t):

    fmt = "%H:%M"

    a = datetime.strptime(t, fmt)

    b = datetime.strptime(TARGET_TIME, fmt)

    return abs((a - b).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# SELECT2 FIX (FINAL STABLE)

# ======================

def select_station(page, value, label):

    step(f"👉 Selecting {label}")

    # reset stale dropdown state

    page.keyboard.press("Escape")

    page.wait_for_timeout(500)

    # open correct dropdown

    if label == "Origin":

        page.locator("#select2-FromStationId-container").click()

    else:

        page.locator("#select2-ToStationId-container").click()

    page.wait_for_timeout(800)

    # type into active select2 search box

    search = page.locator("input.select2-search__field")

    search.fill(value)

    page.wait_for_timeout(1200)

    # wait results

    page.wait_for_selector(".select2-results__option", timeout=5000)

    # select first match

    page.locator(".select2-results__option").first.click()

    page.wait_for_timeout(1200)

    # verify backend value

    try:

        if label == "Origin":

            val = page.locator("#FromStationId").input_value()

        else:

            val = page.locator("#ToStationId").input_value()

        step(f"✔ {label} confirmed: {val}")

    except:

        step(f"⚠️ {label} verification failed")

# ======================

# DATE SELECTION (COMMIT SAFE)

# ======================

def select_date(page):

    step("👉 Selecting DATE")

    page.locator("#OnwardDate").click(force=True)

    page.wait_for_timeout(1200)

    page.click(f"text={TARGET_DATE['day']}")

    page.wait_for_timeout(800)

    # force JS commit

    page.keyboard.press("Tab")

    page.wait_for_timeout(1200)

    step(f"✔ Date selected: {TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}")

# ======================

# PAX

# ======================

def select_pax(page):

    step("👉 Selecting PAX")

    try:

        page.click("text=Pax")

        page.wait_for_timeout(500)

        page.keyboard.type("1")

        page.keyboard.press("Enter")

        step("✔ Pax = 1")

    except:

        step("⚠️ Pax skipped")

# ======================

# VALIDATION (REAL BACKEND CHECK)

# ======================

def validate(page):

    step("👉 Validating form")

    try:

        origin = page.locator("#FromStationId").input_value()

        dest = page.locator("#ToStationId").input_value()

    except:

        return False, "Cannot read Select2 values"

    step(f"DEBUG origin: {origin}")

    step(f"DEBUG dest: {dest}")

    if not origin:

        return False, "Origin NOT selected"

    if not dest:

        return False, "Destination NOT selected"

    return True, "OK"

# ======================

# SEARCH (AJAX SAFE)

# ======================

def search(page):

    step("👉 Clicking SEARCH")

    page.click("button:has-text('Search')")

    # wait for ANY rendering state

    page.wait_for_timeout(5000)

    page.wait_for_selector(

        "table, .table, .trip, .result, .results, .container",

        timeout=30000

    )

    step("✔ Search completed (waiting for results render)")

# ======================

# SCAN RESULTS (ROBUST)

# ======================

def scan(page):

    step("👉 Scanning results (multi-mode)")

    page.wait_for_timeout(4000)

    selectors = [

        "table tr",

        ".trip",

        ".result",

        ".results",

        ".table tr"

    ]

    rows = None

    for sel in selectors:

        if page.locator(sel).count() > 0:

            rows = page.locator(sel)

            step(f"✔ Using selector: {sel}")

            break

    if rows is None:

        step("❌ No structured results found → dumping page")

        step(page.inner_text("body")[:2000])

        return "❌ NO RESULTS FOUND"

    n = rows.count()

    step(f"Rows found: {n}")

    for i in range(n):

        text = rows.nth(i).inner_text().lower()

        if "departure" in text:

            continue

        times = re.findall(r"\b([01]\d|2[0-3]):[0-5]\d\b", text)

        seats = re.search(r"(\d+)", text)

        seats = int(seats.group(1)) if seats else 0

        for t in times:

            if in_window(t) and seats > 4:

                return f"🚆 MATCH\nTime: {t}\nSeats: {seats}"

    return "❌ No matching trains"

# ======================

# MAIN

# ======================

def run():

    try:

        step("🚀 BOT STARTED")

        with sync_playwright() as p:

            browser = p.chromium.launch(headless=True)

            page = browser.new_page()

            page.goto("https://online.ktmb.com.my")

            page.wait_for_timeout(8000)

            # popup handling

            try:

                page.click("text=Accept")

            except:

                pass

            # enter booking

            try:

                page.click("text=Book Ticket")

            except:

                pass

            page.wait_for_timeout(5000)

            # FLOW

            select_station(page, FROM_STATION, "Origin")

            select_station(page, TO_STATION, "Destination")

            select_date(page)

            select_pax(page)

            ok, reason = validate(page)

            step(f"✔ VALIDATION: {reason}")

            if not ok:

                send(f"❌ FORM INVALID: {reason}")

                return

            search(page)

            result = scan(page)

            send(result)

            browser.close()

    except Exception:

        send("🔥 CRASH\n" + traceback.format_exc())

run()
