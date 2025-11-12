# app.py
from flask import Flask, render_template, request, redirect, session
import sqlite3
from flask import jsonify, request
import asyncio
from Agents.orchestrator_agent import orchestrator_agent
from openai.types.responses import ResponseTextDeltaEvent
from agents import Runner
from globals import pending_commands , command_results
import bcrypt
from tts import text_to_speech
#import nltk

app = Flask(__name__)
app.secret_key = "supersecretkey"

audio_ausgabe=False

history = {}

#nltk.download("punkt")

REGISTRATION_CODES = ["REGISTRATION", ""]

# Datenbank-Initialisierung
def init_db():
    with sqlite3.connect("database.db") as conn:
        print("test")
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            email_password TEXT,
            imap_server TEXT,
            smtp_server TEXT,
            imap_port INTEGER,
            smtp_port INTEGER
        )""")

init_db()

def is_mobile():
    ua = request.user_agent.string.lower()
    return "mobile" in ua or "iphone" in ua or "android" in ua

# Startseite/Login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        with sqlite3.connect("database.db") as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and bcrypt.checkpw(password.encode("utf-8"), user[2]):
            session["username"] = username
            history[username]=[{"role": "system", "content": "Du bist nerio ein hilfreicher Assistent. Die uhrzeit die du bekommst ist immer richtig!!!!"}]
            return redirect("/chat")
        else:
            return "Login fehlgeschlagen"
    if is_mobile():
        return render_template("login_mobile.html")
    return render_template("login.html")

@app.route("/logout")
def logout():
    history[session["username"]]=None
    session.clear()  # löscht alle Sitzungsdaten (z. B. username)
    return redirect("/")  # leitet zur Login-Seite weiter

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        code = request.form["code"]

        if code not in REGISTRATION_CODES:
            return "Ungültiger Registrierungscode"

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        # Temporär speichern bis E-Mail-Daten eingegeben sind
        session["temp_user"] = {
            "username": username,
            "password": hashed_password
        }

        return redirect("/register_email")

    if is_mobile():
        return render_template("register_mobile.html")
    return render_template("register.html")


@app.route("/register_email", methods=["GET", "POST"])
def register_email():
    if "temp_user" not in session:
        return redirect("/register")

    if request.method == "POST":
        email = request.form["email"]
        email_password = request.form["email_password"]
        imap_server = request.form["imap_server"]
        smtp_server = request.form["smtp_server"]
        imap_port = request.form["imap_port"]
        smtp_port = request.form["smtp_port"]

        temp_user = session.pop("temp_user")
        username = temp_user["username"]
        hashed_password = temp_user["password"]

        try:
            with sqlite3.connect("database.db") as conn:
                conn.execute("""
                    INSERT INTO users (username, password, email, email_password,
                                       imap_server, smtp_server, imap_port, smtp_port)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (username, hashed_password, email, email_password,
                      imap_server, smtp_server, imap_port, smtp_port))
            return redirect("/")
        except Exception as e:
            print(e)
            return "Fehler beim Speichern oder Benutzername existiert bereits."

    return render_template("register_email.html")


# Chat-Seite
@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect("/")
    if is_mobile():
        return render_template("chat_mobile.html", username=session["username"])
    return render_template("chat.html", username=session["username"])

@app.route("/get_username")
def get_username():
    username = session.get("username", None)
    return jsonify({"username": username})
    

@app.route("/nerio_chat", methods=["POST"])
def nerio_chat():
    global history
    message = request.json["message"]
    history[session["username"]].append(
        {"role": "user", "content": message})
    output = asyncio.run(run_nerio())

    sentences = output.split('. ')
    sentences = [sentence.strip('.') for sentence in sentences]

    audio_files = []

    for sentence in sentences:
        if audio_ausgabe:
            audio_file_path = text_to_speech(sentence)  # Generiere die Audiodatei für jeden Satz
            audio_files.append(audio_file_path)
        history[session["username"]].append({"role": "assistant", "content": sentence})

    return jsonify({"responses": sentences, "audio": audio_files})  # Gebe Sätze und Audio zurück


async def run_nerio():
    global history
    result = Runner.run_streamed(orchestrator_agent, input=history[session['username']])
    print(history)
    output = ""
    async for event in result.stream_events():
        if event.type == "raw_response_event" and \
                isinstance(event.data, ResponseTextDeltaEvent):
            delta = event.data.delta
            output += delta

    if output.strip():
        history[session["username"]].append({"role": "assistant", "content": output})
    return output

@app.route("/get_command/<username>", methods=["GET"])
def get_command(username):
    command = pending_commands.pop(username, None)
    return jsonify({"command": command})

@app.route("/send_result/<username>", methods=["POST"])
def receive_result(username):
    result = request.get_json()
    command_results[username] = result
    return jsonify({"status": "Ergebnis gespeichert"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
