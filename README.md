# Winterthur Music School Calendar Scraper

Scrapes concert events from 3 Winterthur music schools and adds them to Google Calendar.

**Sources:**
- Jugendmusikschule Winterthur — jugendmusikschule.ch/events
- Musikschule Prova — prova.ch/events/
- Konservatorium Winterthur — konservatorium.ch (aktuelles, veranstaltungen, veranstaltungen-uebersicht)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Calendar credentials

1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable the **Google Calendar API**
4. Go to **Credentials → Create Credentials → OAuth client ID**
5. Choose **Desktop app**, download the JSON file
6. Save it to:

```bash
~/.config/winterthur_music_cal/credentials.json
```

### 3. First run

The first time you run without `--dry-run`, a browser window opens asking you
to authorise Google Calendar access. The token is saved automatically to
`~/.config/winterthur_music_cal/token.json` and reused on future runs.

## Usage

```bash
# Preview all events without writing anything
python main.py --dry-run

# One school only
python main.py --school prova --dry-run

# Only events in the next 30 days
python main.py --days-ahead 30

# Write to a specific calendar
python main.py --calendar-id abc123@group.calendar.google.com

# Everything at once
python main.py --school all --days-ahead 60
```

