#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9",
}

url = "https://konservatorium.ch/veranstaltungen/"
resp = requests.get(url, headers=HEADERS, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Print the 3 siblings before and after each H2
print("=== H2 CONTEXT (2 siblings before and after each H2) ===\n")
for h2 in soup.find_all("h2")[:6]:
    print(f"--- H2: {h2.get_text(strip=True)!r} ---")
    # previous siblings
    prev = [s for s in h2.previous_siblings if hasattr(s, "name") and s.name][:2]
    for s in reversed(prev):
        print(f"  BEFORE <{s.name}>: {s.get_text(strip=True)!r}")
    # next siblings
    count = 0
    for s in h2.next_siblings:
        if not hasattr(s, "name") or not s.name:
            continue
        print(f"  AFTER  <{s.name}>: {s.get_text(strip=True)!r}")
        count += 1
        if count >= 2:
            break
    print()

print("\n=== ALL SPANS ===")
for tag in soup.find_all("span")[:10]:
    t = tag.get_text(strip=True)
    if t:
        print(repr(t))

print("\n=== ALL DIVS with date-like text ===")
import re
DATE_RE = re.compile(r"\d{4}|\d{1,2}\. \w+")
for tag in soup.find_all("div"):
    t = tag.get_text(strip=True)
    if DATE_RE.search(t) and len(t) < 100:
        print(f"<div class={tag.get('class')}> {t!r}")

