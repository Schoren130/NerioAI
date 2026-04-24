import os
import time
import wave
import threading
import contextlib
import requests
import pyaudio
import numpy as np
import tensorflow as tf

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

# TensorFlow Warnings ignorieren
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# =====================================================================
# KONFIGURATION
# =====================================================================

# Server-URL (IP oder Hostname deines Rechners, auf dem app.py läuft)
SERVER_URL = "http://localhost:5000"  # HIER ANPASSEN!

# Login-Daten für deinen Server
USERNAME = "Nero"           # HIER ANPASSEN!
PASSWORD = "nero"               # HIER ANPASSEN!

# Audio-Aufnahmeeinstellungen
CHUNK = 2000              # Schiebefenster für Wakeword
FORMAT = pyaudio.paInt16
CHANNELS = 1              # Mikrofonkanäle (Raspberry Pi meist 1)
RATE = 16000              # Abtastrate (muss 16000 sein für Modell und Server)
TEMP_RECORD_WAV = "temp_record.wav"
TEMP_PLAY_WAV = "temp_play.wav"

# Wakeword Einstellungen
MODEL_PATH = "wakeword_model.keras"
LABELS_PATH = "wakeword_labels.txt"
WAKEWORD_THRESHOLD = 0.90
COMMAND_RECORD_SECONDS = 5.0 # Wie viele Sekunden NACH Erkennung aufgenommen wird

# =====================================================================

session = requests.Session()

def get_pi_token():
    """Holt den PI_TOKEN vom Server basierend auf den Anmeldedaten."""
    print(f"Hole Token vom Server {SERVER_URL} für '{USERNAME}'...")
    try:
        response = session.post(
            f"{SERVER_URL}/api/get_pi_token",
            json={"username": USERNAME, "password": PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            token = response.json().get("pi_token")
            print("Token erfolgreich geladen!")
            return token
        else:
            print("Token-Abruf fehlgeschlagen. Bitte Benutzernamen und Passwort prüfen.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Fehler bei der Verbindung zum Server: {e}")
        return None

INPUT_DEVICE_INDEX = None

def get_input_device(p):
    """Sucht das erste verfügbare Mikrofon, falls keins explizit gesetzt ist."""
    if INPUT_DEVICE_INDEX is not None:
        return INPUT_DEVICE_INDEX
        
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:
            print(f"Verwende Mikrofon: {dev_info.get('name')} (ID: {i})")
            return i
            
    print("Warnung: Kein Mikrofon gefunden!")
    return None

def get_spectrogram(audio):
    """Feature-Extraktion für das TensorFlow Wakeword Modell (MUSS exakt dem Training entsprechen)."""
    zero_padding = tf.zeros([RATE] - tf.shape(audio), dtype=tf.float32)
    audio = tf.concat([audio, zero_padding], 0)
    audio.set_shape([RATE])
    spectrogram = tf.signal.stft(audio, frame_length=255, frame_step=128)
    spectrogram = tf.abs(spectrogram)
    spectrogram = tf.math.log(spectrogram + 1e-6)
    spectrogram = tf.expand_dims(spectrogram, -1)
    return spectrogram

def wait_for_wakeword(model, wakeword_idx, class_names, stream):
    """Lauscht kontinuierlich auf das Wake Word im Hintergrund."""
    print(f"\n🎧 Warte auf Wake Word '{class_names[wakeword_idx]}'...")
    buffer = np.zeros(int(RATE * 1.0), dtype=np.float32)
    
    # Alte Daten verwerfen
    try:
        while stream.get_read_available() > 0:
            stream.read(stream.get_read_available(), exception_on_overflow=False)
    except:
        pass
        
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        new_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        
        buffer = np.roll(buffer, -CHUNK)
        buffer[-CHUNK:] = new_data
        
        audio_tensor = tf.convert_to_tensor(buffer, dtype=tf.float32)
        spec = get_spectrogram(audio_tensor)
        
        prediction = model.predict(tf.expand_dims(spec, 0), verbose=0)[0]
        score = prediction[wakeword_idx]
        
        if score >= WAKEWORD_THRESHOLD:
            print(f"\n🟢 >>> WAKE WORD '{class_names[wakeword_idx]}' ERKANNT! ({score*100:.1f}%) <<<")
            return

def record_command(p, stream):
    """Nimmt den Befehl für eine festgelegte Zeit auf."""
    print(f"🎙️ Aufnahme läuft für {COMMAND_RECORD_SECONDS} Sekunden... Bitte sprich jetzt!")
    frames = []
    
    num_chunks = int((RATE / CHUNK) * COMMAND_RECORD_SECONDS)
    for _ in range(num_chunks):
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        except Exception as e:
            print(f"Fehler beim Lesen des Audio-Streams: {e}")
            break
            
    print("🛑 Aufnahme beendet. Verbuche und sende an Server...")
    
    with wave.open(TEMP_RECORD_WAV, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        
    return TEMP_RECORD_WAV

def transcribe_audio(filename):
    """Sendet die aufgenommene Datei an den /stt Endpunkt des Servers."""
    print("Sende Audiodatei zur Transkription (/stt)...")
    url = f"{SERVER_URL}/stt"
    try:
        with open(filename, "rb") as f:
            files = {"file": f}
            response = session.post(url, files=files, timeout=30)
            if response.status_code == 200:
                data = response.json()
                transcript = data.get("transcript", "")
                print(f"Transkript: '{transcript}'")
                return transcript
            else:
                print(f"Fehler bei STT (Status {response.status_code}): {response.text}")
                return None
    except Exception as e:
        print(f"Fehler beim Senden der Datei: {e}")
        return None

def ask_nerio(transcript):
    """Sendet das Transkript an /nerio_chat und fordert eine Audioantwort an."""
    if not transcript: return None
    print("Frage Nerio (/nerio_chat)...")
    url = f"{SERVER_URL}/nerio_chat"
    try:
        payload = {"message": transcript, "switch": True}
        response = session.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Fehler bei Nerio Chat (Status {response.status_code})")
            return None
    except Exception as e:
        print(f"Fehler beim Senden der Nachricht an Nerio: {e}")
        return None

def play_audio(audio_urls):
    """Lädt die Server-Audio-Dateien herunter und spielt sie ab."""
    if not audio_urls:
         print("Keine Audioantworten von Nerio erhalten.")
         return

    pygame.mixer.init()
    for audio_path in audio_urls:
        if audio_path == 0 or not audio_path: continue
        print(f"Lade Audio von Nerio herunter: {audio_path}")
        
        # WICHTIG: Windows-Server geben Pfade oft mit Backslash '\' zurück.
        # URLs dürfen aber nur Forward-Slashes '/' enthalten!
        clean_audio_path = audio_path.replace("\\", "/")
        download_url = f"{SERVER_URL}/{clean_audio_path}"
        
        try:
            response = session.get(download_url, timeout=15)
            if response.status_code == 200:
                with open(TEMP_PLAY_WAV, "wb") as f:
                    f.write(response.content)
                print("🔊 Spiele Antwort...")
                pygame.mixer.music.load(TEMP_PLAY_WAV)
                pygame.mixer.music.play()
                
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                pygame.mixer.music.unload()
            else:
                print(f"Fehler beim Herunterladen der Audiodatei {audio_path}")
        except Exception as e:
            print(f"Fehler beim Abspielen: {e}")

def load_wakeword_model():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
        print("Kritischer Fehler: Wake Word Modell oder Labels fehlen! Führe train_wakeword.py aus.")
        return None, None, None
        
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        class_names = [line.strip() for line in f.readlines() if line.strip()]
        
    wakeword_idx = -1
    for i, c in enumerate(class_names):
        if any(w in c.lower() for w in ["nerio", "wake", "aufmerksam"]):
            wakeword_idx = i; break
    if wakeword_idx == -1: wakeword_idx = 0
    
    print("Lade Neuronales Netz für Wake Word...")
    model = tf.keras.models.load_model(MODEL_PATH)
    return model, class_names, wakeword_idx

def main():
    print("====================================")
    print(" Nerio Raspberry Pi Client gestartet ")
    print("====================================")
    
    # 1. Token vom Server beziehen
    pi_token = get_pi_token()
    if not pi_token:
        print("Programm wird beendet, da kein Token generiert werden konnte.")
        return
        
    session.headers.update({"Authorization": f"Bearer {pi_token}"})

    # 2. Modell laden
    model, class_names, wakeword_idx = load_wakeword_model()
    if not model: return

    # 3. Audio Stream initialisieren (bleibt dauerhaft offen, viel performanter)
    p = pyaudio.PyAudio()
    device_index = get_input_device(p)
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, 
                        input_device_index=device_index, frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Fehler: Mikrofon konnte nicht geöffnet werden: {e}")
        p.terminate()
        return

    # Hauptschleife
    try:
        while True:
            print("\n" + "="*40)
            
            # 1. Endlosschleife: Auf Wakeword warten
            wait_for_wakeword(model, wakeword_idx, class_names, stream)
            
            # 2. Kommando für z.B. 5 Sekunden aufzeichnen
            if not os.path.exists(TEMP_RECORD_WAV): open(TEMP_RECORD_WAV, 'w').close()
            record_command(p, stream)
            
            # 3. Transkribieren und API Calls
            transcript = transcribe_audio(TEMP_RECORD_WAV)
            if transcript:
                nerio_response = ask_nerio(transcript)
                if nerio_response:
                    text_responses = nerio_response.get("responses", [])
                    audio_urls = nerio_response.get("audio", [])
                    for txt in text_responses:
                        print(f"Nerio sagt: {txt}")
                    play_audio(audio_urls)
                    
            # Nach Ausführung Buffer etc. leeren (Cooldown)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nBeenden des Clients...")
    except Exception as e:
        print(f"Unerwarteter Fehler in der Hauptschleife: {e}")
    finally:
        # Sauber Beenden
        if 'stream' in locals():
            stream.stop_stream()
            stream.close()
        if 'p' in locals():
            p.terminate()

if __name__ == "__main__":
    main()
