from flask import Flask, Response, request, jsonify
import requests
from ics import Calendar, Event
from datetime import datetime
import os
import logging
import sys
from dotenv import load_dotenv
import json
from flask_cors import CORS

# Load environment variables from .env file before configuring logging
load_dotenv()

# Determine log file path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.getenv("LOG_PATH", os.path.join(BASE_DIR, "app.log"))

# Configure logging to show both in console and file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH)
    ]
)
logger = logging.getLogger(__name__)

# Get environment variables
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("DATABASE_ID")
PORT = int(os.getenv("PORT", "5004"))  # Changed from 5000 to 5001 to match ngrok

if not NOTION_API_KEY or not DATABASE_ID:
    raise ValueError("Please set NOTION_API_KEY and DATABASE_ID environment variables")

NOTION_API_URL = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Cache for calendar data
cached_calendar = None
cache_timestamp = None

@app.route("/")
def index():
    """Simple index page to verify the server is running."""
    # Handle webhook verification
    challenge = request.args.get('challenge')
    if challenge:
        logger.info(f"Received webhook verification challenge: {challenge}")
        return jsonify({"challenge": challenge})
    
    return "Notion Calendar Sync Server is running!"

@app.route("/health")
def health_check():
    """Endpoint to check if the server is running."""
    return "Server is running!"

def fetch_notion_events():
    logger.info(f"Fetching events from Notion database {DATABASE_ID}")
    
    try:
        query = {
            "filter": {
                "property": "Name",
                "rich_text": {
                    "is_not_empty": True
                }
            },
            "sorts": [
                {
                    "property": "Do Date",
                    "direction": "ascending"
                }
            ]
        }
        
        res = requests.post(NOTION_API_URL, headers=NOTION_HEADERS, json=query)
        
        if res.status_code != 200:
            logger.error(f"Notion API error: {res.status_code} - {res.text}")
            return []
            
        data = res.json()
        logger.debug(f"Notion API response: {json.dumps(data, indent=2)}")
        
        events = []
        for page in data.get('results', []):
            properties = page.get('properties', {})
            
            # Get basic properties
            name = properties.get('Name', {}).get('title', [{}])[0].get('plain_text', '')
            do_date = properties.get('Do Date', {}).get('date', {})
            start_date = do_date.get('start')
            end_date = do_date.get('end')
            
            # Get course name and emoji if relation exists
            course_name = ""
            course_emoji = ""
            if properties.get('Course', {}).get('relation'):
                course_id = properties['Course']['relation'][0].get('id')
                if course_id:
                    try:
                        course_res = requests.get(
                            f"https://api.notion.com/v1/pages/{course_id}",
                            headers=NOTION_HEADERS
                        )
                        if course_res.status_code == 200:
                            course_data = course_res.json()
                            # Get course name
                            course_name = course_data.get('properties', {}).get('Name', {}).get('title', [{}])[0].get('plain_text', '')
                            # Get course emoji if it exists
                            course_emoji = course_data.get('icon', {}).get('emoji', '')
                    except Exception as e:
                        logger.warning(f"Error fetching course page: {str(e)}")
            
            # Get status
            status = properties.get('Status', {}).get('status', {}).get('name', '')
            
            # Create event
            event = Event()
            # Format event name with emoji and course name (if available)
            if course_name:
                emoji_prefix = f"{course_emoji} " if course_emoji else ""
                event.name = f"{name} - {emoji_prefix}{course_name}"
            else:
                event.name = name
            
            # Parse start date
            try:
                if start_date:
                    if 'T' in start_date:  # If it has time
                        event.begin = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    else:  # If it's just a date
                        event.begin = datetime.fromisoformat(start_date)
                        
                    # If end date exists, use it; otherwise, default to start date + 1 hour
                    if end_date:
                        if 'T' in end_date:
                            event.end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        else:
                            event.end = datetime.fromisoformat(end_date)
                    else:
                        # Default to 1 hour duration if no end time is specified
                        event.end = event.begin.replace(hour=event.begin.hour + 1)
                    
                    # If it's just a date (no time), make it a full-day event
                    if 'T' not in start_date:
                        event.make_all_day()
                else:
                    logger.warning(f"No start date found for event: {name}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Error parsing date for event '{name}': {str(e)}")
                continue
            
            # Create description
            description_parts = []
            if status:
                description_parts.append(f"Status: {status}")
            if page.get('url'):
                description_parts.append(f"URL: {page.get('url')}")
            
            event.description = "\n".join(description_parts)
            
            events.append(event)
        
        logger.info(f"Generated {len(events)} events")
        return events
        
    except Exception as e:
        logger.error(f"Error fetching events: {str(e)}", exc_info=True)
        return []

@app.route("/calendar.ics", methods=["GET", "OPTIONS"])
def calendar_feed():
    """Generate and return the ICS calendar feed."""
    try:
        if request.method == "OPTIONS":
            return Response(
                status=200,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )

        global cached_calendar, cache_timestamp
        
        if cached_calendar is None or cache_timestamp is None:
            logger.info("Generating new calendar feed...")
            cal = Calendar()
            events = fetch_notion_events()
            
            if not events:
                logger.warning("No events found in Notion database")
                return Response("No events found", status=404)
            
            for event in events:
                cal.events.add(event)
            
            cached_calendar = str(cal)
            cache_timestamp = datetime.now()
            logger.info(f"Generated calendar with {len(events)} events")
            logger.debug(f"Generated calendar: {cached_calendar}")
        
        response = Response(
            cached_calendar,
            mimetype="text/calendar",
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )
        return response
        
    except Exception as e:
        logger.error(f"Error generating calendar: {str(e)}", exc_info=True)
        return Response("Error generating calendar", status=500)

@app.route("/webhook", methods=["POST", "GET", "OPTIONS"])
def webhook():
    """Handle Notion webhook events."""
    try:
        if request.method == "OPTIONS":
            return Response(
                status=200,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )

        if request.method == "GET":
            challenge = request.args.get('challenge')
            if challenge:
                logger.info(f"Received webhook verification challenge: {challenge}")
                return jsonify({"challenge": challenge})
            return "Webhook verification endpoint", 200

        data = request.json
        logger.info(f"Received webhook event: {json.dumps(data, indent=2)}")
        
        global cached_calendar, cache_timestamp
        cached_calendar = None
        cache_timestamp = None
        
        return "", 200
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        return Response("Error", status=500)

if __name__ == "__main__":
    logger.info("Starting server...")
    logger.info(f"Using NOTION_API_KEY: {NOTION_API_KEY[:5]}... (truncated for security)")
    logger.info(f"Using DATABASE_ID: {DATABASE_ID}")
    app.run(port=PORT, debug=False, host='0.0.0.0')
