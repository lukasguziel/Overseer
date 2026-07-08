# Review-Checkliste — Preset-Abnahme aus Profi-Artist-Sicht

Vor der Übergabe jeden Punkt gegen den Dry-Run-Output abhaken.

## Regeln

- [ ] Jede Regel geht auf einen **bestätigten** Interview-Punkt zurück
      (kein Befund ohne Zustimmung wurde zur Regel).
- [ ] Jede `prefix`-Regel matcht die im Miner belegte Achse; `_evidence`
      entfernt.
- [ ] Keine Regel benennt Objekte um, die die Konvention bereits erfüllen
      (Dry-Run: renames = genau die Gegenbeispiele aus dem Interview).
- [ ] `compile_rules` ohne Warnings (validate_preset grün).

## Naming-Sicherheit

- [ ] Globales Casing zerstört keine erkannte Gewohnheit (Suffixe wie `_GEO`,
      Bindestriche, Punkt-Notation) — sonst keep_separators/apply_casing aus.
- [ ] Führende Etagen-/Ebenen-Indizes (`0.`, `-1.`, `EG_`) überleben.
- [ ] Bedeutungstragende Nummern werden nicht renummeriert.
- [ ] Junk-Namen (`Cube`, `Null` …) werden nicht durch Casing „geadelt",
      sondern bleiben als Todos sichtbar.

## Struktur

- [ ] `structure` bildet die EIGENE Taxonomie des Users ab (Roots aus den
      Reports), keine erfundene.
- [ ] Aliases decken die realen Schreibweisen aller analysierten Projekte ab.
- [ ] Kein Reparenting-Vorschlag bei Szenen mit gewachsener, funktionierender
      Hierarchie (Tidy reicht).

## Preset-Hygiene

- [ ] schema 2, meta.id/name/description gefüllt; description enthält das
      Interview-Protokoll (bestätigt/abgelehnt/doku).
- [ ] Dry-Run gegen JEDEN analysierten Report gelaufen; total ops plausibel
      und erklärbar.
- [ ] pytest + ruff grün (CI-Gate).
- [ ] Übergabetext nennt, was bewusst NICHT automatisiert wurde und warum.
