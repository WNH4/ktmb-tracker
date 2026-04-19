from playwright.sync_api import sync_playwright
import requests
import traceback
import re
import os
import json
from datetime import datetime, timezone, timedelta

# ======================
# CONFIG FROM WORKFLOW
# ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8661868720:AAGoXKdncFwDCOsw_lqweIKvn3EXvGuokSM")
CHAT_ID = os.getenv("CHAT_ID", "8240067274")

FROM_STATION = os.getenv("FROM_STATION", "JB SENTRAL")
TO_STATION = os.getenv("TO_STATION", "KLUANG")

TRAVEL_DATE = os.getenv("TRAVEL_DATE", "")
TARGET_TIME = os.getenv("TARGET_TIME", "21:05")
MODE = os.getenv("MODE", "resale")  # resale / open_check

TIME_WINDOW_MIN = int(os.getenv("TIME_WINDOW_MIN", "15"))
MIN_SEATS = int(os.getenv("MIN_SEATS", "5"))

SALE_START_SGT = os.getenv("SALE_START_SGT", "")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

STATE_DIR = ".state"
STATE_FILE = os.path.join(STATE_DIR, f"{MODE}_{TRAVEL_DATE}.json")

if not TRAVEL_DATE:
    raise Exception("TRAVEL_DATE not provided by workflow")


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


def debug_send(msg):
    if DEBUG:
        send(msg)


def log(msg):
    print(msg)


# ======================
# HELPERS
# ======================
def in_window(t):
    fmt = "%H:%M"
    a = datetime.strptime(t, fmt)
    b = datetime.strptime(TARGET_TIME, fmt)
    return abs((a - b).total_seconds()) <= TIME_WINDOW_MIN * 60


def get_date_parts():
    dt = datetime.strptime(TRAVEL_DATE, "%Y-%m-%d")
    return {
        "day": str(dt.day),
        "month": dt.strftime("%b"),
        "year": str(dt.year)
    }


def now_sgt():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))


def open_check_active_now():
    if not SALE_START_SGT:
        return True
    start_dt = datetime.fromisoformat(SALE_START_SGT)
    return now_sgt() >= start_dt


def extract_first_int(text):
    m = re.search(r"\d+", text.replace(",", ""))
    return int(m.group()) if m else 0


# ======================
# STATE
# ======================
def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(data):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


# ======================
# UI INPUTS
# ======================
def select_station(page, value, label):
    log(f"Selecting {label}")

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


def select_date(page):
    log("Setting date")

    d = get_date_parts()
    date_str = f"{d['day']} {d['month']} {d['year']}"

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


def select_pax(page):
    log("Selecting pax")

    try:
        page.click("text=Pax")
        page.wait_for_timeout(500)
        page.keyboard.type("1")
        page.keyboard.press("Enter")
        page.wait_for_timeout(800)
    except Exception:
        pass


def validate(page):
    origin = page.locator("#FromStationId").input_value()
    dest = page.locator("#ToStationId").input_value()
    date = page.locator("#OnwardDate").input_value()

    if not origin:
        return False, "Origin missing"
    if not dest:
        return False, "Destination missing"
    if not date:
        return False, "Date missing"

    return True, "OK"


def search(page):
    log("Clicking search")

    btn = page.locator("button:has-text('Search')")
    btn.scroll_into_view_if_needed()
    page.wait_for_timeout(800)
    btn.click()

    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(10000)


# ======================
# SCAN RESULTS
# ======================
def scan(page):
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
            break

    if rows is None:
        if MODE == "resale":
            return {"status": "NO_MATCH"}
        return {"status": "NOT_OPEN"}

    matches = []

    for i in range(rows.count()):
        row = rows.nth(i)
        cells = row.locator("td")

        if cells.count() >= 6:
            try:
                service = cells.nth(0).inner_text().strip()
                departure = cells.nth(1).inner_text().strip()
                arrival = cells.nth(2).inner_text().strip()
                seats_text = cells.nth(4).inner_text().strip()
                fare = cells.nth(5).inner_text().strip()

                seats = extract_first_int(seats_text)

                if re.match(r"^\d{2}:\d{2}$", departure) and in_window(departure):
                    matches.append({
                        "service": service,
                        "departure": departure,
                        "arrival": arrival,
                        "seats": seats,
                        "fare": fare
                    })
            except Exception:
                pass

    if not matches:
        if MODE == "resale":
            return {"status": "NO_MATCH"}
        return {"status": "NOT_OPEN"}

    best = max(matches, key=lambda x: x["seats"])

    if MODE == "open_check":
        return {
            "status": "OPENED",
            "service": best["service"],
            "departure": best["departure"],
            "arrival": best["arrival"],
            "seats": best["seats"],
            "fare": best["fare"]
        }

    return {
        "status": "MATCH",
        "service": best["service"],
        "departure": best["departure"],
        "arrival": best["arrival"],
        "seats": best["seats"],
        "fare": best["fare"]
    }


# ======================
# NOTIFICATION LOGIC
# ======================
def handle_open_check(result):
    if not open_check_active_now():
        debug_send(
            f"⏸ Open check not active yet\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Gate: {SALE_START_SGT}"
        )
        return

    state = load_state()
    previously_open = state.get("opened", False)

    if result["status"] == "OPENED":
        debug_send(
            f"DEBUG open_check result\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Time: {result['departure']}\n"
            f"Previously open: {previously_open}"
        )

        if not previously_open:
            send(
                f"🎉 KTMB TICKET OPENED\n"
                f"{FROM_STATION} → {TO_STATION}\n"
                f"Date: {TRAVEL_DATE}\n"
                f"Time: {result['departure']}\n"
                f"Arrival: {result['arrival']}\n"
                f"Seats shown: {result['seats']}\n"
                f"Fare: {result['fare']}"
            )

        state["opened"] = True
        state["last_departure"] = result["departure"]

    else:
        debug_send(
            f"⏳ Not open for target window\n"
            f"{FROM_STATION} → {TO_STATION}\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Target: {TARGET_TIME} ± {TIME_WINDOW_MIN} min"
        )

        state["opened"] = False
        state["last_departure"] = None

    save_state(state)


def handle_resale(result):
    state = load_state()
    last_seats = state.get("last_seats")
    last_departure = state.get("last_departure")
    last_status = state.get("last_status")

    if result["status"] == "MATCH":
        current_seats = result["seats"]
        current_departure = result["departure"]

        changed = (
            last_status != "MATCH"
            or last_seats != current_seats
            or last_departure != current_departure
        )

        debug_send(
            f"DEBUG resale result\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Time: {current_departure}\n"
            f"Seats: {current_seats}\n"
            f"Changed: {changed}"
        )

        if changed:
            send(
                f"🚆 KTMB RETURN CHANGE DETECTED\n"
                f"Date: {TRAVEL_DATE}\n"
                f"Time: {current_departure}\n"
                f"Arrival: {result['arrival']}\n"
                f"Seats shown: {current_seats}\n"
                f"Fare: {result['fare']}\n"
                f"Status: list only, not login-confirmed"
            )

        state["last_status"] = "MATCH"
        state["last_seats"] = current_seats
        state["last_departure"] = current_departure

    else:
        changed = last_status != "NO_MATCH"

        debug_send(
            f"❌ No target-window tickets shown\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Target: {TARGET_TIME} ± {TIME_WINDOW_MIN} min\n"
            f"Changed: {changed}"
        )

        if changed:
            send(
                f"❌ KTMB RETURN UPDATE\n"
                f"Date: {TRAVEL_DATE}\n"
                f"No tickets currently shown"
            )

        state["last_status"] = "NO_MATCH"
        state["last_seats"] = None
        state["last_departure"] = None

    save_state(state)


# ======================
# MAIN
# ======================
def run():
    try:
        debug_send(
            f"🚀 Bot started\n"
            f"Mode: {MODE}\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Target: {TARGET_TIME} ± {TIME_WINDOW_MIN} min"
        )

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
            if not ok:
                send(f"❌ FORM INVALID: {reason}")
                browser.close()
                return

            search(page)
            result = scan(page)

            if MODE == "resale":
                handle_resale(result)
            elif MODE == "open_check":
                handle_open_check(result)

            browser.close()

    except Exception:
        send("🔥 CRASH\n" + traceback.format_exc())


run()
