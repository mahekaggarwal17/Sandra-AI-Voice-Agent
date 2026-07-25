import os
import datetime
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

import database

def get_google_creds(user_email: str = None, user_id: int = None):
    # 1. Try to load token from the database
    token_data = None
    try:
        if user_id:
            token_data = database.get_oauth_token(user_id)
        elif user_email:
            user = database.get_user_by_email(user_email)
            if user:
                token_data = database.get_oauth_token(user['id'])
    except Exception as db_err:
        print(f"⚠️ Database token fetch failed: {db_err}. Falling back to file storage.")

    if token_data:
        scopes = [
            'https://www.googleapis.com/auth/calendar.events',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/tasks'
        ]
        return Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes', scopes)
        )

    # 2. Fallback to file tokens
    os.makedirs('tokens', exist_ok=True)
    token_path = 'token.json'
    if user_email:
        token_path = f'tokens/{user_email}.json'
        if not os.path.exists(token_path) and os.path.exists('token.json'):
            token_path = 'token.json'
    elif os.path.exists('token.json'):
        token_path = 'token.json'
    else:
        token_files = [f for f in os.listdir('tokens') if f.endswith('.json')] if os.path.exists('tokens') else []
        if token_files:
            token_path = os.path.join('tokens', token_files[0])
        else:
            raise Exception("Google Account is not authenticated. Please run auth_server.py first.")
            
    scopes = [
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/tasks'
    ]
    return Credentials.from_authorized_user_file(token_path, scopes)

def get_calendar_service(user_email: str = None, user_id: int = None):
    return build('calendar', 'v3', credentials=get_google_creds(user_email, user_id))

def get_gmail_service(user_email: str = None, user_id: int = None):
    return build('gmail', 'v1', credentials=get_google_creds(user_email, user_id))

def get_tasks_service(user_email: str = None, user_id: int = None):
    return build('tasks', 'v1', credentials=get_google_creds(user_email, user_id))

def find_alternate_slots(service, date_obj, user_tz, calendar_id, working_hours_start=9, working_hours_end=18, max_slots=3):
    """
    Finds the next `max_slots` free 30-minute slots starting from date_obj in user's timezone.
    """
    now = datetime.datetime.now(user_tz)
    slots = []
    current_day = date_obj.astimezone(user_tz).date()
    
    for i in range(3):  # Check today and next 2 days
        day = current_day + datetime.timedelta(days=i)
        
        # Calculate working hours in user's timezone
        day_start = user_tz.localize(datetime.datetime.combine(day, datetime.time(working_hours_start, 0)))
        day_end = user_tz.localize(datetime.datetime.combine(day, datetime.time(working_hours_end, 0)))
        
        if i == 0:
            search_start = max(date_obj.astimezone(user_tz), day_start)
        else:
            search_start = day_start
        
        if day == now.date():
            if now > day_end:
                continue  # Past working hours today
            if now > search_start:
                # Align to next 30 minutes
                minutes = (now.minute // 30 + 1) * 30
                if minutes == 60:
                    search_start = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
                else:
                    search_start = now.replace(minute=minutes, second=0, microsecond=0)
                if search_start >= day_end:
                    continue
        
        # Query events for this day
        time_min = day_start.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        time_max = day_end.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        
        try:
            events_result = service.events().list(
                calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
        except Exception as e:
            print(f"Error fetching events for alternate slots: {e}")
            events = []
            
        busy_intervals = []
        for event in events:
            estart_raw = event['start'].get('dateTime', event['start'].get('date'))
            eend_raw = event['end'].get('dateTime', event['end'].get('date'))
            
            if 'dateTime' not in event['start']:
                estart = user_tz.localize(datetime.datetime.strptime(estart_raw, "%Y-%m-%d"))
                eend = user_tz.localize(datetime.datetime.strptime(eend_raw, "%Y-%m-%d"))
            else:
                estart = datetime.datetime.fromisoformat(estart_raw.replace('Z', '+00:00')).astimezone(user_tz)
                eend = datetime.datetime.fromisoformat(eend_raw.replace('Z', '+00:00')).astimezone(user_tz)
            busy_intervals.append((estart, eend))
            
        current_slot = search_start
        while current_slot + datetime.timedelta(minutes=30) <= day_end:
            slot_start = current_slot
            slot_end = current_slot + datetime.timedelta(minutes=30)
            
            is_busy = False
            for b_start, b_end in busy_intervals:
                if slot_start < b_end and slot_end > b_start:
                    is_busy = True
                    break
                    
            if not is_busy:
                slots.append(slot_start)
                if len(slots) >= max_slots:
                    return slots
            current_slot = slot_end
            
    return slots

def check_availability(date_iso: str = "today", timezone_name: str = "UTC", user_email: str = None, user_id: int = None) -> str:
    """Checks Google Calendar for busy slots on a specific date, and suggests alternate free slots."""
    try:
        service = get_calendar_service(user_email, user_id)
        
        try:
            user_tz = pytz.timezone(timezone_name)
        except Exception:
            user_tz = pytz.UTC
            
        now_user = datetime.datetime.now(user_tz)
        date_str = str(date_iso).lower().strip() if date_iso else 'today'
        if not date_str or date_str in ['today', 'now', 'current']:
            dt = now_user
        elif date_str == 'tomorrow':
            dt = now_user + datetime.timedelta(days=1)
        else:
            try:
                dt = datetime.datetime.fromisoformat(str(date_iso).replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = user_tz.localize(dt)
                else:
                    dt = dt.astimezone(user_tz)
            except Exception:
                try:
                    clean_str = str(date_iso).split('T')[0]
                    naive_date = datetime.datetime.strptime(clean_str[:10], "%Y-%m-%d")
                    dt = user_tz.localize(naive_date)
                except Exception:
                    dt = now_user
            
        start_of_day_local = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_local = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        start_of_day = start_of_day_local.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')
        end_of_day = end_of_day_local.astimezone(pytz.UTC).isoformat().replace('+00:00', 'Z')
        
        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")
        
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=start_of_day, timeMax=end_of_day, 
            singleEvents=True, orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        formatted_date = dt.strftime('%Y-%m-%d')
        
        # Calculate alternates
        alternates = find_alternate_slots(service, dt, user_tz, calendar_id)
        alt_str = ""
        if alternates:
            alt_lines = [f"  * {alt.strftime('%A, %b %d at %I:%M %p')} ({timezone_name})" for alt in alternates]
            alt_str = "\n\nSuggested available slots:\n" + "\n".join(alt_lines)
            
        if not events:
            return f"The calendar is completely free on {formatted_date} ({timezone_name})." + alt_str
            
        busy_times = []
        for event in events:
            estart_raw = event['start'].get('dateTime', event['start'].get('date'))
            eend_raw = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'Busy')
            
            if 'dateTime' not in event['start']:
                busy_times.append(f"- All day: {summary} [Event ID: {event.get('id')}]")
            else:
                estart_dt = datetime.datetime.fromisoformat(estart_raw.replace('Z', '+00:00')).astimezone(user_tz)
                eend_dt = datetime.datetime.fromisoformat(eend_raw.replace('Z', '+00:00')).astimezone(user_tz)
                busy_times.append(f"- Blocked from {estart_dt.strftime('%I:%M %p')} to {eend_dt.strftime('%I:%M %p')} ({summary}) [Event ID: {event.get('id')}]")
                
        return f"Existing events on {formatted_date} ({timezone_name}):\n" + "\n".join(busy_times) + alt_str
        
    except Exception as e:
        print(f"❌ CALENDAR ERROR: {e}")
        return f"Failed to check availability: {str(e)}"

def book_meeting(date_time_iso: str, name: str = "User", timezone_name: str = "UTC", user_email: str = None, guest_emails: str = "", duration_mins: int = 30, user_id: int = None, title: str = None) -> str:
    """Creates a Google Calendar meeting with optional multi-guests, Google Meet video link, and customizable duration. Checks conflicts first."""
    try:
        service = get_calendar_service(user_email, user_id)
        
        try:
            user_tz = pytz.timezone(timezone_name)
        except Exception:
            user_tz = pytz.UTC
            
        # Parse ISO datetime
        try:
            start_time = datetime.datetime.fromisoformat(date_time_iso.replace('Z', '+00:00'))
            if start_time.tzinfo is None:
                start_time = user_tz.localize(start_time)
            else:
                start_time = start_time.astimezone(user_tz)
        except ValueError:
            clean_str = date_time_iso.split('.')[0].split('+')[0].split('-')[0]
            start_time = datetime.datetime.strptime(clean_str[:19], "%Y-%m-%dT%H:%M:%S")
            start_time = user_tz.localize(start_time)
            
        end_time = start_time + datetime.timedelta(minutes=duration_mins)
        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")

        # Double booking check
        time_min = start_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        time_max = end_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=time_min, timeMax=time_max, 
            singleEvents=True
        ).execute()
        events = events_result.get('items', [])
        
        if events:
            alternates = find_alternate_slots(service, start_time, user_tz, calendar_id)
            alt_msg = ""
            if alternates:
                alt_lines = [f"  * {alt.strftime('%A, %b %d at %I:%M %p')} ({timezone_name})" for alt in alternates]
                alt_msg = "\n\nSuggested available slots:\n" + "\n".join(alt_lines)
            return f"Cannot book meeting at {start_time.strftime('%I:%M %p')} ({timezone_name}) because that slot is busy." + alt_msg

        # Parse guests
        attendees = []
        if guest_emails:
            for g in guest_emails.split(','):
                g_strip = g.strip()
                if g_strip:
                    attendees.append({'email': g_strip})

        event = {
            'summary': title or f'NovaVoice Demo: {name}',
            'description': 'Automated booking created via Gemini Live AI Calling Assistant.',
            'start': {'dateTime': start_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')},
            'end': {'dateTime': end_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')},
            'attendees': attendees,
            'conferenceData': {
                'createRequest': {
                    'requestId': f"novavoice-{int(datetime.datetime.now().timestamp())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }

        event_result = service.events().insert(
            calendarId=calendar_id, 
            body=event,
            conferenceDataVersion=1
        ).execute()
        
        html_link = event_result.get('htmlLink')
        meet_link = ""
        conf = event_result.get('conferenceData', {})
        for entry in conf.get('entryPoints', []):
            if entry.get('entryPointType') == 'video':
                meet_link = entry.get('uri')
                break
                
        print(f"✅ REAL CALENDAR BOOKING SUCCESS: {html_link}")
        
        msg = f"Success! Meeting booked on Google Calendar for {name} on {start_time.strftime('%A, %b %d at %I:%M %p')} ({timezone_name})."
        if meet_link:
            msg += f" Google Meet Link: {meet_link}"
        return msg
        
    except Exception as e:
        print(f"❌ CALENDAR ERROR: {e}")
        return f"Failed to book meeting: {str(e)}"

def update_meeting(event_id: str, new_date_time_iso: str, timezone_name: str = "UTC", user_email: str = None, duration_mins: int = 30, user_id: int = None) -> str:
    """Updates / reschedules a meeting on Google Calendar."""
    try:
        service = get_calendar_service(user_email, user_id)
        
        try:
            user_tz = pytz.timezone(timezone_name)
        except Exception:
            user_tz = pytz.UTC
            
        try:
            start_time = datetime.datetime.fromisoformat(new_date_time_iso.replace('Z', '+00:00'))
            if start_time.tzinfo is None:
                start_time = user_tz.localize(start_time)
            else:
                start_time = start_time.astimezone(user_tz)
        except ValueError:
            clean_str = new_date_time_iso.split('.')[0].split('+')[0].split('-')[0]
            start_time = datetime.datetime.strptime(clean_str[:19], "%Y-%m-%dT%H:%M:%S")
            start_time = user_tz.localize(start_time)
            
        end_time = start_time + datetime.timedelta(minutes=duration_mins)
        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")

        # Fetch event
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        event['start'] = {'dateTime': start_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')}
        event['end'] = {'dateTime': end_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')}
        
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        print(f"✅ CALENDAR UPDATE SUCCESS: {updated_event.get('htmlLink')}")
        return f"Success! Meeting rescheduled on Google Calendar to {start_time.strftime('%A, %b %d at %I:%M %p')} ({timezone_name})."
    except Exception as e:
        print(f"❌ CALENDAR UPDATE ERROR: {e}")
        return f"Failed to reschedule meeting: {str(e)}"

def cancel_meeting(event_id: str, user_email: str = None, user_id: int = None) -> str:
    """Cancels / deletes a meeting on Google Calendar."""
    try:
        service = get_calendar_service(user_email, user_id)
        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")
        
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print(f"✅ CALENDAR CANCEL SUCCESS: {event_id}")
        return "Success! Meeting has been cancelled."
    except Exception as e:
        print(f"❌ CALENDAR CANCEL ERROR: {e}")
        return f"Failed to cancel meeting: {str(e)}"

# GMAIL AND TASKS INTEGRATION
import base64
from email.mime.text import MIMEText

def send_email(to: str, subject: str, body: str, user_email: str = None, user_id: int = None) -> str:
    """Sends an email via Gmail API."""
    try:
        service = get_gmail_service(user_email, user_id)
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        send_result = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        print(f"[GMAIL SEND SUCCESS]: {send_result.get('id')}")
        return f"Successfully sent email to {to}."
    except Exception as e:
        print(f"[GMAIL ERROR]: {e}")
        return f"Failed to send email: {str(e)}"

def add_todo(title: str, due_date_iso: str = None, user_email: str = None, user_id: int = None) -> str:
    """Adds a task to Google Tasks."""
    try:
        service = get_tasks_service(user_email, user_id)
        
        tasklists_result = service.tasklists().list(maxResults=1).execute()
        tasklists = tasklists_result.get('items', [])
        if not tasklists:
            return "Failed to add todo: No task list found."
        tasklist_id = tasklists[0]['id']
        
        task = {'title': title}
        if due_date_iso:
            task['due'] = due_date_iso
            
        task_result = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
        print(f"✅ GOOGLE TASKS SUCCESS: {task_result.get('title')}")
        return f"Successfully added to-do: '{title}'."
    except Exception as e:
        print(f"❌ GOOGLE TASKS ERROR: {e}")
        return f"Failed to add to-do: {str(e)}"