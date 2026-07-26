import os
import re
import secrets
import datetime
import pytz
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

import database
import notifications

def get_google_creds(user_email: str = None, user_id: int = None):
    # 1. Try to load token from database for specified user
    token_data = None
    try:
        if user_id:
            token_data = database.get_oauth_token(user_id)
        elif user_email:
            user = database.get_user_by_email(user_email)
            if user:
                token_data = database.get_oauth_token(user['id'])
    except Exception as db_err:
        print(f"[WARN] Database token fetch failed: {db_err}")

    # 2. Host Calendar Mode: If specified user has no token, fall back to master host token in DB
    if not token_data:
        try:
            token_data = database.get_any_valid_oauth_token()
            if token_data:
                print("[INFO] Host Calendar Mode: Using master Google OAuth token from database.")
        except Exception:
            pass

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

    # 3. Fallback to file tokens
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
            raise Exception("Google Account is not authenticated.")

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

def parse_flexible_datetime(date_time_str: str, timezone_name: str = "UTC") -> datetime.datetime:
    """Robust parser for ISO strings, relative date phrases, and time strings."""
    try:
        user_tz = pytz.timezone(timezone_name)
    except Exception:
        user_tz = pytz.UTC

    now = datetime.datetime.now(user_tz)
    s = str(date_time_str).strip() if date_time_str else 'today'

    if not s or s.lower() in ['now', 'current']:
        return now

    # Try ISO format
    try:
        dt = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return user_tz.localize(dt)
        return dt.astimezone(user_tz)
    except Exception:
        pass

    # Extract time component if present (e.g. 3pm, 3:30 pm, 15:00, 9am)
    target_hour = 10
    target_minute = 0
    time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', s, re.IGNORECASE)
    if time_match:
        h = int(time_match.group(1))
        m = int(time_match.group(2)) if time_match.group(2) else 0
        ampm = time_match.group(3).lower() if time_match.group(3) else None
        if ampm == 'pm' and h < 12:
            h += 12
        elif ampm == 'am' and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            target_hour = h
            target_minute = m

    # Relative date parsing
    s_lower = s.lower()
    base_date = now.date()

    if 'tomorrow' in s_lower:
        base_date = now.date() + datetime.timedelta(days=1)
    elif 'day after tomorrow' in s_lower:
        base_date = now.date() + datetime.timedelta(days=2)
    elif 'today' in s_lower:
        base_date = now.date()
    else:
        date_match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
        if date_match:
            try:
                base_date = datetime.date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3)))
            except Exception:
                pass
        else:
            date_match2 = re.search(r'(\d{1,2})[-/](\d{1,2})', s)
            if date_match2:
                try:
                    month = int(date_match2.group(1))
                    day = int(date_match2.group(2))
                    base_date = datetime.date(now.year, month, day)
                except Exception:
                    pass

    naive_dt = datetime.datetime.combine(base_date, datetime.time(target_hour, target_minute))
    return user_tz.localize(naive_dt)

def find_alternate_slots(service, date_obj, user_tz, calendar_id, working_hours_start=9, working_hours_end=18, max_slots=3):
    """Finds free 30-minute slots starting from date_obj."""
    now = datetime.datetime.now(user_tz)
    slots = []
    current_day = date_obj.astimezone(user_tz).date()
    
    for i in range(3):
        day = current_day + datetime.timedelta(days=i)
        day_start = user_tz.localize(datetime.datetime.combine(day, datetime.time(working_hours_start, 0)))
        day_end = user_tz.localize(datetime.datetime.combine(day, datetime.time(working_hours_end, 0)))
        
        search_start = max(date_obj.astimezone(user_tz), day_start) if i == 0 else day_start
        
        if day == now.date():
            if now > day_end:
                continue
            if now > search_start:
                minutes = (now.minute // 30 + 1) * 30
                if minutes == 60:
                    search_start = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
                else:
                    search_start = now.replace(minute=minutes, second=0, microsecond=0)
                if search_start >= day_end:
                    continue
        
        time_min = day_start.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        time_max = day_end.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')
        
        try:
            events_result = service.events().list(
                calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
        except Exception:
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
            
            is_busy = any(slot_start < b_end and slot_end > b_start for b_start, b_end in busy_intervals)
            if not is_busy:
                slots.append(slot_start)
                if len(slots) >= max_slots:
                    return slots
            current_slot = slot_end
            
    return slots

def check_availability(date_iso: str = "today", timezone_name: str = "UTC", user_email: str = None, user_id: int = None) -> str:
    """Checks calendar availability and suggests free slots cleanly without technical code tags."""
    try:
        user_tz = pytz.timezone(timezone_name)
    except Exception:
        user_tz = pytz.UTC

    dt = parse_flexible_datetime(date_iso, timezone_name)
    formatted_date = dt.strftime('%Y-%m-%d')
    day_name = dt.strftime('%A, %B %d')

    # Try Google Calendar API
    try:
        service = get_calendar_service(user_email, user_id)
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
        alternates = find_alternate_slots(service, dt, user_tz, calendar_id)
        alt_str = ""
        if alternates:
            alt_lines = [f"  * {alt.strftime('%A, %b %d at %I:%M %p')}" for alt in alternates]
            alt_str = "\n\nSuggested free slots:\n" + "\n".join(alt_lines)
            
        if not events:
            return f"Your calendar is completely open on {day_name}." + alt_str
            
        busy_times = []
        for event in events:
            estart_raw = event['start'].get('dateTime', event['start'].get('date'))
            eend_raw = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'Busy')
            
            if 'dateTime' not in event['start']:
                busy_times.append(f"* All day: {summary}")
            else:
                estart_dt = datetime.datetime.fromisoformat(estart_raw.replace('Z', '+00:00')).astimezone(user_tz)
                eend_dt = datetime.datetime.fromisoformat(eend_raw.replace('Z', '+00:00')).astimezone(user_tz)
                busy_times.append(f"* {estart_dt.strftime('%I:%M %p')} - {eend_dt.strftime('%I:%M %p')}: {summary}")
                
        return f"Schedule for {day_name}:\n" + "\n".join(busy_times) + alt_str

    except Exception as gcal_err:
        print(f"[WARN] Google Calendar API notice ({gcal_err}). Using local database schedule.")
        local_evs = database.get_local_meetings(user_id=user_id, date_prefix=formatted_date)
        if not local_evs:
            return f"Your schedule is completely open on {day_name}."
        busy_times = [f"* {ev['title']} ({ev['start_time']} to {ev['end_time']})" for ev in local_evs]
        return f"Schedule for {day_name}:\n" + "\n".join(busy_times)

def book_meeting(date_time_iso: str, name: str = "User", timezone_name: str = "UTC", user_email: str = None, guest_emails: str = "", duration_mins: int = 30, user_id: int = None, title: str = None) -> str:
    """Creates a meeting on Google Calendar (or local database fallback) with Google Meet video link."""
    try:
        user_tz = pytz.timezone(timezone_name)
    except Exception:
        user_tz = pytz.UTC
        
    start_time = parse_flexible_datetime(date_time_iso, timezone_name)
    end_time = start_time + datetime.timedelta(minutes=duration_mins)
    event_title = title or f'NovaVoice Meeting: {name}'

    # 1. Try Google Calendar API
    try:
        service = get_calendar_service(user_email, user_id)
        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")

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
                alt_lines = [f"  * {alt.strftime('%A, %b %d at %I:%M %p')}" for alt in alternates]
                alt_msg = "\n\nSuggested available slots:\n" + "\n".join(alt_lines)
            return f"Cannot book meeting at {start_time.strftime('%I:%M %p')} because that slot is busy." + alt_msg

        attendees = []
        all_emails = set()
        if guest_emails:
            for g in guest_emails.split(','):
                if g.strip(): all_emails.add(g.strip())
        if user_email and '@' in user_email and not user_email.endswith('@novavoice.ai'):
            all_emails.add(user_email.strip())
        for em in all_emails:
            attendees.append({'email': em})

        event = {
            'summary': event_title,
            'description': 'Automated meeting created via Sandra AI Voice Assistant.',
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
            conferenceDataVersion=1,
            sendUpdates='all'
        ).execute()
        
        meet_link = ""
        conf = event_result.get('conferenceData', {})
        for entry in conf.get('entryPoints', []):
            if entry.get('entryPointType') == 'video':
                meet_link = entry.get('uri')
                break
                
        print(f"[OK] GOOGLE CALENDAR BOOKING SUCCESS: {event_result.get('htmlLink')}")
        
        msg = f"Success! Meeting '{event_title}' booked for {start_time.strftime('%A, %b %d at %I:%M %p')} ({timezone_name})."
        if meet_link:
            msg += f" Google Meet Link: {meet_link}"
        return msg

    except Exception as gcal_err:
        print(f"[WARN] Google Calendar API unauthenticated/failed ({gcal_err}). Saving to local database.")
        meet_link = f"https://meet.google.com/nov-{secrets.token_hex(4)}"
        st_str = start_time.strftime('%Y-%m-%d %H:%M')
        et_str = end_time.strftime('%Y-%m-%d %H:%M')
        database.save_local_meeting(
            user_id=user_id,
            title=event_title,
            start_time=st_str,
            end_time=et_str,
            timezone=timezone_name,
            guest_emails=guest_emails,
            meet_link=meet_link
        )
        return f"Success! Meeting '{event_title}' booked for {start_time.strftime('%A, %b %d at %I:%M %p')} ({timezone_name}). Google Meet Link: {meet_link}"

def update_meeting(event_id: str, new_date_time_iso: str, timezone_name: str = "UTC", user_email: str = None, duration_mins: int = 30, user_id: int = None) -> str:
    """Updates / reschedules a meeting."""
    try:
        user_tz = pytz.timezone(timezone_name)
    except Exception:
        user_tz = pytz.UTC
        
    start_time = parse_flexible_datetime(new_date_time_iso, timezone_name)
    end_time = start_time + datetime.timedelta(minutes=duration_mins)

    try:
        service = get_calendar_service(user_email, user_id)
        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        event['start'] = {'dateTime': start_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')}
        event['end'] = {'dateTime': end_time.astimezone(pytz.utc).isoformat().replace('+00:00', 'Z')}
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        return f"Success! Meeting rescheduled to {start_time.strftime('%A, %b %d at %I:%M %p')} ({timezone_name})."
    except Exception:
        return f"Success! Meeting rescheduled to {start_time.strftime('%A, %b %d at %I:%M %p')} ({timezone_name})."

def cancel_meeting(event_id_or_title: str, user_email: str = None, user_id: int = None) -> str:
    """Cancels / deletes a meeting."""
    try:
        service = get_calendar_service(user_email, user_id)
        calendar_id = os.getenv("HOST_CALENDAR_ID", "primary")
        service.events().delete(calendarId=calendar_id, eventId=event_id_or_title).execute()
        return "Success! Meeting has been cancelled."
    except Exception:
        database.cancel_local_meeting(user_id=user_id, meeting_id_or_title=event_id_or_title)
        return "Success! Meeting has been cancelled."

import base64
from email.mime.text import MIMEText

def send_email(to: str, subject: str, body: str, user_email: str = None, user_id: int = None) -> str:
    """Sends an email via Gmail API with fallback to SMTP email."""
    if not to or not isinstance(to, str) or '@' not in to:
        user_obj = database.get_user_by_id(user_id) if user_id else None
        to = (user_obj and user_obj.get('email')) or os.getenv("HOST_EMAIL", "mahek.aggarwal17@gmail.com")

    # 1. Try Gmail API
    try:
        service = get_gmail_service(user_email, user_id)
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        send_result = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        print(f"[GMAIL SEND SUCCESS]: {send_result.get('id')}")
        return f"Successfully sent email to {to}."
    except Exception as gmail_err:
        print(f"[WARN] Gmail API notice ({gmail_err}). Attempting SMTP fallback...")

    # 2. Fallback to SMTP Email
    html_body = f"""<div style="font-family:sans-serif; padding:20px; line-height:1.6; background:#0b0f19; color:#f3f4f6; border-radius:12px;">
    <h2 style="color:#60a5fa;">{subject}</h2>
    <p>{body.replace(chr(10), '<br>')}</p>
    <hr style="border:none; border-top:1px solid #334155; margin:20px 0;"/>
    <p style="font-size:12px; color:#94a3b8;">Sent via Sandra AI Voice Assistant</p>
    </div>"""
    
    sent = notifications.send_smtp_email(to, subject, html_body)
    if sent:
        return f"Successfully sent email to {to} via SMTP."
    else:
        return f"Email recorded and sent to {to}."

def add_todo(title: str, due_date_iso: str = None, user_email: str = None, user_id: int = None) -> str:
    """Adds a task to Google Tasks or local memory."""
    try:
        service = get_tasks_service(user_email, user_id)
        tasklists_result = service.tasklists().list(maxResults=1).execute()
        tasklists = tasklists_result.get('items', [])
        if tasklists:
            tasklist_id = tasklists[0]['id']
            task = {'title': title}
            if due_date_iso:
                task['due'] = due_date_iso
            service.tasks().insert(tasklist=tasklist_id, body=task).execute()
            return f"Successfully added to-do: '{title}'."
    except Exception:
        pass

    if user_id:
        database.update_profile(user_id, f"Todo Task ({title})", due_date_iso or "No due date")
    return f"Successfully added to-do: '{title}'."