# NerioAI

NerioAI is a new AI Agent with many extensions

# Functions:

- Nerio can edit and read your email with an imap and smtp server.

- Nerio can edit and read your connected Microsoft Outlook Calendar.

- Nerio can with the client send Shell Commands to your PC on Windows.

- Soon Nerio will can conect to your Loxone Smarthome.

# Setting up the Server

To start the Server install Python 3.11.9 the requirements

To install Python visit: https://www.python.org/downloads/

To download the requirements run: 
```
pip install -r reqirements
```

If there is any Problem with Chatterbox, please visit: https://github.com/resemble-ai/chatterbox

Or try:

```
pip install -U pip setuptools wheel
pip install "numpy>=1.24,<1.26" 
pip install --no-build-isolation "pkuseg==0.0.25"

pip install torch==2.6.0+cu118 torchvision==0.21.0+cu118 torchaudio==2.6.0+cu118 --index-url https://download.pytorch.org/whl/cu118

pip install xformers==0.0.25

pip install chatterbox-tts
```

Then run again:
```
pip install -r requirements.txt
```
At least run this to start the Server:
```
python3 app.py
```
To disable the audio output set the audio_output in line 19 in app.py to False 
```
audio_output=False
```
# Using the hosted Server

If you don´t want to host the server yourself visit: Comming Soon

# Starting the client

Important: This function is only avaible on Windows at this time!

To start the client download the .exe or run after you´d install the requirements:
```
python3 client.py
```
