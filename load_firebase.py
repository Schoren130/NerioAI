import firebase_admin
from firebase_admin import credentials, firestore
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Firebase Admin SDK initialisieren
cred = credentials.Certificate(json.loads(os.environ.get("GOOGLE_CREDENTIALS")))
firebase_admin.initialize_app(cred)

# Firestore Client erstellen
db = firestore.client()