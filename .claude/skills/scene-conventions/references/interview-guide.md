# Interview-Guide — Konventionen bestätigen lassen

Regeln fürs Interview: kurz, konkret, immer mit den echten Namen aus der
Szene. Eine Frage pro Befund. Keine Ja/Nein-Suggestivfragen ohne Beleg.
Antworten entscheiden, ob ein Befund Regel, Ausnahme oder nur Doku wird.

## 1. Affixe (Präfix/Suffix)

Pro AFFIXES-Befund mit dominanter Achse:

> **„{N} von {M} {Achse}-Objekten tragen `{AFFIX}`** (z. B. {3 Beispiele}).
> a) Ist das Absicht — soll `{AFFIX}` künftig auf ALLE {Achse} angewendet
>    werden? Dann würde ich {fehlende Namen} umbenennen.
> b) {Intruder-Namen} tragen den Präfix, sind aber kein {Achse} — Ausnahme
>    oder Altlast?"

- a=ja → `prefix`-Regel mit dem Achsen-Match. Die fehlenden Mitglieder werden
  die ersten Renames; im Dry-Run zeigen.
- a=nein („nur in diesem Projekt") → keine Regel; als Projekt-Eigenheit in
  `meta.description` notieren.
- Suffix-Befunde: Regel gibt es (noch) nicht — fragen, ob die Gewohnheit
  wichtig ist. Wenn ja: `apply_casing` so konfigurieren, dass sie überlebt
  (keep_separators / Naming selektiv), und das dem User sagen.

## 2. Casing

> „Global dominiert **{Stil}** ({Verteilung}). {Kategorie} weicht ab
> ({Verteilung der Kategorie}) — Absicht (z. B. Lights immer UPPER) oder
> gewachsen?"

Absicht → `casing` = globaler Stil, Abweichung dokumentieren (die Engine kann
kein Casing pro Kategorie — nicht versprechen!). Gewachsen → Naming-Tab
angleichen lassen.

## 3. Numbering

> „Deine Serien sind {pad}-stellig und starten bei {start}; {Beispiele mit
> Lücken}. Sollen Lücken geschlossen werden (renumber), oder sind die Nummern
> bedeutungstragend (Etage, Variante) und bleiben?"

Bedeutungstragend → KEINE renumber-Regel, `dedupe` ggf. aus.

## 4. Struktur / Taxonomie

> „Deine Top-Container sind {ROOTS}. Ist das dein Standard-Setup für jedes
> Projekt? Welche fehlen hier nur zufällig?"

Bestätigte Container → `structure`-Baum; alternative Schreibweisen aus
anderen Projekten → `aliases`. NIE eine fremde Taxonomie vorschlagen, solange
eine eigene existiert.

## 5. Sprache

> „{X} % deiner Namen sind Deutsch, {Y} % Englisch. Ziel: alles {en/de},
> oder gemischt lassen und nur neue Objekte konsequent?"

Gemischt lassen → `language: null` (kein Übersetzen im Naming), Translate-Tab
als Werkzeug für gezielte Fälle empfehlen.

## 6. Junk & Duplikate

> „{N} Objekte heißen noch `Cube`/`Null` &c. ({Beispiele}) — umbenennen
> lassen oder ist das Absicht (z. B. Platzhalter)?"

> „`{Name}` existiert {N}×. Eindeutig machen (Suffix A/B/C oder 01/02) oder
> so lassen?" → `condition`-Regel mit `duplicates_gt` + `suffix_scheme`.

## Protokoll-Vorlage

Am Ende des Interviews die Entscheidungen als Liste festhalten (wird die
`meta.description` des Presets):

```
Bestätigt: ABC_ vor jedem Spline (Regel prefix_abc_spline)
Bestätigt: 2-stellige Nummern ab 01, per Parent
Abgelehnt: LGT_-Präfix nur Projekt X, keine Regel
Doku:      _GEO-Suffix auf Meshes — Engine erzwingt nicht, Casing schont es
```
