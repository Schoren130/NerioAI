import os
import wave
import uuid
import pyaudio

# =====================================================================
# KONFIGURATION
# =====================================================================
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1              # Mikrofonkanäle (Raspberry Pi/ReSpeaker meist 1)
RATE = 16000              # 16000 Hz ist Standard für Wakewords
RECORD_SECONDS = 1.0      # Wie lange soll ein Beispiel aufgenommen werden? (1.0 Sekunden ist oft ideal)

INPUT_DEVICE_INDEX = None # Manuelle Vorgabe des Mikrofons (None = automatisch)
# =====================================================================

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

def main():
    print("====================================")
    print(" Wakeword Dataset Recorder (Nerio)  ")
    print("====================================")
    
    label = input("Welches Wort möchtest du aufnehmen? (Z.B. 'wakeword' oder 'background'): ").strip().lower()
    if not label:
        print("Ungültiges Label. Programm wird beendet.")
        return

    # Ordner erstellen in dataset/label/
    dataset_dir = os.path.join("dataset", label)
    os.makedirs(dataset_dir, exist_ok=True)
    
    # Vorhandene Dateien zählen
    existing_files = len([f for f in os.listdir(dataset_dir) if f.endswith(".wav")])
    print(f"\nOrdner '{dataset_dir}' ist bereit. Bisher aufgenommene Dateien: {existing_files}")
    print(f"Es wurde konfiguriert, immer genau {RECORD_SECONDS} Sekunden aufzunehmen.")
    
    p = pyaudio.PyAudio()
    device_index = get_input_device(p)

    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=device_index,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        print(f"Fehler beim Öffnen des Mikrofons: {e}")
        p.terminate()
        return

    print("\nANLEITUNG:")
    print(" - Drücke ENTER, um sofort eine Aufnahme zu starten.")
    print(" - Tippe 'q' und dann ENTER, um zu beenden.\n")

    count = existing_files
    
    try:
        while True:
            cmd = input(f"[{count} Beispiele] -> ENTER für Aufnahme (oder 'q' zum Beenden): ")
            if cmd.strip().lower() == 'q':
                break
                
            print(f"🎙️ Nehme für {RECORD_SECONDS} Sekunden auf...")
            frames = []
            
            # Berechne wie viele Chunks wir für die gewünschte Zeit aufnehmen müssen
            num_chunks = int(RATE / CHUNK * RECORD_SECONDS)
            
            for _ in range(num_chunks):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                
            print("🛑 Aufnahme beendet!")
            
            # Speichern der Audiodatei mit einer eindeutigen ID
            filename = os.path.join(dataset_dir, f"{uuid.uuid4().hex[:8]}.wav")
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
            
            count += 1
            print(f"💾 Gespeichert als: {filename}\n")
            
    except KeyboardInterrupt:
        pass
    finally:
        print("\nBeende Recorder...")
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    main()
