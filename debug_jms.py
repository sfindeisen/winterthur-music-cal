#!/usr/bin/env python3

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")

resp = requests.get("https://www.jugendmusikschule.ch/events", headers=HEADERS)
soup = BeautifulSoup(resp.text, "html.parser")

markers = [t for t in soup.find_all("h5") if DATE_RE.search(t.get_text())]
print(f"Found {len(markers)} date markers\n")

for marker in markers[:3]:
    print(f"DATE H5: {marker.get_text(strip=True)!r}")
    count = 0
    for sib in marker.next_siblings:
        name = getattr(sib, "name", None)
        if name is None:
            continue
        text = sib.get_text(strip=True)[:80]
        print(f"  <{name}>: {text!r}")
        count += 1
        if count >= 6:
            break
    print()

