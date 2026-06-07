from dataclasses import dataclass
from datetime import datetime


@dataclass
class Event:
    title: str
    date: datetime
    end_date: datetime | None
    location: str
    description: str
    url: str
    source: str

