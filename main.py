from fastapi import FastAPI, Request
from google.auth.transport.requests import Request as GoogleRequest
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from apscheduler.schedulers.background import BackgroundScheduler

import base64
import json
import threading

from agent import process_email
from mail_reader import fetch_new_emails, extract_mail_history_from_sender
import state

app = FastAPI()

# --- App Configuration ---
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
    ]
TOPIC_NAME = 'projects/email-ai-agent-466215/topics/gmail-webhook-topic'  # <-- Replace
GMAIL_USER_ID = 'me'

# --- Global Variables ---
creds = None
gmail_service = None
lock = threading.Lock()

# --- Gmail Setup ---
def init_gmail():
    global creds, gmail_service
    if creds and creds.valid:
        return
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
    gmail_service = build('gmail', 'v1', credentials=creds)

    response = gmail_service.users().watch(
        userId=GMAIL_USER_ID,
        body={
            'labelIds': ['INBOX'],
            'topicName': TOPIC_NAME
        }
    ).execute()

    state.set_last_history_id(response['historyId'])
    last_history_id = state.get_last_history_id()

    print("Watch set with historyId:", last_history_id)
        

# --- Webhook Endpoint ---
@app.post("/webhook")
async def gmail_webhook(request: Request):
    data = await request.json()
    try:
        message_data = base64.b64decode(data['message']['data']).decode('utf-8')
        notification = json.loads(message_data)
        print("📥 Notification received:", notification)
        notificationId = notification['historyId']
        new_mails = fetch_new_emails(gmail_service, GMAIL_USER_ID, lock, notificationId)

        if new_mails:  # Only process if there are actually new messages
            extract_mail_history_from_sender(gmail_service, GMAIL_USER_ID, new_mails)
    except Exception as e:
        print("❌ Error processing webhook:", e)
    return {"status": "ok"}

# --- Scheduler to Renew Watch Every 6 Days ---
scheduler = BackgroundScheduler()

def rewatch_job():
    print("🔁 Re-registering Gmail watch...")
    init_gmail()

scheduler.add_job(rewatch_job, 'interval', days=6)
scheduler.start()

# --- Start Gmail Setup ---
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting app and setting Gmail watch...")
    init_gmail()
