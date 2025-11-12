from agents import function_tool
import imaplib
import email
from email.header import decode_header
import sqlite3
from flask import session

IMAP_SERVER = None
EMAIL_USER = None
EMAIL_PASS = None

def init_data():
    
    global IMAP_SERVER
    global EMAIL_USER
    global EMAIL_PASS
    username = session.get("username", None)

    with sqlite3.connect("/tmp/database.db") as conn:
            user = conn.execute("""
                SELECT email, email_password, imap_server, smtp_server, imap_port, smtp_port
                FROM users WHERE username=?
            """, (username,)).fetchone()

    IMAP_SERVER = user[2]
    EMAIL_USER = user[0]
    EMAIL_PASS = user[1]



def connect_mailbox():
    init_data()
    """Verbindung zum IMAP-Server herstellen und Inbox wählen"""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    return mail


def parse_email(msg_bytes):
    """Hilfsfunktion: Mail-Daten extrahieren"""
    msg = email.message_from_bytes(msg_bytes)

    # Betreff decodieren
    subject, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")

    from_ = msg.get("From")

    # Body extrahieren
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

    return {"from": from_, "subject": subject, "body": body}


@function_tool()
async def email_lesen(von: str , limit:int) -> None:
    print("email wird gelesnen")
    mail = connect_mailbox()
    status, messages = mail.search(None, f'(FROM "{von}")')

    email_ids = messages[0].split()
    # nur die letzten `limit` Mails (neueste zuerst)
    latest_ids = email_ids[::-1][:limit]

    emails = []
    for num in latest_ids:
        _, msg_data = mail.fetch(num, "(RFC822)")
        emails.append(parse_email(msg_data[0][1]))

    mail.logout()
    print(emails)
    return emails

@function_tool()
async def ungelesene_email_lesen() -> None:
    print("unemail wird gelesnen")
    try:
        mail = connect_mailbox()
        status, messages = mail.search(None, "UNSEEN")

        emails = []
        for num in messages[0].split():
            _, msg_data = mail.fetch(num, "(RFC822)")
            emails.append(parse_email(msg_data[0][1]))

        mail.logout()
        print(emails)
        return emails
    except Exception as e:
        print(e)
        return(e)
    