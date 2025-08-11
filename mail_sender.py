import base64, re
from email.mime.text import MIMEText

def send_email(gmail_service, recipient_email, subject, body_text):
    """
    Sends an email via Gmail API.

    gmail_service: authenticated Gmail API service object
    sender_email: your Gmail address
    recipient_email: target address to send the mail
    subject: email subject
    body_text: email body
    """
    # Extract plain email from "Name <email>" format
    match = re.search(r"<(.+?)>", recipient_email)
    if match:
        recipient_email = match.group(1)

    # Basic validation
    recipient_email = recipient_email.strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", recipient_email):
        raise ValueError(f"❌ Invalid recipient email: {recipient_email}")
    
    # Create MIMEText email
    message = MIMEText(body_text)
    message['to'] = recipient_email
    message['subject'] = subject

    # Encode the message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    # Send it
    sent_message = gmail_service.users().messages().send(
        userId="me",  # "me" means the authenticated account
        body={'raw': raw_message}
    ).execute()

    print(f"✅ Email sent to {recipient_email} (ID: {sent_message['id']})")
    return sent_message

