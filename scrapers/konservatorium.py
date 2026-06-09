import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
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

ZURICH = pytz.timezone("Europe/Zurich")

DE_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8,
    "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    "januer": 1, "mäz": 3, "mörz": 3,
}

WEEKDAYS = r"(?:Mo|Di|Mi|Do|Fr|Sa|So|Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)"

# Matches a single date+optional-time fragment:
# e.g. "14. April 2026, 18.30 Uhr" or "12. Juni" (no year, no time)
SINGLE_DATE_RE = re.compile(
    r"""
    (?:""" + WEEKDAYS + r"""[.,\s-]*)?   # optional weekday
    (\d{1,2})\.?\s+                       # day
    ([A-Za-zäöüÄÖÜ]+)\s*                  # month name
    (\d{4})?                              # optional year
    (?:[,\s]+
      (?:ab\s+|ca\.\s+)?
      (\d{1,2})[.:\s](\d{2})?
      \s*Uhr
    )?                                    # optional time
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Separators between two dates in a range
RANGE_SEP_RE = re.compile(r"\s*(?:–|—|-{1,2}|bis)\s*", re.IGNORECASE)


def _parse_month(name: str) -> int:
    return DE_MONTHS.get(name.lower().strip(), 0)


def _build_dt(day: int, month: int, year: int, hour: int, minute: int) -> datetime:
    return ZURICH.localize(datetime(year, month, day, hour, minute, 0))


def _parse_single(text: str) -> datetime | None:
    """Parse the first date+time found in text. Returns None on failure."""
    m = SINGLE_DATE_RE.search(text)
    if not m:
        return None
    day = int(m.group(1))
    month = _parse_month(m.group(2))
    if month == 0:
        return None
    year = int(m.group(3)) if m.group(3) else datetime.now(ZURICH).year
    hour = int(m.group(4)) if m.group(4) else 0
    minute = int(m.group(5)) if m.group(5) else 0
    try:
        return _build_dt(day, month, year, hour, minute)
    except ValueError:
        return None


def _parse_date_string(raw: str) -> tuple[datetime | None, datetime | None, str]:
    """
    Returns (start_dt, end_dt, location).
    Handles single dates, dash ranges, and multiple dates (;  /  and).
    end_dt is None for single-day/timed events.
    """
    raw = " ".join(raw.split())

    matches = list(SINGLE_DATE_RE.finditer(raw))
    if not matches:
        return None, None, ""

    # Build datetime for each match, propagating year forward from the
    # nearest match that has an explicit year.
    datetimes = []
    last_year = datetime.now(ZURICH).year

    for m in matches:
        day = int(m.group(1))
        month = _parse_month(m.group(2))
        if month == 0:
            datetimes.append(None)
            continue
        year = int(m.group(3)) if m.group(3) else last_year
        last_year = year
        hour   = int(m.group(4)) if m.group(4) else 0
        minute = int(m.group(5)) if m.group(5) else 0
        try:
            datetimes.append(_build_dt(day, month, year, hour, minute))
        except ValueError:
            datetimes.append(None)

    # Drop failed parses
    valid = [(m, dt) for m, dt in zip(matches, datetimes) if dt is not None]
    if not valid:
        return None, None, ""

    start_match, start_dt = valid[0]
    end_match,   end_dt   = valid[-1]

    # Location: text after the last valid match
    tail = raw[end_match.end():].strip().lstrip(",;/–-").strip()
    location = _clean_location(tail)

    # Only set end_dt when there really are multiple dates
    if len(valid) == 1:
        end_dt = None

    return start_dt, end_dt, location


def _clean_location(tail: str) -> str:
    """Strip price/note fragments from a location string."""
    for kw in ["Eintritt", "Preise", "Fr.", "CHF", "Gratis", "Anmeldung"]:
        idx = tail.find(kw)
        if idx != -1:
            tail = tail[:idx].strip().rstrip(",").strip()
    return tail


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

    for h2 in soup.find_all("h2"):
        title = h2.get_text(strip=True)
        if not title:
            continue

        sibs = []
        for sib in h2.next_siblings:
            if not hasattr(sib, "name") or sib.name is None:
                continue
            if sib.name == "h2":
                break
            if sib.name == "div":
                sibs.append(sib)
            if len(sibs) >= 2:
                break

        if not sibs:
            continue

        date_div_text = sibs[0].get_text(strip=True)
        start_dt, end_dt, location = _parse_date_string(date_div_text)
        if start_dt is None:
            continue

        description = sibs[1].get_text(strip=True) if len(sibs) > 1 else ""

        events.append(Event(
            title=title,
            date=start_dt,
            end_date=end_dt,
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

    seen: set[tuple[str, datetime]] = set()
    unique: list[Event] = []
    for ev in all_events:
        key = (ev.title, ev.date)
        if key not in seen:
            seen.add(key)
            unique.append(ev)

    return unique
