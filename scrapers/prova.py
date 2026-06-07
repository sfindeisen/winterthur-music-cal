import time
import requests
from bs4 import BeautifulSoup
import dateparser
import pytz

from scrapers import Event

URL = "https://www.prova.ch/events/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
ZURICH = pytz.timezone("Europe/Zurich")


def _parse_date(text: str):
    text = text.strip().rstrip("h").strip()
    return dateparser.parse(
        text,
        languages=["de"],
        settings={"TIMEZONE": "Europe/Zurich", "RETURN_AS_TIMEZONE_AWARE": True},
    )


def _fetch_detail(url: str) -> tuple[str, str]:
    try:
        time.sleep(0.5)
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception:
        return "", ""

    soup = BeautifulSoup(resp.text, "html.parser")
    description = ""
    location = ""

    content = (
        soup.find("div", class_=lambda c: c and "entry-content" in c)
        or soup.find("article")
        or soup.find("main")
        or soup.body
    )
    if content:
        p = content.find("p")
        if p:
            description = p.get_text(strip=True)

    for line in soup.get_text(separator="\n").splitlines():
        line = line.strip()
        if line.startswith("Ort:") or line.startswith("Adresse:"):
            location = line.split(":", 1)[-1].strip()
            break

    return description, location


def scrape() -> list[Event]:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[prova] Fetch error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    events = []

    for h3 in soup.find_all("h3"):
        a = h3.find("a")
        if not a:
            continue

        title = h3.get_text(strip=True)
        detail_url = a.get("href", URL)

        # Date is in the <p> immediately after the <h3>
        date_str = ""
        for sib in h3.next_siblings:
            if not hasattr(sib, "name") or sib.name is None:
                continue
            if sib.name == "p":
                date_str = sib.get_text(strip=True)
                break

        if not date_str:
            continue

        dt = _parse_date(date_str)
        if dt is None:
            continue

        description, location = _fetch_detail(detail_url)

        events.append(Event(
            title=title,
            date=dt,
            end_date=None,
            location=location,
            description=description,
            url=detail_url,
            source="Musikschule Prova",
        ))

    return events
