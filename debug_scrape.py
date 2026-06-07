#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9",
}

URLS = [
    "https://www.jugendmusikschule.ch/events",
    "https://www.prova.ch/events/",
    "https://konservatorium.ch/veranstaltungen/",
]

for url in URLS:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    print('='*60)
    resp = requests.get(url, headers=HEADERS, timeout=15)
    print(f"Status: {resp.status_code}")
    soup = BeautifulSoup(resp.text, "html.parser")

    print("\n--- All H2s ---")
    for tag in soup.find_all("h2")[:5]:
        print(repr(tag.get_text(strip=True)))

    print("\n--- All H3s ---")
    for tag in soup.find_all("h3")[:5]:
        print(repr(tag.get_text(strip=True)))

    print("\n--- All H5s ---")
    for tag in soup.find_all("h5")[:5]:
        print(repr(tag.get_text(strip=True)))

    print("\n--- First 10 Ps ---")
    for tag in soup.find_all("p")[:10]:
        print(repr(tag.get_text(strip=True)))

