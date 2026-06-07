#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
resp = requests.get("https://www.jugendmusikschule.ch/events", headers=HEADERS)
soup = BeautifulSoup(resp.text, "html.parser")

for h2 in soup.find_all("h2")[:3]:
    print(f"H2: {h2.get_text(strip=True)!r}")
    count = 0
    for sib in h2.next_siblings:
        name = getattr(sib, "name", None)
        if name is None:
            continue
        print(f"  AFTER <{name}>: {sib.get_text(strip=True)[:80]!r}")
        count += 1
        if count >= 5:
            break
    count = 0
    for sib in h2.previous_siblings:
        name = getattr(sib, "name", None)
        if name is None:
            continue
        print(f"  BEFORE <{name}>: {sib.get_text(strip=True)[:80]!r}")
        count += 1
        if count >= 3:
            break
    print()

