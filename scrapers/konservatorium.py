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
    # typos seen in the wild
    "januer": 1, "mäz": 3, "mörz": 3,
}

# Matches the first real date in a string like "Samstag, 04. Juli 2026, 19 Uhr, Serenadenplatz"
# Also handles missing year, missing time, ab/ca. prefixes, colons in time
DATE_RE = re.compile(
    r"""
    (?:(?:Mo|Di|Mi|Do|Fr|Sa|So|Montag|Dienstag|Mittwoch|Donnerstag|
          Freitag|Samstag|Sonntag)[.,\s-]*)?  # optional weekday
    (\d{1,2})\.?\s+                            # day
    ([A-Za-zäöüÄÖÜ]+)\s*                       # month name
    (\d{4})?                                   # optional year
    (?:[,\s]+                                  # separator
      (?:ab\s+|ca\.\s+)?                       # optional prefix
      (\d{1,2})[.:\s](\d{2})?                 # hour and optional minute
      \s*Uhr                                   # "Uhr"
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _parse_date_string(raw: str) -> tuple[datetime | None, str]:
    """
    Parse the first date found in raw.
    Returns (datetime_aware, location_string).
    Location is everything after the last time reference, or after the date.
    """
    # Normalise: collapse whitespace, strip
    raw = " ".join(raw.split())

    m = DATE_RE.search(raw)
    if not m:
        return None, ""

    day = int(m.group(1))
    month_str = m.group(2).lower()
    month = DE_MONTHS.get(month_str, 0)
    if month == 0:
        return None, ""

    year_str = m.group(3)
    year = int(year_str) if year_str else datetime.now(ZURICH).year

    hour = int(m.group(4)) if m.group(4) else 0
    minute = int(m.group(5)) if m.group(5) else 0

    try:
        dt = datetime(year, month, day, hour, minute, 0)
        dt = ZURICH.localize(dt)
    except ValueError:
        return None, ""

    # Location: text after the match end, strip leading comma/spaces/dash
    tail = raw[m.end():].strip().lstrip(",–-").strip()
    # Remove trailing price/note fragments that start with common keywords
    for kw in ["Eintritt", "Preise", "Fr.", "CHF", "Gratis", "Anmeldung"]:
        idx = tail.find(kw)
        if idx != -1:
            tail = tail[:idx].strip().rstrip(",").strip()

    return dt, tail


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

        # Collect the next sibling divs
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

        # First div is the date line
        date_div_text = sibs[0].get_text(strip=True)
        dt, location = _parse_date_string(date_div_text)
        if dt is None:
            continue

        # Second div (if present) is the description
        description = sibs[1].get_text(strip=True) if len(sibs) > 1 else ""

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
