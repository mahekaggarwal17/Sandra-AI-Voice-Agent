# auth_server.py
import os
from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# Allow HTTP traffic for local localhost testing
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)

# Build the config dynamically from your .env file
client_config = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# Scopes needed for Calendar, Gmail, Tasks, and OpenID userinfo
SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# Set up the OAuth flow
flow = Flow.from_client_config(
    client_config,
    scopes=SCOPES,
    redirect_uri=os.getenv("GOOGLE_AUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")
)

@app.route('/')
def index():
    auth_url, _ = flow.authorization_url(prompt='consent')
    return f'<h2>AI Calling Assistant</h2><a href="{auth_url}">Click here to Authorize Google Calendar & Workspace</a>'

@app.route('/auth/callback')
def callback():
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    
    # Retrieve the user's email
    try:
        user_info_service = build('oauth2', 'v2', credentials=creds)
        user_info = user_info_service.userinfo().get().execute()
        email = user_info.get('email', 'default_user')
    except Exception as e:
        print(f"Failed to fetch user email: {e}")
        email = "default_user"
        
    os.makedirs('tokens', exist_ok=True)
    token_file = f'tokens/{email}.json'
    with open(token_file, 'w') as f:
        f.write(creds.to_json())
        
    # Also write default token.json for backward compatibility
    with open('token.json', 'w') as f:
        f.write(creds.to_json())
        
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:8000")
    
    return f"""
    <h2>Success!</h2>
    <p>Authenticated as: <strong>{email}</strong></p>
    <p>Credentials saved. Redirecting to the NovaVoice dashboard...</p>
    <script>
        setTimeout(() => {{
            window.location.href = "{frontend_url}/?user={email}";
        }}, 3000);
    </script>
    """

if __name__ == '__main__':
    print("🚀 Starting local auth server...")
    print("👉 Open http://localhost:8000 in your browser to log in.")
    app.run(port=8000)