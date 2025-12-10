from google.cloud import texttospeech
import uuid
import os


def text_to_speech(text):
    client = texttospeech.TextToSpeechClient(client_options={"api_key": "AIzaSyC0LwH6m5Bw6MMpc9ArC_4ok7HWCFgqoP8"})

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        name="de-DE-Chirp3-HD-Fenrir",
        language_code="de-DE",

    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=44100,
        speaking_rate=1.1
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    os.makedirs("static/audio", exist_ok=True)

    audio_file_name = f"{uuid.uuid4()}.wav"
    audio_file_path = os.path.join("static/audio", audio_file_name)

    with open(audio_file_path, "wb") as f:
        f.write(response.audio_content)
    return audio_file_path
