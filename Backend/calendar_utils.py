import datetime
import os
import pytz
import dateparser
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- Google Calendar Setup ---
SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")

if not os.path.exists(CREDENTIALS_FILE):
    raise FileNotFoundError("⚠️ Google Calendar credentials.json file not found!")

# Replace with your actual calendar ID
CALENDAR_ID = "paste your calender ID"


# Setup Google Calendar API client
credentials = service_account.Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=SCOPES
)
service = build("calendar", "v3", credentials=credentials)

# --- Book event to Google Calendar ---
async def async_book_calendar_event(summary: str, time_range: list[str]):
    """
    Creates a Google Calendar event using the given summary and time range.
    :param summary: Event title
    :param time_range: [start, end] in ISO 8601 string
    """
    try:
        event = {
            'summary': summary,
            'start': {'dateTime': time_range[0], 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': time_range[1], 'timeZone': 'Asia/Kolkata'},
        }
        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print("✅ Event created:", created_event.get("htmlLink"))
        return created_event
    except Exception as e:
        print("❌ Error while booking:", e)
        raise e

# --- Fallback time slot if datetime not parsed ---
def get_available_slots() -> list[str]:
    """
    Returns a fallback time slot: tomorrow 11:00 AM IST, 30 minutes duration.
    """
    ist = pytz.timezone("Asia/Kolkata")
    tomorrow = datetime.datetime.now(ist) + datetime.timedelta(days=1)
    start = ist.localize(datetime.datetime(tomorrow.year, tomorrow.month, tomorrow.day, 11, 0))
    end = start + datetime.timedelta(minutes=30)
    return [start.isoformat(), end.isoformat()]

# --- Smart natural language datetime parser ---
def parse_datetime_from_message(message: str) -> list[str] | None:
    """
    Extracts datetime from user message using regex + dateparser.
    Handles:
    - absolute (e.g. 2025-07-12 at 10am)
    - relative (e.g. tomorrow at 4pm)
    - mixed (e.g. next Saturday at 10am 2025-07-12)
    Returns [start, end] as ISO strings in IST.
    """
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)

    # Extract phrases like:
    # - "2025-07-12 at 10am"
    # - "tomorrow at 11am"
    # - "at 4pm tomorrow"
    datetime_patterns = [
    r'\b\d{4}-\d{2}-\d{2}\s*(?:at\s*)?\d{1,2}(?::\d{2})?\s*(am|pm)?',                 # 2025-07-12 at 10am
    r'\b(?:tomorrow|today|next\s+\w+)\s*(at\s*)?\d{1,2}(?::\d{2})?\s*(am|pm)?',       # tomorrow at 11am
    r'\b\d{1,2}(?::\d{2})?\s*(am|pm)?\s*(tomorrow|today|next\s+\w+)',                 # 4pm tomorrow
    r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*\d{1,2}(?::\d{2})?\s*(am|pm)?',  # friday 12pm
    r'\b(?:tomorrow|today|next\s+\w+)',                                               # fallback relative
]
    datetime_fragment = None
    for pattern in datetime_patterns:
        match = re.search(pattern, message.lower())
        if match:
            datetime_fragment = match.group()
            break

    if not datetime_fragment:
        datetime_fragment = message  # fallback

    dt = dateparser.parse(
        datetime_fragment,
        settings={
            'TIMEZONE': 'Asia/Kolkata',
            'RETURN_AS_TIMEZONE_AWARE': True,
            'PREFER_DATES_FROM': 'future',
            'RELATIVE_BASE': now
        }
    )

    if dt:
        if dt.tzinfo is None:
            dt = ist.localize(dt)
        end = dt + datetime.timedelta(minutes=30)
        print(f"🕓 Parsed from '{datetime_fragment}': {dt.isoformat()} to {end.isoformat()}")
        return [dt.isoformat(), end.isoformat()]
    else:
        print(f"⚠️ Failed to parse from: '{datetime_fragment}'")
        return None
