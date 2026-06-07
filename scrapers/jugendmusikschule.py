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
    text = text.replace("\xa0", " ").replace("Uhr", "").strip()
    parts = text.split()
    if not parts:
        return None
    date_part = parts[0]
    time_part = parts[1] if len(parts) > 1 else "00.00"
    try:
        if "." in time_part:
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
        t for t in soup.find_all("h5")
        if DATE_RE.search(t.get_text())
    ]

    for marker in date_markers:
        dt = _parse_date(marker.get_text(strip=True))
        if dt is None:
            continue

        # City is the next h5 sibling inside the same parent div
        location_city = ""
        for sib in marker.next_siblings:
            if getattr(sib, "name", None) == "h5":
                location_city = sib.get_text(strip=True)
                break

        # The h2 (title) and p (description) are in the NEXT sibling div
        # of this marker's parent
        parent = marker.parent
        if parent is None:
            continue

        title = ""
        description = ""
        location_venue = ""

        # Walk next siblings of the parent div to find the content div
        for next_div in parent.next_siblings:
            if getattr(next_div, "name", None) != "div":
                continue
            h2 = next_div.find("h2")
            if h2:
                title = h2.get_text(strip=True)
                p = next_div.find("p")
                if p:
                    description = p.get_text(strip=True)
            break  # only look at the immediately next div

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
