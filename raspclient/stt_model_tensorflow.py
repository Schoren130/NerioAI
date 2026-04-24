import os
import pyaudio
import numpy as np
import tensorflow as tf
from scipy.signal import spectrogram
import time

# Konfiguration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 1.5 # Länge des Wake-Words

def get_spectrogram(audio):
    # Erstellt ein Spektrogramm aus den Rohdaten
    f, t, Sxx = spectrogram(audio, fs=RATE)
    # Logarithmus anwenden für bessere Dynamik
    log_spec = np.log(Sxx + 1e-10)
    # Normierung (Z-Score Standardisierung) - Hilft extrem gegen Stille-Erkennung
    mean = np.mean(log_spec)
    std = np.std(log_spec) + 1e-10
    return (log_spec - mean) / std

def create_model(input_shape):
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=input_shape),
        tf.keras.layers.Reshape((input_shape[0], input_shape[1], 1)),
        tf.keras.layers.Conv2D(32, 3, activation='relu'),
        tf.keras.layers.MaxPooling2D(),
        tf.keras.layers.Dropout(0.25),
        tf.keras.layers.Conv2D(64, 3, activation='relu'),
        tf.keras.layers.MaxPooling2D(),
        tf.keras.layers.Dropout(0.25),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

# --- 1. AUFNAHME VON TRAININGSDATEN ---
def record_samples(label_name, num_samples=10):
    p = pyaudio.PyAudio()
    samples = []
    print(f"\nStarte Aufnahme für: {label_name}. Bereit machen...")
    time.sleep(2)
    
    for i in range(num_samples):
        print(f"Aufnahme {i+1}/{num_samples} (Sprich jetzt!)...")
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(np.frombuffer(data, dtype=np.int16))
        
        audio_data = np.concatenate(frames).astype(np.float32)
        samples.append(get_spectrogram(audio_data))
        stream.stop_stream()
        stream.close()
        time.sleep(1.0) # Kurze Pause zwischen den Aufnahmen
    
    p.terminate()
    return np.array(samples)

def train_model():
    print("--- ROBUSTES WAKE WORD TRAINING ---")
    print("Dieses Training generiert automatisch negative Beispiele (Stille & Rauschen).")
    num_samples = int(input("Wie viele Samples pro Klasse aufnehmen? (Empfehlung: 20): ") or 20)
    
    print("\n[PHASE 1] Wake Word aufnehmen")
    wake_samples = record_samples("WAKE WORD", num_samples)
    
    print("\n[PHASE 2] Hintergrundgeräusche aufnehmen")
    noise_samples = record_samples("HINTERGRUND (bitte still sein oder normal reden, KEIN Wake Word)", num_samples)
    
    print("\n[PHASE 3] Generiere synthetische negative Daten (Stille, Rauschen)")
    # Synthetische Daten hinzufügen für Robustheit gegen Stille und Rauschen
    synth_samples = []
    length = int(RATE * RECORD_SECONDS)
    for _ in range(num_samples):
        # 1. Reine Stille
        silence = np.zeros(length, dtype=np.float32)
        synth_samples.append(get_spectrogram(silence))
        
        # 2. Weißes Rauschen
        noise = np.random.normal(0, np.random.uniform(500, 3000), length).astype(np.float32)
        synth_samples.append(get_spectrogram(noise))
    synth_samples = np.array(synth_samples)
    
    # Kombinieren
    X = np.concatenate([wake_samples, noise_samples, synth_samples])
    
    # Labels: 1 für Wake Word, 0 für Noise & Synthetisch
    y = np.concatenate([
        np.ones(len(wake_samples)), 
        np.zeros(len(noise_samples)), 
        np.zeros(len(synth_samples))
    ])
    
    # Mischen
    indices = np.arange(len(X))
    np.random.shuffle(indices)
    X = X[indices]
    y = y[indices]
    
    model = create_model(X[0].shape)
    
    print("\nStarte Training...")
    early_stopping = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=4, restore_best_weights=True)
    model.fit(X, y, epochs=30, batch_size=8, callbacks=[early_stopping])
    
    model.save("wakeword_model.keras")
    print("\nModell erfolgreich trainiert und unter 'wakeword_model.keras' gespeichert!")
    return model

# --- 2. ECHTZEIT ERKENNUNG ---
def start_detection(model):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    print("\nHöre zu... (Strg+C zum Beenden)")
    buffer = np.zeros(int(RATE * RECORD_SECONDS))
    
    try:
        while True:
            data = stream.read(CHUNK)
            new_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            buffer = np.roll(buffer, -CHUNK)
            buffer[-CHUNK:] = new_data
            
            spec = get_spectrogram(buffer)
            prediction = model.predict(spec[np.newaxis, ...], verbose=0)
            
            if prediction[0][0] > 0.95:
                print(">>> WAKE WORD ERKANNT! <<<")
                # Buffer leeren, um mehrfache Erkennungen des gleichen Worts zu vermeiden
                buffer = np.zeros(int(RATE * RECORD_SECONDS))
                time.sleep(1) # Kurze Pause nach Erkennung
                
    except KeyboardInterrupt:
        print("\nBeendet.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    if not os.path.exists("wakeword_model.keras"):
        print("Kein trainiertes Modell gefunden. Starte Trainingsprozess...")
        model = train_model()
    else:
        auswahl = input("Soll das Modell neu trainiert werden? (j/N): ")
        if auswahl.lower() == 'j':
            model = train_model()
        else:
            model = tf.keras.models.load_model("wakeword_model.keras")
            
    start_detection(model)