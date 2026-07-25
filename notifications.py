# notifications.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_smtp_email(to_email: str, subject: str, html_body: str) -> bool:
    """Sends an email using standard SMTP with smtplib."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
        print("[WARN] SMTP credentials not fully configured in .env. Skipping SMTP email.")
        print(f"--- MOCK SMTP EMAIL TO: {to_email} ---")
        print(f"Subject: {subject.encode('ascii', 'replace').decode('ascii')}")
        print(f"Body: {html_body[:200].encode('ascii', 'replace').decode('ascii')}...")
        print("---------------------------------------")
        return False
        
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = to_email
        
        part = MIMEText(html_body, 'html')
        msg.attach(part)
        
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, to_email, msg.as_string())
        server.quit()
        print(f"[OK] SMTP Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] SMTP Email error: {e}")
        return False

def build_meeting_email_html(action: str, title: str, start_time_str: str, timezone: str, meet_link: str = "", cal_link: str = "") -> str:
    """Builds a beautifully styled HTML email template matching the Glassmorphism/NovaVoice premium look."""
    action_color = "#10b981" # Emerald green for booking
    action_label = "Booked"
    if "reschedule" in action.lower() or "update" in action.lower():
        action_color = "#3b82f6" # Blue
        action_label = "Rescheduled"
    elif "cancel" in action.lower() or "delete" in action.lower():
        action_color = "#ef4444" # Red
        action_label = "Cancelled"
        
    meet_btn = ""
    if meet_link and action_label != "Cancelled":
        meet_btn = f'''
        <div style="margin: 25px 0;">
            <a href="{meet_link}" target="_blank" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.2);">
                Join Google Meet
            </a>
        </div>
        '''
        
    cal_btn = ""
    if cal_link:
        cal_btn = f'''
        <p style="margin-top: 15px;">
            <a href="{cal_link}" target="_blank" style="color: #60a5fa; text-decoration: underline; font-size: 14px;">
                View on Google Calendar
            </a>
        </p>
        '''

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #0b0f19;
                color: #f3f4f6;
                margin: 0;
                padding: 20px;
            }}
            .card {{
                max-width: 600px;
                margin: 20px auto;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 30px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            }}
            .badge {{
                display: inline-block;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
                background-color: {action_color}22;
                color: {action_color};
                border: 1px solid {action_color}44;
                margin-bottom: 20px;
            }}
            h1 {{
                font-size: 24px;
                margin: 0 0 10px 0;
                color: #ffffff;
            }}
            .details {{
                margin: 20px 0;
                padding: 15px;
                background: rgba(255, 255, 255, 0.02);
                border-radius: 8px;
                border-left: 4px solid {action_color};
                text-align: left;
            }}
            .details p {{
                margin: 8px 0;
                font-size: 16px;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #6b7280;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <span class="badge">{action_label}</span>
            <h1>Meeting Notification</h1>
            <p style="color: #9ca3af; font-size: 16px;">Your schedule has been updated by NovaVoice Assistant.</p>
            
            <div class="details">
                <p><strong>Event:</strong> {title}</p>
                <p><strong>Time:</strong> {start_time_str}</p>
                <p><strong>Timezone:</strong> {timezone}</p>
            </div>
            
            {meet_btn}
            {cal_btn}
            
            <div class="footer">
                <p>This is an automated message from NovaVoice Pro Platform.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# TWILIO TELEPHONY FALLBACK
def trigger_twilio_call(to_phone: str, text_to_say: str) -> str:
    """Triggers an outbound phone call using Twilio Voice API. Falls back to simulated mock logs if keys are missing."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_phone = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not all([account_sid, auth_token, from_phone]):
        # Mock Telephony Mode
        print("\n" + "="*50)
        print("[MOCK] --- MOCK TELEPHONY OUTBOUND CALL ---")
        print(f"Dialing User at: {to_phone}")
        print(f"Synthesized Speech (TwiML):")
        print(f'  "Hello! This is your NovaVoice calling assistant fallback. {text_to_say.encode("ascii", "replace").decode("ascii")}"')
        print("SIMULATION: Outbound phone call dialed and successfully answered by user.")
        print("="*50 + "\n")
        return f"[MOCK SUCCESS] Simulated call to {to_phone} successful. Read: '{text_to_say}'"
        
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        
        twiml = f'''<Response>
            <Say voice="alice" language="en-US">Hello! {text_to_say}</Say>
            <Pause length="1"/>
            <Say voice="alice" language="en-US">Goodbye and take care!</Say>
        </Response>'''
        
        call = client.calls.create(
            twiml=twiml,
            to=to_phone,
            from_=from_phone
        )
        print(f"[OK] TWILIO CALL TRIGGERED: {call.sid}")
        return f"Outbound call successfully placed. Call SID: {call.sid}"
    except Exception as e:
        print(f"[ERROR] TWILIO CALL ERROR: {e}")
        return f"Failed to place Twilio call: {str(e)}"
