from __future__ import annotations

import os

# Curated core dictionary: interior/archviz terms, hand-picked translations.
# Always wins over the bundled bulk dictionary below.
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
    # Interior terms where the bulk dictionary picks the wrong base sense.
    "haus": "house", "schiene": "rail", "herd": "stove",
    "wasserhahn": "faucet", "kronleuchter": "chandelier",
    "leiste": "trim", "steckdose": "socket", "spuele": "sink",
    "spüle": "sink", "geschirrspueler": "dishwasher",
    "geschirrspüler": "dishwasher", "kuehlschrank": "fridge",
    "kühlschrank": "fridge",
}

EN_TO_DE = {}
for _de, _en in DE_TO_EN.items():
    EN_TO_DE.setdefault(_en, _de)

# ---- Bundled bulk dictionaries (data/<lang>_en.tsv) -----------------------
# One compact single-word file per source language, "src \t en \t flag":
#   de  distilled from the TU-Chemnitz Ding dictionary (GPL)
#   fr/es/it/nl/pl/cs/pt/ru/tr  distilled from the FreeDict project (GPL)
# Flag "A" marks source words whose form is also an English word ("hut",
# "pain", "sale") -- those are only translated when the name shows other
# evidence for that language (see naming/translate.py).
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Source languages in lookup-priority order (de first: primary use case).
BULK_LANGS = ("de", "fr", "es", "it", "nl", "pl", "cs", "pt", "ru", "tr")

BULK: dict[str, dict[str, str]] = {}       # lang -> {src: en}
AMBIG: dict[str, set[str]] = {}            # lang -> src words that look English
WORDS: dict[str, set[str]] = {}            # lang -> non-ambiguous src words


def _load_bulk(lang: str) -> None:
    mapping: dict[str, str] = {}
    amb: set[str] = set()
    try:
        with open(os.path.join(_DATA_DIR, lang + "_en.tsv"),
                  encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                mapping.setdefault(parts[0], parts[1])
                if len(parts) > 2 and parts[2] == "A":
                    amb.add(parts[0])
    except Exception:
        pass  # plugin still works without this language pack
    BULK[lang] = mapping
    AMBIG[lang] = amb
    # Ambiguous forms are kept OUT of the word sets: they must neither skew
    # the language statistics nor count as language evidence on their own.
    WORDS[lang] = {w for w in mapping if w not in amb}


for _lang in BULK_LANGS:
    _load_bulk(_lang)

BULK_DE_EN = BULK["de"]
BULK_EN_DE: dict[str, str] = {}
for _de, _en in BULK_DE_EN.items():
    BULK_EN_DE.setdefault(_en, _de)
AMBIGUOUS = AMBIG["de"]

DE_WORDS = set(DE_TO_EN.keys()) | WORDS["de"]
EN_WORDS = set(DE_TO_EN.values()) | {
    "lights", "chairs", "walls", "plants", "trees", "props", "cushion",
    "rug", "shelf", "stairs", "cam", "bathroom",
} | set(BULK_DE_EN.values())

# Words that exist in exactly ONE source language (and are not English):
# such a token alone is enough evidence for its language.
_seen: dict[str, str | None] = {}
for _lang in BULK_LANGS:
    for _w in WORDS[_lang]:
        _seen[_w] = None if _w in _seen else _lang
UNIQUE_LANG: dict[str, str] = {w: lg for w, lg in _seen.items()
                               if lg is not None and w not in EN_WORDS}
for _w in DE_TO_EN:                # curated German is always German evidence
    UNIQUE_LANG.setdefault(_w, "de")
del _seen


def _deumlauted(token: str) -> str:
    """ASCII transcription back to umlauts ('fussboden' -> 'fußboden',
    'staender' -> 'ständer') so transcribed names still hit the dictionary."""
    return (token.replace("ae", "ä").replace("oe", "ö")
            .replace("ue", "ü").replace("ss", "ß"))


def _bulk_en(token: str, include_ambiguous: bool) -> str | None:
    if not include_ambiguous and token in AMBIGUOUS:
        return None
    return BULK_DE_EN.get(token)


def to_english(token: str, include_ambiguous: bool = False) -> str:
    """DE -> EN. By default bulk entries whose German form is also an English
    word ('wall', 'hut', 'rat') are NOT translated -- safe for naming
    normalization and keyword matching, and keeps renames idempotent
    (wand -> wall must not become bulwark on the next pass). The guarded
    translate flow passes include_ambiguous=True and applies its own
    German-evidence check."""
    hit = DE_TO_EN.get(token) or _bulk_en(token, include_ambiguous)
    if hit is None:
        alt = _deumlauted(token)
        if alt != token:
            hit = DE_TO_EN.get(alt) or _bulk_en(alt, include_ambiguous)
    return hit or token


def to_english_raw(token: str) -> str:
    return to_english(token, include_ambiguous=True)


def lookup_en(token: str, lang: str,
              include_ambiguous: bool = False) -> str | None:
    """Single-language raw lookup <lang> -> EN (None if unknown)."""
    if lang == "de":
        hit = DE_TO_EN.get(token)
        if hit:
            return hit
    if not include_ambiguous and token in AMBIG.get(lang, ()):
        return None
    return BULK.get(lang, {}).get(token)


def candidate_langs(token: str) -> list[str]:
    """All source languages that know this token (raw, incl. ambiguous)."""
    out = [lg for lg in BULK_LANGS
           if token in BULK[lg] or (lg == "de" and token in DE_TO_EN)]
    return out


def to_german(token: str) -> str:
    return EN_TO_DE.get(token) or BULK_EN_DE.get(token, token)


def add_translations(extra: dict) -> None:
    for de, en in extra.items():
        de, en = de.lower(), en.lower()
        DE_TO_EN[de] = en
        EN_TO_DE.setdefault(en, de)
        DE_WORDS.add(de)
        EN_WORDS.add(en)
