import re
# api_server.py
import os
from dotenv import load_dotenv
load_dotenv()

import datetime
import json
import asyncio
import threading
import urllib.parse
import requests
from flask import Flask, request, jsonify, redirect, session
from flask_cors import CORS
from flask_sock import Sock
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import websockets

import database
import calendar_tool
from notifications import send_smtp_email, build_meeting_email_html, trigger_twilio_call

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "novavoice-super-secret-key-12345")
CORS(app, supports_credentials=True)
sock = Sock(app)

# Allow HTTP traffic for local localhost testing
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Persistent HTTP Session for fast connection reuse
nvidia_session = requests.Session()

# Initialize Database Schema
database.init_db()

from flask import send_file

@app.route('/')
def index_page():
    return send_file('index.html')

# --- LOCAL AUTHENTICATION APIs ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    phone_number = data.get('phone_number')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    try:
        user_id = database.create_user(email, password, phone_number)
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "id": user_id,
                "email": email,
                "phone_number": phone_number
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    user = database.authenticate_user(email, password)
    if user:
        return jsonify({
            "message": "Logged in successfully",
            "user": user
        })
    return jsonify({"error": "Invalid email or password"}), 401

# --- GOOGLE OAUTH FLOW APIs ---

OAUTH_VERIFIERS = {}

from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

def get_oauth_redirect_uri():
    scheme = 'https' if (request.headers.get('X-Forwarded-Proto') == 'https' or request.is_secure or 'onrender.com' in request.host) else request.scheme
    auto_uri = f"{scheme}://{request.host}/auth/callback"
    
    configured_uri = os.getenv("GOOGLE_API_REDIRECT_URI")
    if configured_uri and "your-app-name" not in configured_uri and "example.com" not in configured_uri:
        if request.host in configured_uri:
            return configured_uri
            
    return auto_uri

@app.route('/auth/login')
def auth_login():
    user_id = request.args.get('user_id')
    if not user_id:
        return "Missing user_id parameter", 400
        
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return """
        <div style="font-family:sans-serif; max-width:600px; margin:50px auto; padding:20px; border:1px solid #f87171; background:#fef2f2; border-radius:8px;">
            <h2 style="color:#dc2626;">Google OAuth Not Configured</h2>
            <p><strong>GOOGLE_CLIENT_ID</strong> or <strong>GOOGLE_CLIENT_SECRET</strong> is missing in your environment variables.</p>
            <p>Sandra is currently running in <strong>Local Calendar Fallback Mode</strong>. All meetings scheduled by voice are saved 100% reliably in your local database with Google Meet links.</p>
            <p>To enable live Google Calendar sync, add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to your environment variables.</p>
            <a href="/" style="display:inline-block; padding:10px 18px; background:#4f46e5; color:white; border-radius:6px; text-decoration:none;">Back to Sandra AI</a>
        </div>
        """, 400
        
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    scopes = [
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/tasks',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ]
    
    state = json.dumps({"user_id": int(user_id)})
    redirect_uri = get_oauth_redirect_uri()
    print(f"[OAUTH] Requesting OAuth with redirect_uri: {redirect_uri}", flush=True)
    
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=redirect_uri
    )
    auth_url, _ = flow.authorization_url(prompt='consent', state=state, access_type='offline')
    
    if hasattr(flow, 'code_verifier') and flow.code_verifier:
        OAUTH_VERIFIERS[int(user_id)] = flow.code_verifier
        session['code_verifier'] = flow.code_verifier
        
    return redirect(auth_url)

@app.route('/auth/callback')
def auth_callback():
    state_str = request.args.get('state')
    if not state_str:
        return "State parameter missing", 400
        
    try:
        state_data = json.loads(state_str)
        user_id = int(state_data.get('user_id'))
    except Exception:
        return "Invalid state parameter", 400
        
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return "Google OAuth credentials not configured", 400

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    scopes = [
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/tasks',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid'
    ]
    
    redirect_uri = get_oauth_redirect_uri()
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=redirect_uri
    )
    
    code_verifier = session.get('code_verifier') or OAUTH_VERIFIERS.get(user_id)
    if code_verifier:
        flow.code_verifier = code_verifier
    
    try:
        auth_response_url = request.url
        if (request.headers.get('X-Forwarded-Proto') == 'https' or redirect_uri.startswith('https')) and auth_response_url.startswith('http://'):
            auth_response_url = auth_response_url.replace('http://', 'https://', 1)
        
        flow.fetch_token(authorization_response=auth_response_url)
        creds = flow.credentials
        
        token_dict = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes
        }
        database.save_oauth_token(user_id, token_dict)
        
        try:
            os.makedirs('tokens', exist_ok=True)
            with open('token.json', 'w') as f:
                f.write(creds.to_json())
        except Exception as err:
            print(f"Warning: could not write token.json: {err}")
        
        target_redirect = os.getenv("FRONTEND_URL") or (f"https://{request.host}" if (request.headers.get('X-Forwarded-Proto') == 'https' or request.is_secure) else f"{request.scheme}://{request.host}")
        
        return f"""
        <div style="font-family:sans-serif; text-align:center; padding:50px;">
            <h2 style="color:#10b981;">✅ Google Calendar Synced Successfully!</h2>
            <p>Your Google Calendar is now connected to Sandra AI Voice Agent.</p>
            <p>Redirecting back to Sandra AI in 3 seconds...</p>
            <script>
                setTimeout(() => {{
                    window.location.href = "{target_redirect}/?auth_success=1";
                }}, 3000);
            </script>
        </div>
        """
    except Exception as oauth_err:
        print(f"[OAUTH ERROR] Callback failed: {oauth_err}")
        return f"""
        <div style="font-family:sans-serif; max-width:600px; margin:50px auto; padding:20px; border:1px solid #f87171; background:#fef2f2; border-radius:8px;">
            <h2 style="color:#dc2626;">Google Calendar Sync Error</h2>
            <p>Error details: <code>{str(oauth_err)}</code></p>
            <p><strong>Common Fixes:</strong></p>
            <ul>
                <li>Ensure <code>{redirect_uri}</code> is added under <strong>Authorized redirect URIs</strong> in Google Cloud Console Credentials.</li>
                <li>Verify your <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> are correct.</li>
            </ul>
            <a href="/" style="display:inline-block; padding:10px 18px; background:#4f46e5; color:white; border-radius:6px; text-decoration:none;">Back to Sandra AI</a>
        </div>
        """, 400

@app.route('/api/auth_status')
def auth_status():
    user_id = request.args.get('user_id')
    user_email = request.args.get('email')
    is_synced = False
    account_email = os.getenv("HOST_EMAIL", "mahek.aggarwal17@gmail.com")
    try:
        creds = calendar_tool.get_google_creds(user_email=user_email, user_id=user_id)
        if creds and (creds.valid or creds.refresh_token):
            is_synced = True
    except Exception:
        if os.path.exists('token.json'):
            is_synced = True

    return jsonify({
        "synced": is_synced,
        "account": account_email
    })

def execute_tool(name, args, user_id):
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    elif not isinstance(args, dict):
        args = {}

    import time
    local_tz = time.tzname[time.daylight] if time.daylight else time.tzname[0]
    
    if name == 'book_meeting':
        return calendar_tool.book_meeting(
            date_time_iso=args.get('date_time') or args.get('date_time_iso') or args.get('date'), 
            name=args.get('guest_email') or args.get('name') or 'User',
            timezone_name=args.get('timezone', local_tz),
            guest_emails=args.get('guest_emails', ''),
            duration_mins=int(args.get('duration', 30)),
            user_id=user_id,
            title=args.get('title', 'Meeting')
        )
    elif name in ['check_availability', 'check_calendar', 'get_calendar', 'list_events']:
        date_val = args.get('date') or args.get('date_iso') or args.get('date_time') or 'today'
        return calendar_tool.check_availability(
            date_iso=date_val,
            timezone_name=args.get('timezone', local_tz),
            user_id=user_id
        )
    elif name == 'send_email':
        to_email = args.get('to') or args.get('recipient') or args.get('email')
        if not to_email or to_email == 'user' or '@' not in str(to_email):
            user_obj = database.get_user_by_id(user_id) if user_id else None
            to_email = (user_obj and user_obj.get('email')) or os.getenv("HOST_EMAIL", "mahek.aggarwal17@gmail.com")
        return calendar_tool.send_email(
            to=to_email,
            subject=args.get('subject', 'Notification from Sandra AI'),
            body=args.get('body') or args.get('message') or args.get('content', ''),
            user_id=user_id
        )
    elif name == 'add_todo':
        return calendar_tool.add_todo(
            title=args.get('title', 'New Task'),
            due_date_iso=args.get('due_date') or args.get('due_date_iso') or args.get('due'),
            user_id=user_id
        )
    elif name in ['update_memory', 'update_user_memory']:
        key = args.get('key', 'info')
        val = args.get('value', 'saved')
        database.update_profile(user_id, key, val)
        return f"Saved {key} to memory."
    elif name == 'cancel_meeting':
        return calendar_tool.cancel_meeting(
            event_id_or_title=args.get('title') or args.get('meeting_id') or args.get('event_id'),
            user_id=user_id
        )
    else:
        return f"Action {name} completed."

@app.route('/api/tool_call', methods=['POST'])
def handle_generic_tool_call():
    data = request.json or {}
    tool_name = data.get('tool_name')
    tool_args = data.get('tool_args', {})
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    res = execute_tool(tool_name, tool_args, uid)
    return jsonify({"result": res})

# --- CALENDAR CRUD & ACTIONS APIs ---

@app.route('/api/book_meeting', methods=['POST'])
def handle_booking():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    print(f"\n🔔 [API REQUEST] Booking: '{data.get('title')}' for User ID {user_id}")
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    result = calendar_tool.book_meeting(
        date_time_iso=data.get('date_time'), 
        name=data.get('guest_email', 'User'),
        timezone_name=data.get('timezone', 'UTC'),
        guest_emails=data.get('guest_emails', ''),
        duration_mins=int(data.get('duration', 30)),
        user_id=uid,
        title=data.get('title')
    )
    print(f"✅ [API RESPONSE] {result}")
    
    if "Success!" in result:
        meet_link = ""
        if "Google Meet Link:" in result:
            meet_link = result.split("Google Meet Link:")[-1].strip()
            
        emails_to_notify = []
        if data.get('guest_emails'):
            emails_to_notify.extend([e.strip() for e in data.get('guest_emails').split(',') if e.strip()])
            
        host = database.get_user_by_id(uid) if uid else None
        if host and host['email']:
            emails_to_notify.append(host['email'])
            
        html_body = build_meeting_email_html(
            action="book",
            title=data.get('title', 'Meeting'),
            start_time_str=data.get('date_time'),
            timezone=data.get('timezone', 'UTC'),
            meet_link=meet_link
        )
        
        for email in set(emails_to_notify):
            send_smtp_email(email, f"Meeting Confirmed: {data.get('title', 'Meeting')}", html_body)
            
    return jsonify({"result": result})

@app.route('/api/check_availability', methods=['POST'])
def handle_availability():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    result = calendar_tool.check_availability(
        date_iso=data.get('date'),
        timezone_name=data.get('timezone', 'UTC'),
        user_id=uid
    )
    return jsonify({"result": result})

@app.route('/api/update_meeting', methods=['POST'])
def handle_update_meeting():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    result = calendar_tool.update_meeting(
        event_id=data.get('event_id'),
        new_date_time_iso=data.get('new_date_time'),
        timezone_name=data.get('timezone', 'UTC'),
        duration_mins=int(data.get('duration', 30)),
        user_id=uid
    )
    
    if "Success!" in result:
        emails_to_notify = []
        host = database.get_user_by_id(uid) if uid else None
        if host and host['email']:
            emails_to_notify.append(host['email'])
            
        html_body = build_meeting_email_html(
            action="update",
            title="Meeting Rescheduled",
            start_time_str=data.get('new_date_time'),
            timezone=data.get('timezone', 'UTC')
        )
        for email in set(emails_to_notify):
            send_smtp_email(email, "Meeting Rescheduled Notice", html_body)
            
    return jsonify({"result": result})

@app.route('/api/cancel_meeting', methods=['POST'])
def handle_cancel_meeting():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    result = calendar_tool.cancel_meeting(
        event_id=data.get('event_id'),
        user_id=uid
    )
    
    if "Success!" in result:
        emails_to_notify = []
        host = database.get_user_by_id(uid) if uid else None
        if host and host['email']:
            emails_to_notify.append(host['email'])
            
        html_body = build_meeting_email_html(
            action="cancel",
            title="Cancelled Meeting",
            start_time_str="Cancelled",
            timezone="N/A"
        )
        for email in set(emails_to_notify):
            send_smtp_email(email, "Meeting Cancelled Notice", html_body)
            
    return jsonify({"result": result})

# --- GMAIL AND TASKS APIs ---

@app.route('/api/send_email', methods=['POST'])
def handle_send_email():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    result = calendar_tool.send_email(
        to=data.get('to'),
        subject=data.get('subject'),
        body=data.get('body'),
        user_id=uid
    )
    return jsonify({"result": result})

@app.route('/api/add_todo', methods=['POST'])
def handle_add_todo():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    result = calendar_tool.add_todo(
        title=data.get('title'),
        due_date_iso=data.get('due_date'),
        user_id=uid
    )
    return jsonify({"result": result})

# --- TELEPHONY FALLBACK OUTBOUND TRIGGER ---

@app.route('/api/trigger_phone_call', methods=['POST'])
def handle_telephony_fallback():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    text = data.get('text_to_say', "Connection fallback initiated.")
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    if not uid:
        return jsonify({"error": "Invalid user identification"}), 400
        
    user_details = database.get_user_by_id(uid)
    if not user_details or not user_details.get('phone_number'):
        return jsonify({"error": "No phone number configured for this user account. Set phone_number under settings."}), 400
        
    res = trigger_twilio_call(user_details['phone_number'], text)
    return jsonify({"result": res})

# --- HISTORY & MEMORY SCOPED APIs ---

@app.route('/api/history', methods=['GET'])
def get_history_list():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify([])
    sessions = database.get_user_conversations(int(user_id))
    return jsonify(sessions)

@app.route('/api/history/session', methods=['GET'])
def get_session_chat():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify([])
    history = database.get_conversation_history(session_id)
    return jsonify(history)

@app.route('/api/get_memory', methods=['GET'])
def handle_get_memory():
    user_id = request.args.get('user_id')
    user_email = request.args.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    if not uid:
        return jsonify({"context": "New user context."})
        
    context = database.get_profile_context(uid)
    return jsonify({"context": context})

@app.route('/api/update_memory', methods=['POST'])
def handle_update_memory():
    data = request.json or {}
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    key = data.get('key')
    value = data.get('value')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    if uid:
        database.update_profile(uid, key, value)
        return jsonify({"result": f"Successfully saved {key} = {value} to memory."})
    return jsonify({"error": "Failed to update memory, invalid user."}), 400

@app.route('/api/log_conversation', methods=['POST'])
def handle_log_conversation():
    data = request.json or {}
    session_id = data.get('session_id')
    speaker = data.get('speaker')
    text = data.get('text')
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    database.log_message(session_id, speaker, text, uid)
    return jsonify({"result": "Logged turn."})

@app.route('/api/summarize_and_email', methods=['POST'])
def handle_summarize_and_email():
    data = request.json or {}
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    user_email = data.get('user_email')
    
    uid = None
    if user_id:
        uid = int(user_id)
    elif user_email:
        user = database.get_user_by_email(user_email)
        if user:
            uid = user['id']
            
    if not uid:
        return jsonify({"error": "Invalid user ID"}), 400
        
    user_details = database.get_user_by_id(uid)
    if not user_details:
        return jsonify({"error": "User details not found"}), 404
        
    history = database.get_conversation_history(session_id)
    if not history:
        return jsonify({"result": "No conversation history found."})
        
    chat_str = "\n".join([f"{speaker.upper()}: {text}" for speaker, text in history])
    
    summary_dir = "summaries"
    os.makedirs(summary_dir, exist_ok=True)
    summary_file = os.path.join(summary_dir, f"summary_{session_id}.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"NovaVoice Call Summary\nSession ID: {session_id}\n" + "-"*40 + "\n" + chat_str)
        
    send_smtp_email(
        to_email=user_details['email'],
        subject=f"NovaVoice Call Summary - Session: {session_id}",
        html_body=f"""<h3>Your Call Summary</h3>
        <p>Session ID: {session_id}</p>
        <hr/>
        <pre style="background:#f3f4f6; padding:15px; border-radius:8px; border:1px solid #e5e7eb;">{chat_str}</pre>"""
    )
    return jsonify({"result": f"Call log saved locally and summary emailed to {user_details['email']}."})

import requests

# --- NVIDIA NIM WEBSOCKET HANDLER ---

async def nvidia_proxy_handler(websocket, user_id, api_key, user_email, session_id):
    print(f"[NVIDIA PROXY] Connected user {user_id}. Starting Session: {session_id}")
    import time
    local_tz = time.tzname[time.daylight] if time.daylight else time.tzname[0]
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys_instruction = (
        "You are Sandra, a warm, professional, intelligent AI voice assistant.\n"
        f"The current local date and time is {now_str}, and your timezone is {local_tz}. Use this for all scheduling.\n"
        "Rules:\n"
        "1. Speak naturally in concise, conversational sentences (1-2 sentences) ideal for text-to-speech.\n"
        "2. NEVER read technical code lines, JSON brackets, event IDs, format symbols, or function syntax out loud.\n"
        "3. When you need to perform an action (check calendar, book meeting, send email, add task, save memory), write [TOOL_CALL: function_name({\"arg\": \"value\"})].\n"
        "4. Available tools (ALWAYS use valid JSON args):\n"
        "   - check_availability({\"date_iso\": \"YYYY-MM-DD or tomorrow/today\"})\n"
        "   - book_meeting({\"date\": \"YYYY-MM-DD\", \"time\": \"HH:MM AM/PM\", \"duration\": 30, \"title\": \"...\"})\n"
        "   - send_email({\"to_email\": \"...\", \"subject\": \"...\", \"body\": \"...\"})\n"
        "   - add_todo({\"task\": \"...\", \"due_date\": \"YYYY-MM-DD\"})\n"
        "   - update_user_memory({\"fact\": \"...\"})\n"
        "   - web_search({\"query\": \"...\"})\n"
        "5. ONLY append [END_CALL] if you are completely finished with the conversation and want to hang up. If you append [END_CALL], you MUST also say 'have a great day' in the same response. Never hang up without saying 'have a great day'."
    )
    try:
        context = database.get_profile_context(user_id)
        if context:
            sys_instruction += f"\nUser Memory & Context:\n{context}"
    except Exception as e:
        print(f"[NVIDIA PROXY] Memory context fetch error: {e}")

    messages = [{"role": "system", "content": sys_instruction}]

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except Exception:
                continue

            if "setup" in data:
                greeting = "Hello! I am Sandra, your AI voice assistant. How can I help you today?"
                messages.append({"role": "assistant", "content": greeting})
                await websocket.send(json.dumps({
                    "serverContent": {
                        "outputTranscription": {"text": greeting},
                        "modelTurn": {"parts": [{"text": greeting}]},
                        "turnComplete": True
                    }
                }))
                continue
            user_text = ""
            if "clientContent" in data:
                turns = data["clientContent"].get("turns", [])
                for turn in turns:
                    for part in turn.get("parts", []):
                        if "text" in part:
                            user_text += part["text"] + " "
            elif "text" in data:
                user_text = data["text"]

            user_text = user_text.strip()
            if not user_text:
                continue

            print(f"[NVIDIA PROXY] User ({user_id}): {user_text}")
            database.log_message(session_id, "user", user_text, user_id)
            messages.append({"role": "user", "content": user_text})

            # Loop to handle tool calls and immediate AI follow-ups without waiting for the user
            while True:
                def fetch_stream(q, loop):
                        try:
                            response = nvidia_session.post(
                                "https://integrate.api.nvidia.com/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {api_key}",
                                    "Content-Type": "application/json",
                                    "Accept": "text/event-stream"
                                },
                                json={
                                    "model": "meta/llama-3.1-8b-instruct",
                                    "messages": messages,
                                    "temperature": 0.4,
                                    "top_p": 0.9,
                                    "max_tokens": 150,
                                    "stream": True
                                },
                                stream=True,
                                timeout=(10, 60)
                            )
                            if response.status_code != 200:
                                loop.call_soon_threadsafe(q.put_nowait, ("ERR", f"HTTP {response.status_code}: {response.text}"))
                                return
                            
                            for line in response.iter_lines():
                                if line:
                                    decoded_line = line.decode('utf-8')
                                    if decoded_line.startswith("data: "):
                                        raw = decoded_line[6:]
                                        if raw == "[DONE]" or raw.strip() == "[DONE]":
                                            break
                                        try:
                                            obj = json.loads(raw)
                                            delta = obj["choices"][0]["delta"].get("content", "")
                                            if delta:
                                                loop.call_soon_threadsafe(q.put_nowait, ("CHUNK", delta))
                                        except Exception:
                                            pass
                        except Exception as err:
                            print(f"[NVIDIA PROXY] Fetch error: {err}")
                            loop.call_soon_threadsafe(q.put_nowait, ("ERR", str(err)))
                        finally:
                            loop.call_soon_threadsafe(q.put_nowait, ("DONE", None))

                q = asyncio.Queue()
                loop = asyncio.get_running_loop()
                threading.Thread(target=fetch_stream, args=(q, loop), daemon=True).start()

                full_ai_response = ""
                err_msg = None
                while True:
                    kind, val = await q.get()
                    if kind == "CHUNK":
                        full_ai_response += val
                    elif kind == "ERR":
                        err_msg = val
                    elif kind == "DONE":
                        break

                if not full_ai_response and err_msg:
                    full_ai_response = "I am sorry, I encountered a temporary issue connecting to the AI service. Please try speaking again."

                if full_ai_response:
                    is_explicit_end = any(p in user_text.lower() for p in ["end call", "hang up", "end session", "nothing else", "that's all", "thats all", "no thanks", "bye", "goodbye", "i'm done", "im done", "all done"])
                    clean_spoken = re.sub(r'\[TOOL_CALL:[\s\S]*?\]', '', full_ai_response).strip()
                    clean_spoken = re.sub(r'\[Event ID:[\s\S]*?\]', '', clean_spoken).strip()
                    clean_spoken = re.sub(r'\{[\s\S]*?\}', '', clean_spoken).strip()
                    if not is_explicit_end:
                        clean_spoken = re.sub(r'\[END_CALL\]', '', clean_spoken).strip()

                    if clean_spoken:
                        await websocket.send(json.dumps({
                            "serverContent": {
                                "outputTranscription": {"text": clean_spoken},
                                "modelTurn": {"parts": [{"text": clean_spoken}]}
                            }
                        }))

                    messages.append({"role": "assistant", "content": full_ai_response})
                    database.log_message(session_id, "model", full_ai_response, user_id)

                    if "[TOOL_CALL:" in full_ai_response:
                        try:
                            s_idx = full_ai_response.find("[TOOL_CALL:")
                            e_idx = full_ai_response.find("]", s_idx)
                            if e_idx != -1:
                                raw_call = full_ai_response[s_idx+11:e_idx].strip()
                                fn_name = raw_call.split("(")[0].strip()
                                raw_args = raw_call[len(fn_name)+1:-1].strip() if "(" in raw_call and raw_call.endswith(")") else "{}"
                                tool_res = execute_tool(fn_name, raw_args, user_id)
                                print(f"[NVIDIA TOOL EXECUTED] {fn_name} -> {tool_res}")
                                clean_tool_res = re.sub(r'\[Event ID:[\s\S]*?\]', '', str(tool_res))
                                messages.append({"role": "user", "content": f"Tool Result ({fn_name}): {clean_tool_res}\nProvide a warm, human 1-2 sentence conversational response based on this result. Do NOT repeat what you said before the tool call. Do NOT output technical syntax."})
                                # We have a tool call, so we continue the while True loop to fetch the AI's confirmation
                                continue
                        except Exception as te:
                            print(f"[NVIDIA TOOL ERROR] {te}")
                
                # If we reach here, there are no more tool calls for this turn
                break
            
            # Signal the frontend that the AI turn is fully complete (triggers TTS)
            await websocket.send(json.dumps({"serverContent": {"turnComplete": True}}))

    except Exception as ws_err:
        print(f"[NVIDIA PROXY] WSS Exception: {ws_err}")


# --- ASYNC WEBSOCKET PROXY (PORT 5001) ---

async def proxy_handler(websocket, path=None):
    if path is None:
        path = websocket.request.path
    parsed = urllib.parse.urlparse(path)
    params = urllib.parse.parse_qs(parsed.query)
    
    user_id_list = params.get('user_id')
    api_key_list = params.get('key')
    
    if not user_id_list:
        await websocket.close(1008, "Missing user_id parameter")
        return
        
    user_id = int(user_id_list[0])
    api_key = (api_key_list[0] if (api_key_list and api_key_list[0] and api_key_list[0] != "null" and api_key_list[0] != "undefined") else None) or os.getenv("NVIDIA_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        await websocket.close(1008, "Missing API Key")
        return
        
    user = database.get_user_by_id(user_id)
    user_email = user['email'] if user else "default_user"
    session_id = f"session_{int(datetime.datetime.now().timestamp())}"

    # Route to NVIDIA handler if key is NVIDIA key (nvapi-...)
    if api_key.startswith("nvapi-") or api_key.startswith("nv") or "nvidia" in api_key.lower():
        await nvidia_proxy_handler(websocket, user_id, api_key, user_email, session_id)
        return
    
    gemini_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key}"
    print(f"[PROXY] Connected user {user_id}. Starting WSS Session: {session_id}")
    
    try:
        async with websockets.connect(gemini_url) as gemini_ws:
            async def client_to_gemini():
                try:
                    async for message in websocket:
                        if isinstance(message, str) and '{"ping"' in message.replace(" ", ""):
                            continue
                        await gemini_ws.send(message)
                        
                        try:
                            if isinstance(message, str):
                                msg_json = json.loads(message)
                                if "realtimeInput" not in msg_json:
                                    if "clientContent" in msg_json:
                                        for turn in msg_json["clientContent"].get("turns", []):
                                            if turn["role"] == "user":
                                                for part in turn.get("parts", []):
                                                    if "text" in part:
                                                        database.log_message(session_id, "user", part["text"], user_id)
                        except Exception:
                            pass
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Proxy client_to_gemini exception: {e}")
                    
            async def gemini_to_client():
                try:
                    async for message in gemini_ws:
                        await websocket.send(message)
                        
                        try:
                            data = json.loads(message)
                            if "serverContent" in data:
                                model_turn = data["serverContent"].get("modelTurn", {})
                                parts = model_turn.get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        database.log_message(session_id, "model", part["text"], user_id)
                        except Exception:
                            pass
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Proxy gemini_to_client exception: {e}")
                    
            t1 = asyncio.create_task(client_to_gemini())
            t2 = asyncio.create_task(gemini_to_client())
            done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            
    except Exception as e:
        print(f"[PROXY] Connection session error: {e}")
    finally:
        print(f"[PROXY] Session {session_id} disconnected. Generating post-call email...")
        try:
            history = database.get_conversation_history(session_id)
            if history:
                chat_str = "\n".join([f"{speaker.upper()}: {text}" for speaker, text in history])
                send_smtp_email(
                    to_email=user_email,
                    subject=f"NovaVoice Auto Call Summary - Session: {session_id}",
                    html_body=f"""<h3>Your Call Transcript Summary</h3>
                    <p>Session: {session_id}</p>
                    <hr/>
                    <pre style="background:#f3f4f6; padding:15px; border-radius:8px; border:1px solid #e5e7eb;">{chat_str}</pre>"""
                )
        except Exception as sum_err:
            print(f"Failed auto email summary: {sum_err}")
            
        await websocket.close()

class FlaskSockWsAdapter:
    def __init__(self, ws):
        self.ws = ws
        self.closed = False
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        while not self.closed:
            try:
                msg = await asyncio.to_thread(self.ws.receive)
                if msg is None:
                    self.closed = True
                    raise StopAsyncIteration
                if msg == "" or msg == "ping" or msg == "pong":
                    continue
                return msg
            except StopAsyncIteration:
                raise StopAsyncIteration
            except Exception as e:
                err_str = str(e).lower()
                if "closed" in err_str or "aborted" in err_str or "bad file descriptor" in err_str or "broken pipe" in err_str:
                    self.closed = True
                    raise StopAsyncIteration
                # Non-fatal timeout or read glitch - pause briefly and continue listening
                await asyncio.sleep(0.1)
                continue
        raise StopAsyncIteration

    async def send(self, data):
        if self.closed:
            return
        try:
            await asyncio.to_thread(self.ws.send, data)
        except Exception as e:
            print(f"[WS SEND WARNING] {e}")

    async def close(self, code=1000, reason=""):
        self.closed = True
        try:
            await asyncio.to_thread(self.ws.close)
        except Exception:
            pass

@sock.route('/ws')
def unified_ws_endpoint(ws):
    user_id_val = request.args.get('user_id', '1')
    api_key_val = request.args.get('key')
    if not api_key_val or api_key_val in ["null", "undefined"]:
        api_key_val = os.getenv("NVIDIA_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    try:
        user_id = int(user_id_val)
    except Exception:
        user_id = 1
        
    user = database.get_user_by_id(user_id)
    user_email = user['email'] if user else "default_user"
    session_id = f"session_{int(datetime.datetime.now().timestamp())}"
    
    adapter = FlaskSockWsAdapter(ws)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        if api_key_val and (api_key_val.startswith("nvapi-") or api_key_val.startswith("nv") or "nvidia" in api_key_val.lower()):
            loop.run_until_complete(nvidia_proxy_handler(adapter, user_id, api_key_val, user_email, session_id))
        else:
            async def handle_gemini():
                gemini_url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={api_key_val}"
                async with websockets.connect(gemini_url) as gemini_ws:
                    async def client_to_gemini():
                        try:
                            async for message in adapter:
                                if isinstance(message, str) and '{"ping"' in message.replace(" ", ""):
                                    continue
                                await gemini_ws.send(message)
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            print(f"Proxy client_to_gemini exception: {e}")
                    async def gemini_to_client():
                        try:
                            async for message in gemini_ws:
                                await adapter.send(message)
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            print(f"Proxy gemini_to_client exception: {e}")
                    t1 = asyncio.create_task(client_to_gemini())
                    t2 = asyncio.create_task(gemini_to_client())
                    done, pending = await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)
                    for task in pending:
                        task.cancel()
            loop.run_until_complete(handle_gemini())
    except Exception as e:
        print(f"[SOCK PROXY] Exception: {e}")
    finally:
        loop.close()

async def main_websocket_proxy():
    print("[PROXY] WSS proxy listener spawned on ws://0.0.0.0:5001", flush=True)
    async with websockets.serve(proxy_handler, "0.0.0.0", 5001):
        await asyncio.Future()  # run forever

def start_websocket_proxy():
    while True:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main_websocket_proxy())
        except Exception as e:
            print(f"[PROXY RESTARTING] WebSocket proxy error: {e}", flush=True)
            import time
            time.sleep(2)

if __name__ == '__main__':
    proxy_thread = threading.Thread(target=start_websocket_proxy, daemon=True)
    proxy_thread.start()
    
    port = int(os.getenv("PORT", 5000))
    print(f"[HTTP] Unified HTTP server running on http://0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port)