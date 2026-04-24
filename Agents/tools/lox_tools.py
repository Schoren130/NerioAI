import requests
from agents import function_tool
import json
from load_firebase import db
from flask import session

"""MINISERVER = "https://192.168.1.137"  # oder https, wenn dein Miniserver das unterstützt
USER = "admin"
PASS = "kasimir!25" """

UUID_LOOKUP = {}
def load_user_config():
    username = session.get("username", None)

    
    user_doc = db.collection("users").document(username).get()
    if user_doc.exists:
        user = user_doc.to_dict()
        MINISERVER = user["loxone_ip"]
        USER = user["loxone_user"]
        PASS = user["loxone_pass"]
    

@function_tool
def get_loxone_name():
    print("get_loxone_name aufgerufen")
    load_user_config()
    global UUID_LOOKUP
    UUID_LOOKUP = {}
    
    url = f"{MINISERVER}/data/LoxAPP3.json"
    response = requests.get(url, auth=(USER, PASS), verify=False)
    if response.status_code != 200:
        return {"error": f"LoxAPP3.json konnte nicht geladen werden: {response.status_code}"}

    data = response.json()
    controls = data.get("controls", {})
    rooms = data.get("rooms", {})

    room_lookup = {rid: r.get("name", "Unbekannter Raum") for rid, r in rooms.items()}
    result = {}

    def recurse(ctrl_dict, parent_room_id=None):
        for uuid, ctrl in ctrl_dict.items():
            name = ctrl.get("name", "OhneName")
            room_id = ctrl.get("room", parent_room_id)
            room_name = room_lookup.get(room_id, "Kein Raum")
            UUID_LOOKUP[(name, room_name)] = uuid
            result[name] = {"room": room_name}
            sub = ctrl.get("subControls", {})
            if sub:
                recurse(sub, room_id)

    recurse(controls)
    print(json.dumps(result, indent=4, ensure_ascii=False))
    return result

def get_uuid_by_name(name: str, room: str):
    load_user_config()
    print("get_uuid_by_name")
    #get_loxone_name()
    return UUID_LOOKUP.get((name, room))

@function_tool
def light(kommando: str, name: str, room: str):
    load_user_config()
    print("light aufgerufen")
    uuid= get_uuid_by_name(name,room)
    print(uuid)
    """mögliches Kommando: "on", "off", "impulse", je nach Block"""
    url = f"{MINISERVER}/jdev/sps/io/{uuid}/{kommando}"
    # falls Basic Auth
    resp = requests.get(url, auth=(USER, PASS), verify=False)  # verify=False, wenn self-signed Zertifikat
    #print(resp)
    # falls Command Encryption / Hashing nötig, müsste die URL entsprechend angepasst werden
    print("Status Code:", resp.status_code)
    print("Antwort:", resp.text)

# Beispiel: einschalte

# Beispiel: ausschalten
#schalte(UUID, "off")

@function_tool
def set_rgbw_strip(h: int, s: int, v: int, name: str, room: str):
    load_user_config()
    uuid= get_uuid_by_name(name,room)
    if h>100:
        h = 100
    if s > 100:
        s = 100
    if v > 100:
        v = 100    
    cmd = f"hsv({h},{s},{v})"
    url = f"{MINISERVER}/jdev/sps/io/{uuid}/{cmd}"
    resp = requests.get(url, auth=(USER, PASS), verify=False)
    print("URL:", url)
    print("Status Code:", resp.status_code)
    try:
        data = resp.json()
        print("JSON Antwort:", data)
        return data
    except ValueError:
        print("Antwort (Text):", resp.text)
    return resp

@function_tool
def get_state(name: str, room: str):
    load_user_config()
    uuid= get_uuid_by_name(name,room)
    url = f"{MINISERVER}/jdev/sps/io/{uuid}"
    resp = requests.get(url, auth=(USER, PASS), verify=False)
    try:
        print(resp.json())
        return resp.json()
    except:
        return resp.text

#print(get_loxone_name())
#light("on","Tischlampe","Esszimmer")
