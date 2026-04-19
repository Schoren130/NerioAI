import firebase_admin
from firebase_admin import credentials, firestore

# Firebase Admin SDK initialisieren
cred = credentials.Certificate("account_key_firebase.json")
firebase_admin.initialize_app(cred)

# Firestore Client erstellen
db = firestore.client()