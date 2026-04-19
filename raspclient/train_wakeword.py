import os
import glob
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models

# =====================================================================
# KONFIGURATION
# =====================================================================
DATASET_PATH = "dataset"
EPOCHS = 30
BATCH_SIZE = 16
SAMPLE_RATE = 16000
# Wir nehmen an, dass alle Aufnahmen ca. 1 Sekunde lang sind (aus record_dataset.py)
# =====================================================================

def get_spectrogram(audio):
    """Konvertiert das rohe Audio-Signal in ein mel-ähnliches Spektrogramm."""
    # Padding, um sicherzustellen, dass die Länge gleich ist
    zero_padding = tf.zeros([SAMPLE_RATE] - tf.shape(audio), dtype=tf.float32)
    audio = tf.concat([audio, zero_padding], 0)
    audio.set_shape([SAMPLE_RATE])

    # Kurzzeit-Fourier-Transformation (STFT) anwenden
    spectrogram = tf.signal.stft(audio, frame_length=255, frame_step=128)
    # Nutze absolute Werte (Magnitude)
    spectrogram = tf.abs(spectrogram)
    # WICHTIG: Logarithmus anwenden. Das komprimiert die Skala und hilft 
    # massiv, Stille und Rauschen voneinander zu unterscheiden!
    spectrogram = tf.math.log(spectrogram + 1e-6)
    
    # Füge eine Channel-Dimension hinzu (für Conv2D nötig -> wie ein 1-Kanal-Bild)
    spectrogram = tf.expand_dims(spectrogram, -1)
    return spectrogram

def load_data(data_dir):
    """Sucht nach Ordnern im Verzeichnis, extrahiert Labels und lädt .wav-Dateien."""
    labels = []
    filepaths = []
    
    # Ordner im Datensatz analysieren (Jeder Ordner-Name = 1 Label)
    for folder_name in os.listdir(data_dir):
        folder_path = os.path.join(data_dir, folder_name)
        if os.path.isdir(folder_path):
            wav_files = glob.glob(os.path.join(folder_path, "*.wav"))
            for wav_file in wav_files:
                filepaths.append(wav_file)
                labels.append(folder_name)
                
    if not filepaths:
        return None, None, []
        
    unique_labels = sorted(list(set(labels)))
    print(f"Gefundene Klassen: {unique_labels}")
    
    # Versuche eine Klasse für Hintergrund/Stille zu identifizieren
    background_class = None
    for l in unique_labels:
        if any(term in l.lower() for term in ["hintergrund", "background", "noise", "stille", "ruhe"]):
            background_class = l
            break
            
    if background_class is None:
        background_class = "_background_"
        unique_labels.append(background_class)
        print(f"Hinweis: Keine Hintergrund-Klasse gefunden. Erstelle synthetische Klasse '{background_class}'.")
    
    # Text-Labels in Integer konvertieren
    label_to_id = {label: i for i, label in enumerate(unique_labels)}
    y = [label_to_id[label] for label in labels]
    
    print("Verarbeite Audiodaten zu Spektrogrammen (das kann kurz dauern)...")
    X = []
    for fp in filepaths:
        # Lade WAV-Datei via TensorFlow
        audio_binary = tf.io.read_file(fp)
        audio, _ = tf.audio.decode_wav(audio_binary, desired_channels=1)
        audio = tf.squeeze(audio, axis=-1)
        
        # Konvertiere in Spektrogramm
        spec = get_spectrogram(audio)
        X.append(spec)
        
    print(f"Generiere erweiterte Stille & Umgebungsgeräusche (Klasse: {background_class})...")
    # Generiere 100 synthetische Negativ-Beispiele mit physikalisch korrekten Ambient-Geräuschen
    # Das ersetzt den Download von riesigen (2GB+) Noise-Bibliotheken!
    for i in range(100):
        if i < 20:
            # 1. Reine Stille (verhindert False Positives wenn absolut nichts gesagt wird)
            audio = np.zeros(SAMPLE_RATE, dtype=np.float32)
        elif i < 40:
            # 2. Weißes Rauschen (Zischen, z.B. Heizung / Radio)
            audio = np.random.normal(0.0, np.random.uniform(0.001, 0.02), SAMPLE_RATE).astype(np.float32)
        elif i < 60:
            # 3. Braunes Rauschen (Tieffrequentes Grollen, klingt absolut wie Wind/Autobahn/Klimaanlage)
            white = np.random.normal(0.0, 0.05, SAMPLE_RATE)
            audio = np.cumsum(white) # Integration von Weiß = Braun
            # Audio normalisieren um Clipping zu vermeiden
            audio = (audio / np.max(np.abs(audio))) * np.random.uniform(0.01, 0.1)
            audio = audio.astype(np.float32)
        elif i < 80:
            # 4. Rosa Rauschen (Mittelfrequentes, sehr natürliches Hintergrundgeräusch)
            # Einfache Approximation mittels Array-Dämpfung
            white = np.fft.rfft(np.random.normal(0.0, 1.0, SAMPLE_RATE))
            keys = np.arange(1, len(white)+1)
            pink = white / np.sqrt(keys) # 1/f Spektrum
            audio = np.fft.irfft(pink)
            audio = (audio / np.max(np.abs(audio))) * np.random.uniform(0.01, 0.1)
            audio = audio.astype(np.float32)
        else:
            # 5. Elektrisches Summen (Typisch für Geräte/Computer/Lüfter, 50Hz / 60Hz + Obertöne)
            t = np.linspace(0, 1.0, SAMPLE_RATE, endpoint=False)
            freq = np.random.choice([50.0, 60.0]) # Europäisches vs US Stromnetz-Brummen
            audio = 0.05 * np.sin(2 * np.pi * freq * t)
            audio += 0.02 * np.sin(2 * np.pi * freq*2 * t) # Oberton
            audio += 0.01 * np.sin(2 * np.pi * freq*3 * t) # Oberton
            # Mische minimales Rauschen drüber
            audio += np.random.normal(0, 0.005, SAMPLE_RATE)
            audio = audio.astype(np.float32)

        X.append(get_spectrogram(tf.convert_to_tensor(audio, dtype=tf.float32)))
        y.append(label_to_id[background_class])
        
    print("\nLade zusätzliche Trainingsdaten (andere Wörter) aus dem Internet um menschliche Sprache herauszufiltern...")
    try:
        mini_speech_zip = tf.keras.utils.get_file(
            'mini_speech_commands.zip',
            origin="http://storage.googleapis.com/download.tensorflow.org/data/mini_speech_commands.zip",
            extract=True,
            cache_dir='.',
            cache_subdir='internet_data'
        )
        base_dir = os.path.join(os.path.dirname(mini_speech_zip), 'mini_speech_commands')
        
        internet_files = []
        # Wir nehmen jeweils 25 Samples von diesen Wörtern, damit das Modell lernt
        # dass normale Wörter NICHT das Wake Word sind.
        for word in ['down', 'go', 'left', 'no', 'right', 'stop', 'up', 'yes']:
            word_dir = os.path.join(base_dir, word)
            if os.path.exists(word_dir):
                internet_files.extend(glob.glob(os.path.join(word_dir, "*.wav"))[:25])
                
        print(f"-> {len(internet_files)} Samples anderer Sprachbefehle heruntergeladen und als Ablenkung eingefügt.")
        for fp in internet_files:
            audio_binary = tf.io.read_file(fp)
            audio, _ = tf.audio.decode_wav(audio_binary, desired_channels=1)
            audio = tf.squeeze(audio, axis=-1)
            spec = get_spectrogram(audio)
            X.append(spec)
            y.append(label_to_id[background_class])
            
    except Exception as e:
        print(f"Fehler beim Download der Internetdaten (wird übersprungen): {e}")

    X = np.array(X)
    y = np.array(y)
    return X, y, unique_labels

def build_model(input_shape, num_classes, norm_layer):
    """Erstellt ein kleines CNN (Convolutional Neural Network) für Audio."""
    model = models.Sequential([
        layers.Input(shape=input_shape),
        # Normalisierung hilft gegen laute/leise Lautstärken
        layers.Resizing(32, 32), 
        norm_layer,
        layers.Conv2D(32, 3, activation='relu'),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, activation='relu'),
        layers.MaxPooling2D(),
        layers.Dropout(0.25),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation='softmax')
    ])

    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    return model

def main():
    print("====================================")
    print(" TensorFlow Wakeword Trainer        ")
    print("====================================")
    
    if not os.path.exists(DATASET_PATH):
        print(f"Fehler: Ordner '{DATASET_PATH}' existiert nicht.")
        print("Bitte erstelle erst mit 'record_dataset.py' ein paar Aufnahmen.")
        return
        
    X, y, class_names = load_data(DATASET_PATH)
    
    if X is None or len(X) == 0:
        print("Fehler: Keine .wav Dateien gefunden im Ordner 'dataset/'!")
        return
        
    print(f"Erfolgreich geladen: {len(y)} Audioschnipsel.")
    print(f"Form eines Spektrogramms: {X.shape[1:]}")
    
    # Normalisierungsschicht speziell auf die lokalen Audiodaten anpassen
    print("Passe Normalisierungsschicht auf Audio-Statistiken an (extrem wichtig für Stille-Erkennung)...")
    norm_layer = layers.Normalization()
    norm_layer.adapt(X)
    
    # Zufällig durchmischen
    indices = np.arange(len(y))
    np.random.shuffle(indices)
    X = X[indices]
    y = y[indices]
    
    # 80% Training, 20% Validierung
    split = int(0.8 * len(y))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    
    print("\nInitialisiere Neuronales Netzwerk...")
    input_shape = X.shape[1:]
    num_classes = len(class_names)
    
    model = build_model(input_shape, num_classes, norm_layer)
    model.summary()
    
    print("\n🔥 Starte Training...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE
    )
    
    # Speichern des Modells
    model_export_path = "wakeword_model.keras"
    model.save(model_export_path)
    print(f"\n✅ Training abgeschlossen! Modell gespeichert als '{model_export_path}'")
    
    # Speichern der Labels als Textdatei (wichtig für die spätere Nutzung)
    with open("wakeword_labels.txt", "w") as f:
        f.write("\n".join(class_names))
    print(f"Klassen-Referenz gespeichert in 'wakeword_labels.txt'")

if __name__ == "__main__":
    main()
