import os
from datetime import timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from scrapers import Event

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CONFIG_DIR = os.path.expanduser("~/.config/winterthur_music_cal")
TOKEN_PATH = os.path.join(CONFIG_DIR, "token.json")
CREDS_PATH = os.path.join(CONFIG_DIR, "credentials.json")


def _get_credentials() -> Credentials:
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDS_PATH}\n"
                    "See README.md for setup instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def add_events(events: list[Event], calendar_id: str, dry_run: bool) -> dict:
    if dry_run:
        return {"added": 0, "skipped": 0}

    creds = _get_credentials()
    service = build("calendar", "v3", credentials=creds)

    added = 0
    skipped = 0

    for event in events:
        # Dedup: search for events with same title within a 1-minute window
        time_min = event.date.isoformat()
        time_max = (event.date + timedelta(minutes=1)).isoformat()
        try:
            existing = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                q=event.title,
                singleEvents=True,
            ).execute()
        except Exception as e:
            print(f"[gcal] Error checking duplicates for '{event.title}': {e}")
            skipped += 1
            continue

        if existing.get("items"):
            skipped += 1
            continue

        end_dt = event.end_date if event.end_date else event.date + timedelta(hours=2)

        body = {
            "summary": event.title,
            "location": event.location,
            "description": (
                f"{event.description}\n\nSource: {event.url}\nSchool: {event.source}"
            ),
            "start": {
                "dateTime": event.date.isoformat(),
                "timeZone": "Europe/Zurich",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Europe/Zurich",
            },
            "extendedProperties": {
                "private": {
                    "source_url": event.url,
                    "source_school": event.source,
                }
            },
        }

        try:
            service.events().insert(calendarId=calendar_id, body=body).execute()
            added += 1
        except Exception as e:
            print(f"[gcal] Error inserting '{event.title}': {e}")
            skipped += 1

    return {"added": added, "skipped": skipped}

