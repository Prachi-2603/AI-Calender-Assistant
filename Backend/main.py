from fastapi import FastAPI
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
import os
import re
from datetime import datetime

from Backend.calendar_utils import (
    get_available_slots,
    async_book_calendar_event,
    parse_datetime_from_message
)

# Load env vars
load_dotenv("Backend/ai.env")

app = FastAPI()

# Load Gemini API key
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise EnvironmentError("❌ GOOGLE_API_KEY not set.")

# Initialize Gemini model
chat_model = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.7,
    google_api_key=google_api_key,
    system_message=(
        "You are a smart calendar assistant. If the user wants to schedule a call, meeting, appointment, "
        "or event, extract the date, time, and purpose and confirm the booking. Be precise and friendly."
    )
)

# Session memory storage
session_memory_store: dict[str, ConversationBufferMemory] = {}

def get_memory(session_id: str) -> ConversationBufferMemory:
    if session_id not in session_memory_store:
        session_memory_store[session_id] = ConversationBufferMemory(return_messages=True)
    return session_memory_store[session_id]

# Booking keywords and types
BOOKING_KEYWORDS = ["book", "schedule", "set up", "arrange", "create", "organize"]
BOOKING_TYPES = ["meeting", "call", "appointment", "event"]

def detect_booking_intent(message: str) -> bool:
    msg = message.lower()
    return any(k in msg for k in BOOKING_KEYWORDS) and any(t in msg for t in BOOKING_TYPES)

def extract_title_from_message(message: str) -> str:
    for bt in BOOKING_TYPES:
        if bt in message.lower():
            title_match = re.search(rf"{bt} (with .+)", message, re.IGNORECASE)
            if title_match:
                return f"{bt.capitalize()} {title_match.group(1).strip().capitalize()}"
            return bt.capitalize()
    return "Meeting"

# Request schema
class ChatInput(BaseModel):
    message: str
    session_id: str = "default"

@app.post("/chat/")
async def chat(input: ChatInput):
    user_message = input.message
    session_id = input.session_id

    try:
        memory = get_memory(session_id)
        memory.chat_memory.add_user_message(user_message)
        history = memory.chat_memory.messages

        # Detect booking intent
        if detect_booking_intent(user_message):
            parsed_range = parse_datetime_from_message(user_message)
            title = extract_title_from_message(user_message)

            if parsed_range:
                await async_book_calendar_event(title, parsed_range)

                # Convert ISO string to datetime for display
                start_dt = datetime.fromisoformat(parsed_range[0])
                response_text = f"📅 {title} booked at {start_dt.strftime('%Y-%m-%d %I:%M %p')}"
            else:
                # Fallback slot
                fallback_range = get_available_slots()
                await async_book_calendar_event(title, fallback_range)

                start_dt = datetime.fromisoformat(fallback_range[0])
                response_text = f"📅 {title} booked at fallback time: {start_dt.strftime('%Y-%m-%d %I:%M %p')}"
        else:
            # Not a booking message: use Gemini
            response = await chat_model.ainvoke(history)
            response_text = response.content

        memory.chat_memory.add_ai_message(response_text)
        return {"response": response_text}

    except Exception as e:
        print(f"[❌ Backend Error]: {e}")
        return {"response": f"⚠️ Internal error: {str(e)}"}
