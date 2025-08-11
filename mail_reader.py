from collections import defaultdict

import base64
import re

from agent import process_email
from mail_sender import send_email
import state

def mail_history_list(gmail_service, mail):
    history = gmail_service.users().messages().list(
    userId='me',
    q=mail,
    maxResults=10  # optional: limit number of results
    ).execute()

    return history


def decode_base64(data):
    return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('UTF-8', errors='replace')

def extract_message_body(payload):
    """Recursively extract text/plain or text/html body from a Gmail message payload."""
    if 'parts' in payload:
        for part in payload['parts']:
            mime_type = part.get('mimeType', '')
            # Look for plain text first
            if mime_type == 'text/plain' and 'data' in part['body']:
                return decode_base64(part['body']['data'])
            # Fallback to HTML
            elif mime_type == 'text/html' and 'data' in part['body']:
                html = decode_base64(part['body']['data'])
                return re.sub(r'<[^>]+>', '', html)  # strip HTML tags
            else:
                # Recursively check nested parts
                text = extract_message_body(part)
                if text:
                    return text
    else:
        # Single-part message
        if 'data' in payload['body']:
            return decode_base64(payload['body']['data'])


# --- Fetch and Save New Emails ---
def fetch_new_emails(gmail_service, GMAIL_USER_ID, lock, notification_history_id):

    start_history_id = state.get_last_history_id()

    results = gmail_service.users().history().list(
        userId=GMAIL_USER_ID,
        startHistoryId=start_history_id,
        historyTypes=['messageAdded']
    ).execute()

    histories = results.get('history', [])

    if not histories:
        return {}
    
    new_mails = defaultdict(list)
    
    for record in histories:
        for msg in record.get('messages', []):
            msg_id = msg['id']

            # Fetch minimal info to get sender quickly
            msg_detail = gmail_service.users().messages().get(
                userId=GMAIL_USER_ID,
                id=msg_id,
                format='metadata',
                metadataHeaders=['From', 'Subject', 'To', 'Cc', 'Bcc', 'Date', 'Message-ID', 'LabelIds']
            ).execute()

            # Check labels from msg_detail, not from msg
            label_ids = msg_detail.get('labelIds', [])
            if 'SENT' in label_ids or 'TRASH' in label_ids:
                print(f"⏩ Skipping sent or trashed mail with ID: {msg_id}")
                continue

            headers = msg_detail.get('payload', {}).get('headers', [])

            from_header = next((h['value'] for h in headers if h['name'] == 'From'), None)
            if from_header and "kaan200277@gmail.com" in from_header.lower():
                print(f"⏩ Skipping sent email from self: {from_header}")
                continue

            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')

            if from_header:
                new_mails[from_header].append(subject)

    state.set_last_history_id(notification_history_id)

    return new_mails


def extract_mail_history_from_sender(gmail_service, GMAIL_USER_ID, new_mails):

    """ for msg_id in new_messages:
        msg = gmail_service.users().messages().get(userId=GMAIL_USER_ID, id=msg_id).execute()

        headers = msg['payload'].get('headers', [])

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
        snippet = msg.get('snippet', '')

        print(f"📨 From: {sender} | Subject: {subject} | Snippet: {snippet}")
    """
    for e_mail in new_mails:
        # The query to find emails from this sender
        # If sender contains name + email, extract email part for query
        email_match = re.search(r'<(.+?)>', e_mail)
        query_email = email_match.group(1) if email_match else e_mail

        history = mail_history_list(gmail_service, f'from:{query_email}')
        messages = history.get('messages', [])

        message_history = []
        #print(f"\n🕑 Last 10 messages from {query_email}:")
        for m in messages:
            msg_id = m['id']
            msg = gmail_service.users().messages().get(
                userId=GMAIL_USER_ID, 
                id=msg_id,
                format='full',
                ).execute()
            

            if 'SENT' in msg.get('labelIds', []):
                print(f"⏩ Skipping sent mail with ID: {msg_id}")
                continue

            from_header = next(
            (h['value'] for h in msg['payload']['headers'] if h['name'] == 'From'),
            None
            )
            if from_header and "kaan200277@gmail.com" in from_header.lower():
                print(f"⏩ Skipping sent email from self: {from_header}")
                continue

            headers = msg['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')

            full_bodys = extract_message_body(msg['payload'])
            mail = f"{subject}: {full_bodys}"

            message_history.append(mail)
        
        print(e_mail)
        print(message_history)

        llm_structured_response_subject, llm_structured_response_body = process_email(e_mail, message_history)
        print(llm_structured_response_subject)
        print(llm_structured_response_body)
        

        send_email(gmail_service, e_mail, llm_structured_response_subject, llm_structured_response_body)