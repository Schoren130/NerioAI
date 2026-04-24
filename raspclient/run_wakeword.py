import os
import time
import pyaudio
import numpy as np
import tensorflow as tf

# =====================================================================
# KONFIGURATION
# =====================================================================
MODEL_PATH = "wakeword_model.keras"
LABELS_PATH = "wakeword_labels.txt"
SAMPLE_RATE = 16000
CHUNK = 2000  # Für schnelles Auswerten ein kleinerer Chunk der geschoben wird (ca. 8x pro Sekunde)
RECORD_SECONDS = 1.0 
THRESHOLD = 0.90

# PyAudio Config
FORMAT = pyaudio.paInt16
CHANNELS = 1

def get_spectrogram(audio):
    """Muss EXAKT der Feature-Extraktion aus train_wakeword.py entsprechen!"""
    zero_padding = tf.zeros([SAMPLE_RATE] - tf.shape(audio), dtype=tf.float32)
    audio = tf.concat([audio, zero_padding], 0)
    audio.set_shape([SAMPLE_RATE])

    spectrogram = tf.signal.stft(audio, frame_length=255, frame_step=128)
    spectrogram = tf.abs(spectrogram)
    # WICHTIG: Die log-Skalierung muss auch hier rein, da sie jetzt Bestandteil 
    # des verbesserten Trainings ist!
    spectrogram = tf.math.log(spectrogram + 1e-6)
    spectrogram = tf.expand_dims(spectrogram, -1)
    return spectrogram

def main():
    print("====================================")
    print(" 🎙️ TensorFlow Wakeword Echtzeit-Test")
    print("====================================")

    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
        print("Fehler: Modell oder Label-Datei nicht gefunden.")
        print("Bitte führe zuerst 'train_wakeword.py' aus, um das Modell zu generieren!")
        return

    # Lade Labels aus Textdatei
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        class_names = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"Geladene Klassen: {class_names}")
    
    # Finde die Wakeword Klasse (suche nach nerio, wakeword, wake, aufmerksam)
    wakeword_idx = -1
    for i, c in enumerate(class_names):
        if any(w in c.lower() for w in ["nerio", "wake", "aufmerksam"]):
            wakeword_idx = i
            break
            
    if wakeword_idx == -1:
        print(f"Konnte Wake-Word Klasse nicht automatisch bestimmen. Verwende Index 0 ({class_names[0]}).")
        wakeword_idx = 0
        
    print(f"Ziel-Label für Erkennung: '{class_names[wakeword_idx]}'")

    # Lade Modell
    print("Lade Neuronales Netz (das kann kurz dauern)...")
    # Silence Warnungen
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    model = tf.keras.models.load_model(MODEL_PATH)

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK)

    print("\n🎧 Höre zu... (Drücke Strg+C zum Beenden)")
    
    # Ringbuffer für Audio füllt sich kontinuierlich auf 16000 (1 Sekunde)
    buffer = np.zeros(int(SAMPLE_RATE * RECORD_SECONDS), dtype=np.float32)
    
    try:
        while True:
            # Lade Audio Chunk (rohe Bytes)
            data = stream.read(CHUNK, exception_on_overflow=False)
            
            # WICHTIG: tf.audio.decode_wav gibt Floats zwischen -1.0 und 1.0 aus.
            # PyAudio liefert hier Int16. Wir müssen also manuell auf den Bereich -1 bis 1 normalisieren!
            # Ohne diese Teilung durch 32768.0 geht die Echtzeitanalyse IMMER schief.
            new_data = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Verschiebe Buffer (Schiebefenster)
            buffer = np.roll(buffer, -CHUNK)
            buffer[-CHUNK:] = new_data
            
            # Erstelle Tensor
            audio_tensor = tf.convert_to_tensor(buffer, dtype=tf.float32)
            
            # Spektrogramm wie im Training erstellen
            spec = get_spectrogram(audio_tensor)
            
            # Vorhersage (Wir erzeugen einen Batch der Größe 1)
            prediction = model.predict(tf.expand_dims(spec, 0), verbose=0)[0]
            
            score = prediction[wakeword_idx]
            
            if score >= THRESHOLD:
                print(f"\n🟢 >>> WAKE WORD ERKANNT! '{class_names[wakeword_idx]}' ({score*100:.1f}%) <<<")
                
                # Buffer leeren um Doppel-Erkennungen des gleichen Worts direkt nacheinander zu vermeiden
                buffer = np.zeros(int(SAMPLE_RATE * RECORD_SECONDS), dtype=np.float32)
                time.sleep(1.5) # Kurze Cooldown-Sperre
                print("Höre zu...")
                
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    main()
