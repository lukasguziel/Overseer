"""DE<->EN Woerterbuch fuer Interior/ArchViz-Begriffe (rein, datengetrieben)."""

from __future__ import annotations

# Kanonische Zuordnung Deutsch -> Englisch. Umlaute zusaetzlich als ae/oe/ue.
DE_TO_EN = {
    "licht": "light", "lichter": "light", "lampe": "lamp", "leuchte": "light",
    "beleuchtung": "lighting", "sonne": "sun", "himmel": "sky",
    "kamera": "camera",
    "stuhl": "chair", "stuehle": "chair", "stühle": "chair",
    "tisch": "table", "wand": "wall", "waende": "wall", "wände": "wall",
    "boden": "floor", "decke": "ceiling",
    "fenster": "window", "tuer": "door", "tuere": "door", "tür": "door",
    "sofa": "sofa", "couch": "couch", "teppich": "carpet",
    "pflanze": "plant", "pflanzen": "plant", "baum": "tree", "baeume": "tree",
    "bäume": "tree", "aussen": "exterior", "außen": "exterior",
    "innen": "interior", "moebel": "furniture", "möbel": "furniture",
    "kueche": "kitchen", "küche": "kitchen", "bad": "bathroom",
    "schrank": "cabinet", "regal": "shelf", "bett": "bed",
    "vorhang": "curtain", "spiegel": "mirror", "treppe": "stairs",
    "saeule": "column", "säule": "column", "dach": "roof", "mauer": "wall",
    "gebaeude": "building", "gebäude": "building", "raum": "room",
    "zimmer": "room", "buero": "office", "büro": "office",
    "umgebung": "environment", "gruppe": "group", "objekt": "object",
    "kissen": "pillow", "wohnzimmer": "livingroom",
    "schlafzimmer": "bedroom", "esszimmer": "diningroom",
    "garten": "garden", "hof": "yard", "fassade": "facade",
    "aussenbereich": "exterior", "innenbereich": "interior",
}

# Reverse: Englisch -> Deutsch (erste kanonische Ruecktrefferwahl).
EN_TO_DE = {}
for _de, _en in DE_TO_EN.items():
    EN_TO_DE.setdefault(_en, _de)

# Vollstaendige Wortmengen fuer die Sprach-Erkennung.
DE_WORDS = set(DE_TO_EN.keys())
EN_WORDS = set(DE_TO_EN.values()) | {
    "lights", "chairs", "walls", "plants", "trees", "props", "cushion",
    "rug", "shelf", "stairs", "cam", "bathroom",
}


def to_english(token: str) -> str:
    return DE_TO_EN.get(token, token)


def to_german(token: str) -> str:
    return EN_TO_DE.get(token, token)


def add_translations(extra: dict) -> None:
    """Erweitert das Woerterbuch zur Laufzeit um zusaetzliche de->en Paare.

    Seiteneffekt auf die Modul-Globals -- gedacht fuer den einmaligen Config-Load
    (Hot-Reload importiert das Modul ohnehin frisch, keine Akkumulation).
    """
    for de, en in extra.items():
        de, en = de.lower(), en.lower()
        DE_TO_EN[de] = en
        EN_TO_DE.setdefault(en, de)
        DE_WORDS.add(de)
        EN_WORDS.add(en)
