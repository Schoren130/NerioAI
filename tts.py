import torchaudio as ta
import torch
from chatterbox.tts import ChatterboxTTS
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
import uuid
import os

# Automatically detect the best available device
if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

print(f"Using device: {device}")

#model = ChatterboxTTS.from_pretrained(device=device)

#text = "Wie nennt man einen Keks unter einem Baum? Ein schattiges Plätzchen. Haha!"
#wav = model.generate(text)
#ta.save("test-1.wav", wav, model.sr)
def text_to_speech(text):
    multilingual_model = ChatterboxMultilingualTTS.from_pretrained(device=device)

    wav = multilingual_model.generate(text, language_id="de")

    audio_file_name = f"{uuid.uuid4()}.wav"
    audio_file_path = os.path.join("static/audio", audio_file_name)

    ta.save(audio_file_path, wav, multilingual_model.sr)

    return audio_file_path


# If you want to synthesize with a different voice, specify the audio prompt
#AUDIO_PROMPT_PATH = "YOUR_FILE.wav"
#wav = model.generate(text, audio_prompt_path=AUDIO_PROMPT_PATH)
#ta.save("test-3.wav", wav, model.sr)
