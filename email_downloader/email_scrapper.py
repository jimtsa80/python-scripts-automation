import os
import base64
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email import message_from_bytes

# Gmail API scope: read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Authenticate the user and return the Gmail API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def get_email_messages(service, query):
    """Retrieve all messages matching the query."""
    messages = []
    response = service.users().messages().list(userId='me', q=query).execute()
    if 'messages' in response:
        messages.extend(response['messages'])

    while 'nextPageToken' in response:
        response = service.users().messages().list(
            userId='me', q=query, pageToken=response['nextPageToken']
        ).execute()
        if 'messages' in response:
            messages.extend(response['messages'])

    return messages

def extract_plain_text(service, msg_id):
    """Extract plain text body from an email message."""
    msg = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
    raw_msg = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
    mime_msg = message_from_bytes(raw_msg)

    body = ''
    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            if part.get_content_type() == 'text/plain':
                charset = part.get_content_charset() or 'utf-8'
                try:
                    body += part.get_payload(decode=True).decode(charset, errors='ignore')
                except:
                    continue
    else:
        charset = mime_msg.get_content_charset() or 'utf-8'
        body = mime_msg.get_payload(decode=True).decode(charset, errors='ignore')

    return body.strip()

def main():
    service = authenticate_gmail()

    # Define the date range: last 30 days from today
    today = datetime.date.today()
    past_30 = today - datetime.timedelta(days=30)
    query = f"after:{past_30.strftime('%Y/%m/%d')} before:{(today + datetime.timedelta(days=1)).strftime('%Y/%m/%d')}"

    # Fetch emails based on the query
    messages = get_email_messages(service, query)
    print(f"Found {len(messages)} emails.")

    # Extract body from each email
    all_bodies = []
    for msg in messages:
        try:
            body = extract_plain_text(service, msg['id'])
            if body:
                all_bodies.append(body)
        except Exception as e:
            print(f"Error processing message: {e}")

    # Save all email bodies to a single text file
    with open("emails_last_30_days.txt", "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_bodies))

    print("✅ File 'emails_last_30_days.txt' created successfully.")

if __name__ == '__main__':
    main()