import os
import pytz
import dateparser
from dateparser.search import search_dates
from datetime import timedelta, datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv("Backend/ai.env")

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = "Backend/credentials.json"

# Verify credentials file exists
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError("⚠️ Google Calendar credentials.json file not found!")

# Setup credentials and service
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('calendar', 'v3', credentials=credentials)

# Calendar ID from env or default to primary
CALENDAR_ID = os.getenv("CALENDAR_ID", "primary")

def parse_datetime_from_message(message: str):
    """Extracts datetime from a natural language message."""
    results = search_dates(
        message,
        settings={
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "Asia/Kolkata",
            "PREFER_DATES_FROM": "future",
            "TO_TIMEZONE": "Asia/Kolkata"
        }
    )

    if not results:
        return None

    _, parsed_dt = results[0]

    if parsed_dt.tzinfo is None:
        parsed_dt = pytz.timezone("Asia/Kolkata").localize(parsed_dt)

    parsed_dt = parsed_dt.astimezone(pytz.timezone("Asia/Kolkata"))
    end_dt = parsed_dt + timedelta(hours=1)

    # Debug log
    print(f"[DEBUG] Parsed start: {parsed_dt.isoformat()}")
    print(f"[DEBUG] Parsed end  : {end_dt.isoformat()}")

    return parsed_dt.isoformat(), end_dt.isoformat()


async def async_book_calendar_event(title: str, time_range: tuple):
    """Books an event on Google Calendar."""
    start, end = time_range

    event = {
        'summary': title,
        'start': {
            'dateTime': start,
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end,
            'timeZone': 'Asia/Kolkata',
        },
    }

    try:
        event_result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"✅ Event created: {event_result.get('htmlLink')}")
    except Exception as e:
        print(f"❌ Failed to create event: {e}")


def get_events_for_tomorrow():
    """Retrieves events scheduled for tomorrow."""
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    tomorrow = now + timedelta(days=1)
    start_of_day = tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0))
    end_of_day = tz.localize(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 23, 59, 59))

    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        print(f"❌ Failed to fetch events: {e}")
        return []
