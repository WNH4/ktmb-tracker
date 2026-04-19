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

FROM_STATION = "JB SENTRAL"
TO_STATION = "KLUANG"

TARGET_DATE = {
    "day": "30",
    "month": "Apr",
    "year": "2026"
}

TARGET_TIME = "21:05"
TIME_WINDOW_MIN = 15
MIN_SEATS = 5

# ======================

# TELEGRAM

# ======================

def send(msg):

    try:

        requests.post(

            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",

            data={"chat_id": CHAT_ID, "text": msg},

            timeout=20

        )

    except Exception:

        pass

def step(msg):

    print(msg)

    send(msg)

# ======================

# TIME FILTER

# ======================

def in_window(t):

    fmt = "%H:%M"

    a = datetime.strptime(t, fmt)

    b = datetime.strptime(TARGET_TIME, fmt)

    return abs((a - b).total_seconds()) <= TIME_WINDOW_MIN * 60

# ======================

# STATION SELECT

# ======================

def select_station(page, value, label):

    step(f"👉 Selecting {label}")

    page.keyboard.press("Escape")

    page.wait_for_timeout(600)

    if label == "Origin":

        page.locator("#select2-FromStationId-container").click()

    else:

        page.locator("#select2-ToStationId-container").click()

    page.wait_for_timeout(800)

    page.locator("input.select2-search__field").fill(value)

    page.wait_for_timeout(1200)

    page.wait_for_selector(".select2-results__option", timeout=5000)

    page.locator(".select2-results__option").first.click()

    page.wait_for_timeout(1800)

    if label == "Origin":

        val = page.locator("#FromStationId").input_value()

    else:

        val = page.locator("#ToStationId").input_value()

    step(f"✔ {label} committed: {val}")

# ======================

# DATE SELECT

# ======================

def select_date(page):

    step("👉 Setting DATE (direct inject)")

    date_str = f"{TARGET_DATE['day']} {TARGET_DATE['month']} {TARGET_DATE['year']}"

    page.evaluate(

        """

        (value) => {

            const input = document.getElementById('OnwardDate');

            if (!input) throw new Error('OnwardDate not found');

            input.value = value;

            input.dispatchEvent(new Event('input', { bubbles: true }));

            input.dispatchEvent(new Event('change', { bubbles: true }));

        }

        """,

        date_str

    )

    page.wait_for_timeout(1500)

    val = page.locator("#OnwardDate").input_value()

    step(f"✔ Date committed (JS): {val}")

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

        page.wait_for_timeout(800)

        step("✔ Pax = 1")

    except Exception:

        step("⚠️ Pax default used")

# ======================

# VALIDATION

# ======================

def validate(page):

    step("👉 Final validation")

    origin = page.locator("#FromStationId").input_value()

    dest = page.locator("#ToStationId").input_value()

    date = page.locator("#OnwardDate").input_value()

    step(f"DEBUG origin: {origin}")

    step(f"DEBUG dest: {dest}")

    step(f"DEBUG date: {date}")

    if not origin:

        return False, "Origin missing"

    if not dest:

        return False, "Destination missing"

    if not date:

        return False, "Date missing"

    return True, "OK"

# ======================

# SEARCH

# ======================

def search(page):

    step("👉 Clicking SEARCH")

    btn = page.locator("button:has-text('Search')")

    btn.scroll_into_view_if_needed()

    page.wait_for_timeout(800)

    btn.click()

    page.wait_for_load_state("networkidle", timeout=30000)

    page.wait_for_timeout(6000)

    step("✔ Search completed")

# ======================

# SAFE NUMBER PARSER

# ======================

def extract_first_int(text):

    m = re.search(r"\d+", text.replace(",", ""))

    return int(m.group()) if m else 0

# ======================

# SCAN RESULTS

# ======================

def scan(page):

    step("👉 Scanning results")

    row_selectors = [

        "table tbody tr",

        "table tr",

        ".table tbody tr"

    ]

    rows = None

    for sel in row_selectors:

        loc = page.locator(sel)

        if loc.count() > 0:

            rows = loc

            step(f"✔ Using selector: {sel}")

            break

    if rows is None:

        step("❌ No results rendered")

        step(page.inner_text("body")[:2000])

        return "❌ NO RESULTS"

    step(f"Rows found: {rows.count()}")

    debug_rows = []

    for i in range(rows.count()):

        row = rows.nth(i)

        cells = row.locator("td")

        # Preferred: parse by actual table columns

        if cells.count() >= 6:

            try:

                service = cells.nth(0).inner_text().strip()

                departure = cells.nth(1).inner_text().strip()

                arrival = cells.nth(2).inner_text().strip()

                seats_text = cells.nth(4).inner_text().strip()

                fare = cells.nth(5).inner_text().strip()

                seats = extract_first_int(seats_text)

                debug_rows.append(

                    f"{service} | dep={departure} | seats={seats} | fare={fare}"

                )

                if re.match(r"^\d{2}:\d{2}$", departure):

                    if in_window(departure) and seats >= MIN_SEATS:

                        return (

                            f"🚆 MATCH\n"

                            f"Service: {service}\n"

                            f"Time: {departure}\n"

                            f"Arrival: {arrival}\n"

                            f"Seats: {seats}\n"

                            f"Fare: {fare}"

                        )

            except Exception:

                pass

        # Fallback: regex parse row text

        text = row.inner_text().lower()

        times = re.findall(r"\b((?:[01]\d|2[0-3]):[0-5]\d)\b", text)

        numbers = [int(x) for x in re.findall(r"\b\d+\b", text)]

        debug_rows.append(text[:150])

        for t in times:

            # heuristically use largest number in row as seats candidate

            seats = max(numbers) if numbers else 0

            if in_window(t) and seats >= MIN_SEATS:

                return f"🚆 MATCH\nTime: {t}\nSeats: {seats}"

    # debug summary to Telegram so you can see what bot read

    if debug_rows:

        step("📋 Parsed rows:\n" + "\n".join(debug_rows[:8]))

    return "❌ No match"

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

            try:

                page.click("text=Accept", timeout=3000)

            except Exception:

                pass

            try:

                page.click("text=Book Ticket", timeout=5000)

            except Exception:

                pass

            page.wait_for_timeout(5000)

            select_station(page, FROM_STATION, "Origin")

            select_station(page, TO_STATION, "Destination")

            select_date(page)

            select_pax(page)

            ok, reason = validate(page)

            step(f"✔ VALIDATION: {reason}")

            if not ok:

                send(f"❌ FORM INVALID: {reason}")

                browser.close()

                return

            search(page)

            result = scan(page)

            send(result)

            browser.close()

    except Exception:

        send("🔥 CRASH\n" + traceback.format_exc())

run()
