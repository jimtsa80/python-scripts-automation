import imaplib
import email
from email.header import decode_header
import os
from datetime import datetime

# Function to clean email subjects
def clean(text):
    return "".join(c if c.isalnum() else "_" for c in text)

# Connect to the email server
def download_json_files(username, password, mail_server, date_from, date_to, download_path):
    # Connect to the server and log in
    mail = imaplib.IMAP4_SSL(mail_server)
    mail.login(username, password)

    # Select the mailbox you want to use
    mail.select("inbox")

    # Search emails within the date range
    date_from = datetime.strptime(date_from, "%d-%b-%Y").strftime("%d-%b-%Y")
    date_to = datetime.strptime(date_to, "%d-%b-%Y").strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'SINCE {date_from}', f'BEFORE {date_to}')
    
    # Create download folder if it doesn't exist
    os.makedirs(download_path, exist_ok=True)

    # Iterate through messages
    for msg_num in messages[0].split():
        status, msg_data = mail.fetch(msg_num, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()

                if msg.is_multipart():
                    for part in msg.walk():
                        # Check if the part is an attachment
                        if part.get_content_disposition() == "attachment":
                            filename = part.get_filename()
                            if filename and filename.endswith(".json"):
                                # Save the JSON file
                                filepath = os.path.join(download_path, clean(filename))
                                with open(filepath, "wb") as f:
                                    f.write(part.get_payload(decode=True))
                                print(f"Downloaded: {filename}")

    # Close the connection and logout
    mail.close()
    mail.logout()

# User inputs
username = "jimtsarouhas@hotmail.com"
password = "kanithos3###"
mail_server = "imap.gmail.com"  # e.g., "imap.gmail.com" for Gmail
date_from = "26-Jan-2025"
date_to = "26-Jan-2025"
download_path = "."

download_json_files(username, password, mail_server, date_from, date_to, download_path)
