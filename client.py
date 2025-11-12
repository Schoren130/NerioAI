import webview
import requests
import subprocess
import threading
import time
import tkinter as tk
from tkinter import messagebox
import sys
import atexit

SERVER_URL = "http://172.18.5.122:5000" # Experimenta Laptop
#SERVER_URL = "http://10.28.5.51:5000" # Laptop Frank
#SERVER_URL =  "http://172.18.5.122:5000" # Experimenta Laptop 2
#SERVER_URL = "http://192.168.88.166:5000" # PC Nero
USERNAME = None
powershell = None
output_buffer = []

class API:
    def set_username(self, name):
        global USERNAME
        USERNAME = name
        print("Benutzername gesetzt:", USERNAME)

import os

WHITELIST = [
    "ls",           # Inhalt anzeigen
    "dir",          # Alternativ zu ls
    "cd",           # Verzeichnis wechseln
    "pwd",
    "mkdir"        # aktuelles Verzeichnis anzeigen
]

def start_powershell():
    global powershell
    home_dir = os.path.expanduser("~")  # ermittelt z.B. C:\Users\DeinName
    powershell = subprocess.Popen(
        ["powershell.exe", "-NoLogo", "-NoExit", "-Command", f"cd '{home_dir}'"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",      # ✅ UTF-8 erzwingen
        errors="replace",      # ✅ ungültige Zeichen ersetzen
        bufsize=1
    )
    threading.Thread(target=read_powershell_output, daemon=True).start()
    print(f"✅ PowerShell-Session gestartet (unsichtbar) im Ordner: {home_dir}")

def read_powershell_output():
    global output_buffer
    for line in powershell.stdout:
        line = line.strip()
        if line:
            print(f"[PS] {line}")
            output_buffer.append(line)

def poll_server():
    while True:
        if not USERNAME:
            time.sleep(1)
            continue
        try:
            response = requests.get(f"{SERVER_URL}/get_command/{USERNAME}")
            data = response.json()
            command = data.get("command")
            if command:
                print(f"📩 Befehl erhalten: {command}")

                #if command.strip().lower() == "exit":
                    #print("🚪 Exit-Befehl – beende Client und PowerShell.")
                    #shutdown()

                    #break

                if command.strip().split()[0].lower() in WHITELIST or ask_user_confirmation(command):
                    result = run_persistent_powershell(command)
                else:
                    result = {"stdout": "", "stderr": "Vom Benutzer abgebrochen", "returncode": -1}

                requests.post(f"{SERVER_URL}/send_result/{USERNAME}", json=result)
        except Exception as e:
            print("Fehler:", e)
        time.sleep(5)

def ask_user_confirmation(command):
    root = tk.Tk()
    root.withdraw()
    return messagebox.askokcancel(
        "PowerShell-Befehl ausführen?",
        f"Soll dieser Befehl ausgeführt werden?\n\n{command}"
    )

def run_persistent_powershell(command):
    global output_buffer
    try:
        output_buffer.clear()
        powershell.stdin.write(command + "\n")
        powershell.stdin.flush()
        time.sleep(3)  # kurze Wartezeit für Ausgabe
        return {
            "stdout": "\n".join(output_buffer),
            "stderr": "",
            "returncode": 0
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -2}

def shutdown():
    global powershell
    try:
        if powershell and powershell.poll() is None:
            powershell.stdin.write("exit\n")
            powershell.stdin.flush()
            powershell.terminate()
            print("🛑 PowerShell beendet.")
    except Exception as e:
        print("Fehler beim Beenden:", e)
    sys.exit(0)

# Sicherstellen, dass beim Beenden aufgeräumt wird
atexit.register(shutdown)

if __name__ == "__main__":
    api = API()
    start_powershell()
    threading.Thread(target=poll_server, daemon=True).start()

    # Webview starten – wenn Fenster geschlossen wird, shutdown()
    webview.create_window("Nerio", f"{SERVER_URL}/chat", width=1000, height=700, js_api=api, on_top=False)
    try:
        webview.start(func=None)
    finally:
        shutdown()
