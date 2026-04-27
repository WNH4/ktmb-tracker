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
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "-1003916125901")

FROM_STATION = os.getenv("FROM_STATION", "JB SENTRAL")
TO_STATION = os.getenv("TO_STATION", "KLUANG")

TRAVEL_DATE = os.getenv("TRAVEL_DATE", "")
TARGET_TIME = os.getenv("TARGET_TIME", "21:05")
MODE = os.getenv("MODE", "resale")  # resale / open_check

TIME_WINDOW_MIN = int(os.getenv("TIME_WINDOW_MIN", "15"))
MIN_SEATS = int(os.getenv("MIN_SEATS", "1"))

SALE_START_SGT = os.getenv("SALE_START_SGT", "")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

STATE_DIR = ".state"

STATE_KEY = f"{MODE}_{FROM_STATION}_{TO_STATION}_{TRAVEL_DATE}_{TARGET_TIME}"
STATE_KEY = re.sub(r"[^A-Za-z0-9_-]+", "_", STATE_KEY)
STATE_FILE = os.path.join(STATE_DIR, f"{STATE_KEY}.json")

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN not provided by workflow")

if not TRAVEL_DATE:
    raise Exception("TRAVEL_DATE not provided by workflow")


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
    btn = page.locator("button:has-text('Search')")
    btn.scroll_into_view_if_needed()
    page.wait_for_timeout(800)
    btn.click()

    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(10000)


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

                if (
                    re.match(r"^\d{2}:\d{2}$", departure)
                    and in_window(departure)
                    and seats >= MIN_SEATS
                ):
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

    trips = {}
    for m in matches:
        trips[m["departure"]] = {
            "service": m["service"],
            "arrival": m["arrival"],
            "seats": m["seats"],
            "fare": m["fare"]
        }

    return {
        "status": "MATCH",
        "trips": trips
    }


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
        if not previously_open:
            send(
                f"🎉 KTMB TICKET OPENED\n"
                f"{FROM_STATION} → {TO_STATION}\n"
                f"Date: {TRAVEL_DATE}\n"
                f"Time: {result['departure']}\n"
                f"Arrival: {result['arrival']}\n"
                f"Public list seats shown: {result['seats']}\n"
                f"Fare: {result['fare']}\n"
                f"⚠️ Please login to confirm actual seat map availability"
            )

        state["opened"] = True
        state["last_departure"] = result["departure"]

    else:
        state["opened"] = False
        state["last_departure"] = None

    save_state(state)


def handle_resale(result):
    state = load_state()

    if result["status"] != "MATCH":
        previous = state.get("trips", {})

        if previous:
            send(
                f"❌ KTMB RETURN UPDATE\n"
                f"{FROM_STATION} → {TO_STATION}\n"
                f"Date: {TRAVEL_DATE}\n"
                f"No target-window tickets currently shown"
            )

        state["trips"] = {}
        save_state(state)
        return

    current_trips = result.get("trips", {})
    previous_trips = state.get("trips", {})

    changes = []

    for dep, info in current_trips.items():
        old = previous_trips.get(dep)

        if old is None:
            changes.append(
                f"🆕 New trip {dep} → {info['arrival']} | seats {info['seats']} | {info['fare']}"
            )
        elif old.get("seats") != info["seats"]:
            changes.append(
                f"🔄 Seat change {dep}: {old.get('seats')} → {info['seats']} | {info['fare']}"
            )

    for dep in previous_trips:
        if dep not in current_trips:
            changes.append(f"❌ Trip disappeared {dep}")

    if changes:
        send(
            f"🚆 KTMB RETURN CHANGE DETECTED\n"
            f"{FROM_STATION} → {TO_STATION}\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Window: {TARGET_TIME} ± {TIME_WINDOW_MIN} min\n\n"
            + "\n".join(changes)
            + "\n\n⚠️ Please login to confirm actual seat map availability"
        )

    state["trips"] = current_trips
    save_state(state)


def load_ktmb(page, browser):
    goto_success = False

    for attempt in range(3):
        try:
            page.goto(
                "https://online.ktmb.com.my",
                wait_until="domcontentloaded",
                timeout=60000
            )
            goto_success = True
            break
        except Exception as e:
            log(f"KTMB load failed attempt {attempt + 1}: {e}")
            page.wait_for_timeout(5000)

    if not goto_success:
        send(
            f"⚠️ KTMB SITE LOAD FAILED\n"
            f"{FROM_STATION} → {TO_STATION}\n"
            f"Date: {TRAVEL_DATE}\n"
            f"Will retry next cron run."
        )
        browser.close()
        return False

    page.wait_for_timeout(8000)
    return True


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

            if not load_ktmb(page, browser):
                return

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
