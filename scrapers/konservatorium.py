import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import dateparser
import pytz

from scrapers import Event

URLS = [
    "https://konservatorium.ch/aktuelles/",
    "https://konservatorium.ch/veranstaltungen/",
    "https://konservatorium.ch/veranstaltungen-uebersicht/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.5",
}

WEEKDAYS = re.compile(
    r"^(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)"
)

ZURICH = pytz.timezone("Europe/Zurich")

DE_MONTHS = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4,
    "Mai": 5, "Juni": 6, "Juli": 7, "August": 8,
    "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
}


def _parse_date_line(raw: str) -> tuple[datetime | None, str]:
    """
    Parse a line like "Dienstag, 14. April 2026, 18.30 Uhr, Konzertsaal"
    Returns (datetime_aware, location_string).
    """
    parts = [p.strip() for p in raw.split(",")]
    # parts[0] = weekday, parts[1] = date, parts[2] = time, parts[3:] = location
    if len(parts) < 3:
        return None, ""

    date_str = parts[1].strip()   # e.g. "14. April 2026"
    time_str = parts[2].replace("Uhr", "").strip()  # e.g. "18.30" or "18"
    location = ", ".join(parts[3:]) if len(parts) > 3 else ""

    # Parse time
    if "." in time_str:
        try:
            hour, minute = int(time_str.split(".")[0]), int(time_str.split(".")[1])
        except ValueError:
            hour, minute = 0, 0
    else:
        try:
            hour, minute = int(time_str), 0
        except ValueError:
            hour, minute = 0, 0

    # Parse date manually to avoid dateparser locale issues
    # date_str format: "14. April 2026"
    date_str = date_str.replace(".", "").strip()  # "14 April 2026"
    tokens = date_str.split()
    if len(tokens) < 3:
        return None, location
    try:
        day = int(tokens[0])
        month = DE_MONTHS.get(tokens[1], 0)
        year = int(tokens[2])
        if month == 0:
            return None, location
        dt = datetime(year, month, day, hour, minute, 0)
        dt = ZURICH.localize(dt)
        return dt, location
    except (ValueError, KeyError):
        return None, location


def _scrape_one_url(url: str) -> list[Event]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"[konservatorium] {url} returned HTTP {resp.status_code}")
            return []
    except Exception as e:
        print(f"[konservatorium] Fetch error for {url}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    events = []

    date_paras = [
        p for p in soup.find_all("p")
        if WEEKDAYS.match(p.get_text(strip=True))
    ]

    for p in date_paras:
        raw = p.get_text(strip=True)
        dt, location = _parse_date_line(raw)
        if dt is None:
            continue

        # Find title: next h2 or h3 sibling
        title = ""
        description = ""
        for sib in p.next_siblings:
            if not hasattr(sib, "name") or sib.name is None:
                continue
            if sib.name in ("h2", "h3"):
                title = sib.get_text(strip=True)
                # Now look for description: next <p> after the heading
                for inner in sib.next_siblings:
                    if not hasattr(inner, "name") or inner.name is None:
                        continue
                    if inner.name == "p":
                        desc_text = inner.get_text(strip=True)
                        # Skip if it looks like another date line
                        if not WEEKDAYS.match(desc_text):
                            description = desc_text
                        break
                    break
                break
            # Stop if we hit another date line
            if sib.name == "p" and WEEKDAYS.match(sib.get_text(strip=True)):
                break

        if not title:
            continue

        events.append(Event(
            title=title,
            date=dt,
            end_date=None,
            location=location,
            description=description,
            url=url,
            source="Konservatorium Winterthur",
        ))

    return events


def scrape() -> list[Event]:
    all_events: list[Event] = []
    for url in URLS:
        all_events.extend(_scrape_one_url(url))

    # Deduplicate: same title + same minute = same event
    seen: set[tuple[str, datetime]] = set()
    unique: list[Event] = []
    for ev in all_events:
        key = (ev.title, ev.date)
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    return unique

