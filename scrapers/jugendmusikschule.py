import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import pytz

from scrapers import Event

URL = "https://www.jugendmusikschule.ch/events"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")
ZURICH = pytz.timezone("Europe/Zurich")


def _parse_date(text: str) -> datetime | None:
    text = text.replace("Uhr", "").strip()
    parts = text.split()
    if len(parts) < 1:
        return None
    date_part = parts[0]
    time_part = parts[-1] if len(parts) > 1 else "00.00"
    try:
        if "." in time_part and time_part != date_part:
            dt = datetime.strptime(f"{date_part} {time_part}", "%d.%m.%Y %H.%M")
        else:
            dt = datetime.strptime(date_part, "%d.%m.%Y")
    except ValueError:
        return None
    return ZURICH.localize(dt)


def scrape() -> list[Event]:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[jugendmusikschule] Fetch error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    events = []

    date_markers = [
        tag for tag in soup.find_all("h5")
        if DATE_RE.search(tag.get_text())
    ]

    for marker in date_markers:
        dt = _parse_date(marker.get_text(strip=True))
        if dt is None:
            continue

        location_city = ""
        location_venue = ""
        title = ""
        description = ""

        h5_count = 0
        p_count = 0
        h2_found = False

        for sib in marker.next_siblings:
            if not hasattr(sib, "name") or sib.name is None:
                continue
            # Stop if we hit the next event's date marker
            if sib.name == "h5" and DATE_RE.search(sib.get_text()):
                break
            if sib.name == "h5":
                h5_count += 1
                if h5_count == 1:
                    location_city = sib.get_text(strip=True)
            elif sib.name == "p" and not h2_found:
                p_count += 1
                if p_count == 1:
                    location_venue = sib.get_text(strip=True)
            elif sib.name == "h2":
                title = sib.get_text(strip=True)
                h2_found = True
            elif sib.name == "p" and h2_found:
                description = sib.get_text(strip=True)
                break

        if not title:
            continue

        location = ", ".join(filter(None, [location_city, location_venue]))
        events.append(Event(
            title=title,
            date=dt,
            end_date=None,
            location=location,
            description=description,
            url=URL,
            source="Jugendmusikschule Winterthur",
        ))

    return events

