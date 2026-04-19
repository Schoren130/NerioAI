import msal
import requests
import webbrowser
import os
import json
from flask import session
from agents import function_tool  # type: ignore
from datetime import datetime, timezone
import dateutil.parser


# ---------- Azure AD Konfiguration ----------
CLIENT_ID = 'a559bb35-722e-4097-955f-91b2d5d4a233'
TENANT_ID = "f29b5a6d-8658-43ff-b3d5-13a41e786135"
AUTHORITY = f'https://login.microsoftonline.com/common'
SCOPE = ['Calendars.ReadWrite']

GRAPH_URL = "https://graph.microsoft.com/v1.0/me"
USER_CACHE_FILE = "user_tokens.json"


# ---------- Hilfsfunktionen für Cache ----------
def load_all_caches():
    print("loading file")
    if os.path.exists(USER_CACHE_FILE):
        with open(USER_CACHE_FILE, "r") as f:
            print("loading finished")
            return json.load(f)
        print("loading finished")
    return {}


def save_all_caches(all_caches):
    with open(USER_CACHE_FILE, "w") as f:
        json.dump(all_caches, f)


# ---------- Token Handling ----------
def get_token():
    print("getting token")
    if "username" not in session:
        print("Test")
        raise Exception("Kein User in der Session. Bitte einloggen.")
    

    user_id = session.get("username", None)
    all_caches = load_all_caches()
    print("test")
    print(all_caches)

    # Lade Cache für diesen User, falls vorhanden
    cache = msal.SerializableTokenCache()
    if user_id in all_caches:
        cache.deserialize(all_caches[user_id])

    print("test2")

    app_msal = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    print("loaded msal")
    accounts = app_msal.get_accounts()
    print("checked accounts")
    print(accounts)
    if accounts:
        print("account found")
        result = app_msal.acquire_token_silent(SCOPE, account=accounts[0])
        print("having result")
        if result and "access_token" in result:
            print("something in result")
            return result["access_token"]
        
    print("going to open website")
    

    # Wenn kein gültiger Token → Device Flow starten
    """flow = app_msal.initiate_device_flow(scopes=SCOPE)
    if "user_code" not in flow:
        raise Exception("Fehler beim Device Flow: " + str(flow))
    print(flow["message"])
    webbrowser.open(flow["verification_uri"])"""

    result = app_msal.acquire_token_interactive(scopes=SCOPE)

    print(result)

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
    ("checking calendar")
    token = get_token()
    url = f"{GRAPH_URL}/calendarview?startDateTime={start_datetime}&endDateTime={end_datetime}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        raise Exception(f"Fehler beim Abrufen: {response.status_code} {response.text}")


@function_tool
async def delete_or_shorten_events(start_datetime: str, end_datetime: str):
    print("deleting events")
    """
    Löscht alle Events vollständig im Zeitraum [start_datetime, end_datetime].
    Kürzt Events, die über den Zeitraum hinausragen (z.B. 9-11 Uhr bei Löschung 10-12 Uhr).
    """
    token = get_token()
    print("got token")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    from datetime import timezone

    start_dt = dateutil.parser.parse(start_datetime)
    end_dt = dateutil.parser.parse(end_datetime)

    # Immer auf UTC konvertieren
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    else:
        start_dt = start_dt.astimezone(timezone.utc)

    if end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)
    else:
        end_dt = end_dt.astimezone(timezone.utc)

    print("parsed datetime")
    # Schritt 1: Alle Events im erweiterten Zeitraum holen (um auch überlappende zu erwischen)
    url = f"{GRAPH_URL}/calendarview?startDateTime={start_dt.isoformat().replace('+00:00', 'Z')}&endDateTime={end_dt.isoformat().replace('+00:00', 'Z')}"

    response = requests.get(url, headers=headers)
    print("got response")
    if response.status_code != 200:
        raise Exception(f"Fehler beim Abrufen: {response.status_code} {response.text}")
    
    events = response.json().get("value", [])
    changed = []
    print("got events")
    try:
        for event in events:
            ev_id = event["id"]
            ev_start = dateutil.parser.parse(event["start"]["dateTime"])
            ev_end = dateutil.parser.parse(event["end"]["dateTime"])

            # immer UTC-aware
            if ev_start.tzinfo is None:
                ev_start = ev_start.replace(tzinfo=timezone.utc)
            else:
                ev_start = ev_start.astimezone(timezone.utc)

            if ev_end.tzinfo is None:
                ev_end = ev_end.replace(tzinfo=timezone.utc)
            else:
                ev_end = ev_end.astimezone(timezone.utc)

            print("parsed events")
            print(event)

            # Fall 1: Event komplett im Löschbereich → löschen
            if ev_start >= start_dt and ev_end <= end_dt:
                del_url = f"{GRAPH_URL}/events/{ev_id}"
                del_resp = requests.delete(del_url, headers=headers)
                if del_resp.status_code in [204, 200]:
                    print("deleted")
                    changed.append({"action": "deleted", "id": ev_id, "subject": event.get("subject")})
                else:
                    print("Fehler beim komplett löschen")
                    raise Exception(f"Fehler beim Löschen: {del_resp.status_code} {del_resp.text}")

            # Fall 2: Event beginnt vor Zeitraum, endet aber im Zeitraum → Ende anpassen
            elif ev_start < start_dt < ev_end <= end_dt:
                patch_url = f"{GRAPH_URL}/events/{ev_id}"
                patch_data = {
                    "end": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Berlin"}
                }
                patch_resp = requests.patch(patch_url, headers=headers, json=patch_data)
                if patch_resp.status_code in [200, 202]:
                    changed.append({"action": "shortened_end", "id": ev_id, "subject": event.get("subject")})
                else:
                    print("Fehler1")
                    raise Exception(f"Fehler beim Kürzen (Ende): {patch_resp.status_code} {patch_resp.text}")

            # Fall 3: Event beginnt im Zeitraum, endet danach → Start anpassen
            elif start_dt <= ev_start < end_dt < ev_end:
                patch_url = f"{GRAPH_URL}/events/{ev_id}"
                patch_data = {
                    "start": {"dateTime": end_dt.isoformat(), "timeZone": "Europe/Berlin"}
                }
                patch_resp = requests.patch(patch_url, headers=headers, json=patch_data)
                if patch_resp.status_code in [200, 202]:
                    changed.append({"action": "shortened_start", "id": ev_id, "subject": event.get("subject")})
                else:
                    print("Fehler2")
                    raise Exception(f"Fehler beim Kürzen (Start): {patch_resp.status_code} {patch_resp.text}")

            # Fall 4: Event überlappt beidseitig (beginnt vor und endet nach Zeitraum)
            elif ev_start < start_dt and ev_end > end_dt:
                # Split-Variante: Zwei Events daraus machen (optional – hier nur Kürzung des mittleren Bereichs)
                patch_url = f"{GRAPH_URL}/events/{ev_id}"
                patch_data = {
                    "end": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Berlin"}
                }
                patch_resp = requests.patch(patch_url, headers=headers, json=patch_data)
                if patch_resp.status_code in [200, 202]:
                    changed.append({"action": "cut_middle_part", "id": ev_id, "subject": event.get("subject")})
                else:
                    print("Fehler3")
                    raise Exception(f"Fehler beim Kürzen (beidseitig): {patch_resp.status_code} {patch_resp.text}")
            else:
                print("no match")
    except Exception as e:
        print(e)
    print("returnning")
    print({"changed_events": changed, "count": len(changed)})
    return {"changed_events": changed, "count": len(changed)}
