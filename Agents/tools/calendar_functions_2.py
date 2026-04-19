import msal
import requests
import webbrowser
import os
import json
from flask import Flask, session
from agents import function_tool  # type: ignore

# ---------- Azure AD Konfiguration ----------
CLIENT_ID = 'a559bb35-722e-4097-955f-91b2d5d4a233'
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPE = ['Calendars.ReadWrite']

GRAPH_URL = "https://graph.microsoft.com/v1.0/me"
USER_CACHE_FILE = "user_tokens.json"


# ---------- Hilfsfunktionen für Cache ----------
def load_all_caches():
    if os.path.exists(USER_CACHE_FILE):
        with open(USER_CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_all_caches(all_caches):
    with open(USER_CACHE_FILE, "w") as f:
        json.dump(all_caches, f)


# ---------- Token Handling ----------
def get_token():
    if "username" not in session:
        print("Test")
        raise Exception("Kein User in der Session. Bitte einloggen.")
    

    user_id = session.get("username", None)
    all_caches = load_all_caches()

    # Lade Cache für diesen User, falls vorhanden
    cache = msal.SerializableTokenCache()
    if user_id in all_caches:
        cache.deserialize(all_caches[user_id])

    app_msal = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    accounts = app_msal.get_accounts()

    if accounts:
        result = app_msal.acquire_token_silent(SCOPE, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]

    # Wenn kein gültiger Token → Device Flow starten
    flow = app_msal.initiate_device_flow(scopes=SCOPE)
    if "user_code" not in flow:
        raise Exception("Fehler beim Device Flow: " + str(flow))
    print(flow["message"])
    webbrowser.open(flow["verification_uri"])

    result = app_msal.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        # Speichere Cache für User
        all_caches[user_id] = cache.serialize()
        save_all_caches(all_caches)
        return result["access_token"]
    else:
        raise Exception(f"Login fehlgeschlagen: {result.get('error_description')}")


# ---------- Funktionen für Kalender ----------
@function_tool
async def create_event(
        title: str,
        start_datetime: str,
        end_datetime: str,
        location: str = "",
        body: str = "") -> None:
    token = get_token()
    event = {
        "subject": title,
        "start": {"dateTime": start_datetime, "timeZone": "Europe/Berlin"},
        "end": {"dateTime": end_datetime, "timeZone": "Europe/Berlin"},
        "location": {"displayName": location},
        "body": {"contentType": "HTML", "content": body}
    }

    url = f"{GRAPH_URL}/events"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=event)

    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Fehler beim Erstellen: {response.status_code} {response.text}")


@function_tool
async def get_events(start_datetime: str, end_datetime: str):
    token = get_token()
    url = f"{GRAPH_URL}/calendarview?startDateTime={start_datetime}&endDateTime={end_datetime}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        raise Exception(f"Fehler beim Abrufen: {response.status_code} {response.text}")