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
    # Normalize non-breaking spaces, remove "Uhr", strip
    text = text.replace("\xa0", " ").strip()
    # Remove anything after a dash or hyphen range (e.g. "16.30 - 18.30 Uhr")
    text = re.split(r"\s+-\s+", text)[0].strip()
    text = text.replace("Uhr", "").strip()
    # Remove non-time words like "abends", "vormittags", "ganztags", "ganzer Tag", "ab"
    text = re.sub(r"\b(abends|vormittags|ganztags|ganzer\s+Tag|ab)\b", "", text, flags=re.IGNORECASE).strip()
    parts = text.split()
    if not parts:
        return None
    date_part = parts[0]
    if not DATE_RE.match(date_part):
        return None
    time_part = parts[1] if len(parts) > 1 else "0"
    # Handle "19.30", "19", "9"
    try:
        if "." in time_part:
            hour, minute = int(time_part.split(".")[0]), int(time_part.split(".")[1])
        else:
            hour, minute = int(time_part), 0
        dt = datetime.strptime(date_part, "%d.%m.%Y").replace(hour=hour, minute=minute)
    except (ValueError, IndexError):
        try:
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

    for row in soup.find_all("div", class_="row b-bot"):
        # Left column: date, city, venue
        left = row.find("div", class_="col-sm-4")
        if not left:
            continue
        headline = left.find("div", class_="headline4")
        if not headline:
            continue

        h5s = headline.find_all("h5")
        if not h5s:
            continue

        date_text = h5s[0].get_text(strip=True)
        dt = _parse_date(date_text)
        if dt is None:
            continue

        city = h5s[1].get_text(strip=True) if len(h5s) > 1 else ""

        # Venue is a text node inside headline4, after the h5 tags
        venue = ""
        for content in headline.children:
            if getattr(content, "name", None) is None:  # NavigableString
                text = content.strip()
                if text:
                    venue = text
                    break

        location = ", ".join(filter(None, [city, venue]))

        # Right column: title and description
        right = row.find("div", class_="col-sm-8")
        if not right:
            continue

        h2 = right.find("h2")
        if not h2:
            continue
        title = h2.get_text(strip=True)

        p = right.find("p")
        description = p.get_text(strip=True) if p else ""

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
