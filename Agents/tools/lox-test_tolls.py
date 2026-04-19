import requests

MINISERVER = "https://172.18.13.247"  # oder https, wenn dein Miniserver das unterstützt
USER = "admin"
PASS = "kasimir!25" 

# Globales Mapping Name → UUID
UUID_LOOKUP = {}

# -----------------------------
# 1️⃣ Hilfsfunktion: TOON-Serialisierung
# -----------------------------
def toon_serialize(obj, indent=0):
    """Rekursiv ein dict in TOON-Format serialisieren"""
    lines = []
    pad = " " * indent
    for k, v in obj.items():
        if isinstance(v, dict):
            lines.append(f"{pad}{k}:")
            lines.append(toon_serialize(v, indent + 4))
        elif isinstance(v, list):
            # primitive arrays
            lines.append(f"{pad}{k}[{len(v)}]: {','.join(map(str, v))}")
        else:
            lines.append(f"{pad}{k}: {v}")
    return "\n".join(lines)

# -----------------------------
# 2️⃣ Funktion: Loxone JSON laden & TOON-Objekt erzeugen
# -----------------------------
def get_loxone_toon(miniserver, user, pwd):
    global UUID_LOOKUP
    UUID_LOOKUP = {}  # Reset

    url = f"{miniserver}/data/LoxAPP3.json"
    resp = requests.get(url, auth=(user, pwd), verify=False)
    if resp.status_code != 200:
        raise RuntimeError(f"LoxAPP3.json konnte nicht geladen werden: {resp.status_code}")

    data = resp.json()
    controls = data.get("controls", {})
    rooms = data.get("rooms", {})
    
    # Room-ID → Raumname
    room_lookup = {rid: r.get("name", "Unbekannter Raum") for rid, r in rooms.items()}

    result = {"controls": {}}

    # Rekursive Verarbeitung der Controls
    def recurse(ctrl_dict, parent_room_id=None):
        for uuid, ctrl in ctrl_dict.items():
            name = ctrl.get("name", "OhneName")
            room_id = ctrl.get("room", parent_room_id)
            room_name = room_lookup.get(room_id, "Kein Raum")

            # UUID speichern für Lookup
            UUID_LOOKUP[name] = uuid

            # TOON-Objekt erstellen
            result["controls"][name] = {"room": room_name}

            # SubControls
            sub = ctrl.get("subControls", {})
            if sub:
                recurse(sub, room_id)

    recurse(controls)
    return toon_serialize(result)

# -----------------------------
# 3️⃣ Funktion: UUID anhand exaktem Namen abrufen
# -----------------------------
def get_uuid_by_name(name: str):
    return UUID_LOOKUP.get(name)

# TOON-Format ausgeben
toon_text = get_loxone_toon(MINISERVER, USER, PASS)
print(toon_text)

# UUID für ein bestimmtes Gerät
uuid = get_uuid_by_name("RGBW 24V Dimmer Tree")
print(uuid)
