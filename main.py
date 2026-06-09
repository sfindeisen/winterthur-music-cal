#!/usr/bin/env python3

import argparse
from datetime import datetime, timedelta

import pytz

ZURICH = pytz.timezone("Europe/Zurich")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape Winterthur music school events and add to Google Calendar."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each event as it is added or skipped",
    )
    parser.add_argument(
        "--school",
        choices=["all", "jugendmusikschule", "prova", "konservatorium"],
        default="all",
        help="Which school to scrape (default: all)",
    )
    parser.add_argument(
        "--calendar-id",
        default="primary",
        help="Google Calendar ID (default: primary)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print events only, do not write to Google Calendar",
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=90,
        help="Only include events within this many days from today (default: 90)",
    )
    return parser.parse_args()


def collect_events(school: str):
    from scrapers.jugendmusikschule import scrape as scrape_jms
    from scrapers.prova import scrape as scrape_prova
    from scrapers.konservatorium import scrape as scrape_konsi

    scrapers = {
        "jugendmusikschule": scrape_jms,
        "prova": scrape_prova,
        "konservatorium": scrape_konsi,
    }

    if school == "all":
        chosen = scrapers.values()
    else:
        chosen = [scrapers[school]]

    events = []
    for fn in chosen:
        print(f"Scraping {fn.__module__}...")
        try:
            result = fn()
            events.extend(result)
        except Exception as e:
            print(f"Error in {fn.__module__}: {e}")

    return events


def filter_events(events, days_ahead: int):
    now = datetime.now(tz=ZURICH)
    cutoff = now + timedelta(days=days_ahead)
    return [e for e in events if now <= e.date <= cutoff]


def print_table(events):
    for ev in events:
        start_str = ev.date.strftime("%a %d.%m.%Y %H:%M")
        if ev.end_date:
            end_str = ev.end_date.strftime("%a %d.%m.%Y %H:%M")
        elif ev.date.hour == 0 and ev.date.minute == 0:
            end_str = "(all-day)"
        else:
            from datetime import timedelta
            end_str = (ev.date + timedelta(hours=2)).strftime("%a %d.%m.%Y %H:%M")
        print(f"Title:    {ev.title}")
        print(f"Start:    {start_str}")
        print(f"End:      {end_str}")
        print(f"Location: {ev.location}")
        print(f"Source:   {ev.source}")
        print()


def main():
    args = parse_args()

    events = collect_events(args.school)
    events = filter_events(events, args.days_ahead)
    events.sort(key=lambda e: e.date)

    print_table(events)
    print(f"\n{len(events)} events found")

    if args.dry_run:
        print("Dry run — not writing to Google Calendar.")
        return

    from gcal import add_events
    result = add_events(events, args.calendar_id, dry_run=False, verbose=args.verbose)
    print(f"{result['added']} added to Google Calendar, {result['skipped']} skipped (already exist)")


if __name__ == "__main__":
    main()
