# API-Referenz

Die vollständige Endpoint-Tabelle inkl. curl-Rezepten und Fehlerbildern lebt
(noch) beim Vorgänger-Skill:
[../../scene-architect/references/api.md](../../scene-architect/references/api.md)

Kurzform der hier gebrauchten Endpoints (Basis `http://127.0.0.1:8787/api/`,
Web-Dialog in C4D muss offen sein):

| Endpoint | Zweck |
|---|---|
| `export` | frischen `var/scene_report.json` schreiben |
| `presets` / `apply_preset` | Preset-Liste / Preset aktivieren |
| `plan_all` | kombinierte Vorschau (Naming+Structure+Layers) |
| `plan_naming` / `plan_layers` / `plan_structure` | Einzel-Vorschauen |
