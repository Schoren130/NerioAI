from agents import function_tool  # type: ignore
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
from flask import session

SMTP_SERVER = None
SMTP_PORT = None
EMAIL_USER = None
EMAIL_PASS = None

def init_data():
    global SMTP_SERVER
    global SMTP_PORT
    global EMAIL_USER
    global EMAIL_PASS
    username = session.get("username", None)

    with sqlite3.connect("/tmp/database.db") as conn:
            user = conn.execute("""
                SELECT email, email_password, imap_server, smtp_server, imap_port, smtp_port
                FROM users WHERE username=?
            """, (username,)).fetchone()

    SMTP_SERVER = user[3]
    SMTP_PORT = user[5]
    EMAIL_USER = user[0]
    EMAIL_PASS = user[1]




@function_tool
def write_email(to: str, subject: str, body: str) -> None:
    init_data()
    print("Email wird geschrieben")
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))
    except Exception as e:
        print(e)

    # Verbindung aufbauen und senden
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to, msg.as_string())
            print(to)
            print("E-Mail erfolgreich gesendet")
            return "E-Mail erfolgreich gesendet"
    except Exception as e:
        print(f"Fehler beim Senden der E-Mail: {e}")
        return f"Fehler beim Senden der E-Mail{e}"


"""@function_tool
async def answer_email(
        empfaenger: str, betreff: str, inhalt: str, id: str) -> None:
    print("Antwort auf Email mit ID: " + id)
    success = nylasClient.send_email(
                to_address=empfaenger,
                subject=betreff,
                body=inhalt,
                reply_to=f"<{id}>")
    if success:
        print("email gesendet")
        return "erfolgreich gesendet"
    else:
        return "Fehler beim senden der email"""
