import argparse
from datetime import datetime, timedelta

import pytz
from rich.console import Console
from rich.table import Table

console = Console()
ZURICH = pytz.timezone("Europe/Zurich")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape Winterthur music school events and add to Google Calendar."
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
        console.print(f"[dim]Scraping {fn.__module__}...[/dim]")
        try:
            result = fn()
            events.extend(result)
        except Exception as e:
            console.print(f"[red]Error in {fn.__module__}: {e}[/red]")

    return events


def filter_events(events, days_ahead: int):
    now = datetime.now(tz=ZURICH)
    cutoff = now + timedelta(days=days_ahead)
    return [e for e in events if now <= e.date <= cutoff]


def print_table(events):
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("School", style="dim", max_width=30)
    table.add_column("Title", max_width=45)
    table.add_column("Date", max_width=18)
    table.add_column("Location", max_width=30)

    for ev in events:
        table.add_row(
            ev.source,
            ev.title,
            ev.date.strftime("%a %d.%m.%Y %H:%M"),
            ev.location,
        )

    console.print(table)


def main():
    args = parse_args()

    events = collect_events(args.school)
    events = filter_events(events, args.days_ahead)
    events.sort(key=lambda e: e.date)

    print_table(events)
    console.print(f"\n[bold]{len(events)} events found[/bold]")

    if args.dry_run:
        console.print("[yellow]Dry run — not writing to Google Calendar.[/yellow]")
        return

    from gcal import add_events
    result = add_events(events, args.calendar_id, dry_run=False)
    console.print(
        f"[green]{result['added']} added to Google Calendar[/green], "
        f"[dim]{result['skipped']} skipped (already exist)[/dim]"
    )


if __name__ == "__main__":
    main()

