# app.py
from flask import Flask, render_template, request, redirect, session
import os
from flask import jsonify, request
import asyncio
import time
import secrets
from Agents.orchestrator_agent import orchestrator_agent
from openai.types.responses import ResponseTextDeltaEvent
from agents import Runner
from waitress import serve
from globals import pending_commands , command_results
import bcrypt
from text_to_speech_google import text_to_speech
#import nltk
from firebase_test import db
from flask_cors import CORS
import openai
from dotenv import load_dotenv



load_dotenv()
openai.api_key = os.environ.get("OPENAI_API_KEY")
app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app)

audio_ausgabe=True

history = {}
last_activity = {}
MAX_HISTORY_MESSAGES = 20

#nltk.download("punkt")

REGISTRATION_CODES = ["NERIO2025", "BETA123"]

# Datenbank-Initialisierung

def is_mobile():
    ua = request.user_agent.string.lower()
    #return "mobile" in ua or "iphone" in ua or "android" in ua
    return False

def identify_user():
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]
        users_stream = db.collection("users").where("pi_token", "==", token).stream()
        u_list = list(users_stream)
        if u_list:
            return u_list[0].id, True
    return session.get("username"), False

# Startseite/Login
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        print("hi")
        user_ref = db.collection("users").document(username)
        print("hiii")
        print(user_ref)
        user_doc = user_ref.get()
        print("hiiiuu")
        if user_doc.exists:
            user = user_doc.to_dict()
            if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
                session["username"] = username
                history[username] = [{"role": "system", "content": "Du bist nerio ein hilfreicher Assistent. Die uhrzeit die du bekommst ist immer richtig!!!!"}]
                return redirect("/chat")
            else:
                return "Login fehlgeschlagen"
        else:
            return "Login fehlgeschlagen"
    if is_mobile():
        return render_template("login_mobile.html")
    return render_template("index.html")

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
    return render_template("index.html")


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
        loxone_ip = request.form["loxone_ip"]
        loxone_user = request.form["loxone_user"]
        loxone_pass = request.form["loxone_pass"]

        temp_user = session.pop("temp_user")
        username = temp_user["username"]
        hashed_password = temp_user["password"]

        try:
            user_ref = db.collection("users").document(username)  # username als Dokument-ID
            if user_ref.get().exists:
                return "Benutzername existiert bereits."
            
            user_ref.set({
                "username": username,
                "password": hashed_password,   # gespeichert als Bytes oder String
                "email": email,
                "email_password": email_password,
                "imap_server": imap_server,
                "smtp_server": smtp_server,
                "imap_port": imap_port,
                "smtp_port": smtp_port,
                "loxone_ip": loxone_ip,
                "loxone_user": loxone_user,
                "loxone_pass": loxone_pass
            })
            return redirect("/")
        except Exception as e:
            print(e)
            return "Fehler beim Speichern oder Benutzername existiert bereits."

    return render_template("index.html")


# Chat-Seite
@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect("/")
    if is_mobile():
        return render_template("chatmobile_new.html", username=session["username"])
    return render_template("index.html", username=session["username"])

@app.route("/get_username")
def get_username():
    username = session.get("username", None)
    if username:
        user_doc = db.collection("users").document(username).get()
        if user_doc.exists:
            language = user_doc.to_dict().get("language", "de")
            return jsonify({"username": username, "language": language})
    return jsonify({"username": username, "language": "de"})

@app.route("/api/save_language", methods=["POST"])
def save_language():
    username = session.get("username")
    if not username:
        return jsonify({"error": "Unauthorized"}), 401
    lang = request.json.get("language")
    if lang:
        db.collection("users").document(username).update({"language": lang})
        return jsonify({"status": "success"})
    return jsonify({"error": "Invalid request"}), 400

@app.route("/api/get_pi_token", methods=["POST"])
def api_get_pi_token():
    try:
        username = request.json.get("username")
        password = request.json.get("password")
        
        if not username or not password:
            return jsonify({"error": "Benutzername und Passwort erforderlich"}), 400
            
        user_ref = db.collection("users").document(username)
        user_doc = user_ref.get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            if bcrypt.checkpw(password.encode("utf-8"), user_data["password"]):
                pi_token = user_data.get("pi_token")
                
                if not pi_token:
                    pi_token = secrets.token_hex(16)
                    user_ref.update({"pi_token": pi_token})
                    
                return jsonify({"pi_token": pi_token})
        return jsonify({"error": "Ungültige Anmeldedaten"}), 401
    except Exception as e:
        print(f"Token Error: {e}")
        return jsonify({"error": "Serverfehler"}), 500

@app.route("/nerio_chat", methods=["POST"])
def nerio_chat():
    print("runned nerio")
    global history, last_activity
    message = request.json["message"]
    try:
        switch_state = request.json["switch"] 
    except Exception:
        switch_state=False
    print(switch_state)
    
    username = None
    
    base_username, is_rasp = identify_user()
    
    if not base_username:
        return jsonify({"error": "Nicht angemeldet oder ungültiger Token"}), 401
        
    username = f"{base_username}raspacc" if is_rasp else base_username

    if username not in history:
        history[username] = [{"role": "system", "content": "Du bist nerio ein hilfreicher Assistent. Die uhrzeit die du bekommst ist immer richtig!"}]

    if is_rasp:
        now = time.time()
        last_time = last_activity.get(username, 0)
        # 600 Sekunden = 10 Minuten Inaktivität
        if (now - last_time) > 600:
            history[username] = [{"role": "system", "content": "Du bist nerio ein hilfreicher Assistent. Die uhrzeit die du bekommst ist immer richtig!"}]
            history[username].append(
                {"role": "system", "content": "Dieser chat ist nicht von der website sondern von dem Sprachassistenten."}
            )
        last_activity[username] = now

    history[username].append(
        {"role": "user", "content": message})
        
    output = asyncio.run(run_nerio(username))

    sentences = output.split('. ')
    sentences = [sentence.strip('.') for sentence in sentences]

    audio_files = []

    for sentence in sentences:
        if switch_state:
            audio_file_path = text_to_speech(sentence)  # Generiere die Audiodatei für jeden Satz
            print(audio_file_path)
            audio_files.append(audio_file_path)
            print(audio_files)
        history[username].append({"role": "assistant", "content": sentence})

    if len(history[username]) > MAX_HISTORY_MESSAGES:
        history[username] = [history[username][0]] + history[username][-(MAX_HISTORY_MESSAGES - 1):]

    return jsonify({"responses": sentences, "audio": audio_files})  # Gebe Sätze und Audio zurück


async def run_nerio(username):
    global history
    result = Runner.run_streamed(orchestrator_agent, input=history[username])
    print(history)
    output = ""
    async for event in result.stream_events():
        if event.type == "raw_response_event" and \
                isinstance(event.data, ResponseTextDeltaEvent):
            delta = event.data.delta
            output += delta

    if output.strip():
        history[username].append({"role": "assistant", "content": output})
    return output

@app.route("/send_command/<username>", methods=["POST"])
def send_command(username):
    data = request.get_json()
    command = data.get("command")
    if not command:
        return jsonify({"error": "Kein Befehl erhalten"}), 400
    pending_commands[username] = command
    return jsonify({"status": f"Befehl an {username} gesendet."})

@app.route("/get_command/<username>", methods=["GET"])
def get_command(username):
    command = pending_commands.pop(username, None)
    return jsonify({"command": command})

@app.route("/send_result/<username>", methods=["POST"])
def receive_result(username):
    result = request.get_json()
    command_results[username] = result
    return jsonify({"status": "Ergebnis gespeichert"})

@app.route('/stt', methods=['POST'])
def stt():
    if 'file' not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen"}), 400

    audio_file = request.files['file']
    
    base_username, _ = identify_user()
    lang = "de"
    if base_username:
        user_doc = db.collection("users").document(base_username).get()
        if user_doc.exists:
            lang = user_doc.to_dict().get("language", "de")

    transcript = openai.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        language=lang,
        file=(audio_file.filename, audio_file.read())
    ).text

    return jsonify({"transcript": transcript})

@app.route('/modi', methods=['POST'])
def modi():
    data = request.get_json()
    mode = data.get("modi")
    print(f"Modus erhalten: {mode}")
    if not mode:
        return jsonify({"error": "Kein Modus erhalten"}), 400
    if mode == "Professional":
        username= session["username"]
        history[username]=[{"role": "system", "content": "Der Modus wurde vom Benutzer auf Professional gesetzt. Antworte jetzt professionell und sachlich."}]
    elif mode == "Friendly":
        username= session["username"]
        history[username]=[{"role": "system", "content": "Der Modus wurde vom Benutzer auf Friendly gesetzt. Antworte jetzt freundlich und locker."}]
    elif mode == "Creative":
        username= session["username"]
        history[username]=[{"role": "system", "content": "Der Modus wurde vom Benutzer auf Creative gesetzt. Antworte sei jetzt besonders kreativ und unkonventionell."}]
    else:        return jsonify({"error": "Ungültiger Modus"}), 400
    return jsonify({"status": f"Modus auf {mode} gesetzt."})

if __name__ == "__main__":
    app.run(debug=True)
    #serve(app,host="172.18.5.122",port=5000)
    print("hi")  # Experimenta Laptop
    #serve(app,host="10.28.5.51",port=5000) # Laptop Frank
    #serve(app,host="172.18.13.78",port=5000) # Laptop Benedikt
    #serve(app,host="192.168.88.166",port=5000) # PC Nero
    #serve(app,host="172.18.5.122",port=5000) # Laptop Experimenta 2

# 1605 Zeilen