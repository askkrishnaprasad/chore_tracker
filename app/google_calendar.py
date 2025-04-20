import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.models import UserCalendarToken
from app import db

# Load API credentials from environment variables
CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5001/calendar/oauth2callback')

# Define OAuth2 scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def get_authorization_url():
    """Generate URL for Google authorization."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force to show consent screen to get refresh token
    )
    
    return authorization_url, state

def process_oauth_callback(code):
    """Process OAuth callback and get tokens."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    
    # Exchange authorization code for tokens
    flow.fetch_token(code=code)
    credentials = flow.credentials
    
    # Get token values
    access_token = credentials.token
    refresh_token = credentials.refresh_token
    expiry = credentials.expiry
    
    return access_token, refresh_token, expiry

def save_tokens(user_id, access_token, refresh_token, expiry):
    """Save tokens to database."""
    # Check if token exists for user
    token_entry = UserCalendarToken.query.filter_by(user_id=user_id).first()
    
    if token_entry:
        # Update existing token
        token_entry.access_token = access_token
        if refresh_token:  # Only update refresh token if provided
            token_entry.refresh_token = refresh_token
        token_entry.token_expiry = expiry
    else:
        # Create new token
        token_entry = UserCalendarToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=expiry
        )
        db.session.add(token_entry)
    
    db.session.commit()

def get_credentials(user_id):
    """Get credentials for a user."""
    token_entry = UserCalendarToken.query.filter_by(user_id=user_id).first()
    
    if not token_entry:
        return None
    
    credentials = Credentials(
        token=token_entry.access_token,
        refresh_token=token_entry.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES
    )
    
    # If token is expired, it will be automatically refreshed when needed
    
    return credentials

def add_calendar_event(user_id, chore_name, due_date, notes=None, duration_hours=1):
    """Add a chore as a Google Calendar event."""
    credentials = get_credentials(user_id)
    
    if not credentials:
        return False, "No calendar connected for this user"
    
    try:
        # Build the service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Parse due date and create event time
        if isinstance(due_date, datetime.date) and not isinstance(due_date, datetime.datetime):
            # If only date is provided (no time), default to 10:00 AM
            due_datetime = datetime.datetime.combine(due_date, datetime.time(10, 0))
        else:
            due_datetime = due_date
            
        # Create end time (default 1 hour duration)
        end_datetime = due_datetime + datetime.timedelta(hours=duration_hours)
        
        # Format times for Google Calendar API
        start_time = due_datetime.isoformat()
        end_time = end_datetime.isoformat()
        
        # Create event details
        event = {
            'summary': f'Chore: {chore_name}',
            'description': notes or 'Assigned chore from Chore Tracker',
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': True,
            },
        }
        
        # Add to primary calendar
        event = service.events().insert(calendarId='primary', body=event).execute()
        
        return True, f"Event created: {event.get('htmlLink')}"
    
    except Exception as e:
        # If token refresh failed or other API error
        # We might need to handle credential refresh here
        return False, f"Error creating calendar event: {str(e)}" 