# Roadmap Neubau

Vorgehen in vertikalen Schritten: nach jeder Phase läuft etwas Sichtbares und Getestetes.
Riskante Punkte (cgo, ARM-Build) werden früh angegangen. Architektur und Regeln: siehe `../CLAUDE.md`.

**Grundregel für jede Phase:** Nichts ist fertig, solange es nicht getestet ist. Jedes neue Feature
bekommt seinen gespiegelten Ordner unter `backend/tests/` bzw. `web/tests/features/`, und `make test`
sowie `make lint` sind grün.

## Phase 0 – Fundament
- [x] Struktur `next/`: Go-Modul, `main.go`, Feature-Ordner, gespiegeltes `tests/`
- [x] Architektur-Tests, die die Regeln aus `CLAUDE.md` erzwingen (Spiegelung, keine Unterordner, Abhängigkeitsrichtung)
- [x] SvelteKit (`adapter-static`) + TypeScript, Vitest, Playwright
- [x] Makefile (`test`, `lint`, `dev`, `build`), golangci-lint, ESLint, svelte-check
- [x] CI (GitHub Actions) für `next/**`
- **Fertig, wenn:** `make test` und `make lint` grün; Binary liefert UI + `/api/health` aus; E2E-Test prüft das.

## Phase 1 – Protokoll (`protocol`)
- [ ] Checksumme, HTTP-Verschlüsselung
- [ ] Befehle bauen: AT+C, M, W, N, X, P, Y
- [ ] Antworten parsen: AT+V, S, T (inkl. ältere Firmware mit kürzeren Antworten)
- [ ] Echte Strings sammeln (Roboter / Legacy-Debug-Logs) → Golden-Files in `tests/protocol/testdata/`
- **Fertig, wenn:** jeder Befehl/jede Antwort aus Legacy `sunraycommstack.py` abgedeckt und getestet ist.

## Phase 2 – Simulator & Robot-Zustand (`link`, `robot`)
- [ ] `Link`-Interface, `sim.go`: simulierter Roboter (versteht AT-Befehle, fährt, Batterie, Job-Wechsel)
- [ ] `robot`: abgeleiteter Status, Befehle mit Stop-Vorrang, Online-Erkennung
- **Fertig, wenn:** `tests/robot` spielt Mähen → Stop → Docken gegen den Simulator durch.

## Phase 3 – Erster Durchstich bis zum Browser (`server`, Web)
- [ ] WebSocket-Hub, REST-Befehle
- [ ] UI: Live-Karte (Canvas) mit Roboterposition, Status, Start/Stop/Dock, Joystick
- **Fertig, wenn:** `make dev` startet mit Simulator, Roboter bewegt sich flüssig im Browser, Playwright-Test läuft.
- Architektur-Review: trägt die Struktur? Wenn nicht, jetzt nachschärfen.

## Phase 4 – Echte Verbindungen (`link`)
- [ ] `http.go` (inkl. Verschlüsselung), `uart.go`, `mqtt.go`
- [ ] Reconnect, Timeouts, alles über `context`
- **Fertig, wenn:** die neue App einen echten Roboter steuert (mindestens über den eigenen Verbindungsweg).

## Phase 5 – Einstellungen & Karten (`settings`, `maps`)
- [ ] Settings laden/speichern/in der UI bearbeiten
- [ ] Legacy-Import aus `~/.cassandra` (Configs, Karten, Tasks)
- [ ] Karten-Editor: Perimeter, Ausschlüsse, Dockpunkte, Suchdraht; mehrere Karten
- [ ] Upload zum Roboter (AT+W/N/X, 30er-Pakete, map_crc prüfen)
- **Fertig, wenn:** die echte Karte importiert, angezeigt und zum Roboter übertragen wird.

## Phase 6 – Planner (parallel zu Phase 2–5 möglich)
- [ ] Im Planner-Repo: C-API, CMake-Target als statische Lib ohne pybind, Tests, Tippfehler `mowExclusionsBoder` korrigieren, Tag
- [ ] Hier: Submodule `third_party/PathPlannerCore`, `planner/cgo.go`, `testkit.FakePlanner`
- [ ] Machbarkeitstest ARM-Build: Go + statische C++-Lib für arm64 (Docker buildx oder zig cc), auf dem Pi starten
- **Fertig, wenn:** `make test-cpp` grün und das arm64-Binary auf dem Pi eine Route berechnet.

## Phase 7 – Aufgaben & Mähen (`tasks`)
- [ ] Teilflächen wählen, Parameter, Route berechnen, Vorschau in der UI
- [ ] Aufgaben speichern, Reihenfolge, mehrere zu einer Route verketten
- [ ] Mähen starten, Fortschritt, zu Fortschritt springen, Punkt überspringen
- [ ] Goto mit A*-Wegfindung aus dem Planner
- **Fertig, wenn:** eine komplette Mähaufgabe vom Planen bis zum Docken auf dem echten Roboter läuft.

## Phase 8 – Zeitplan & Statistik (`schedule`, `stats`)
- [ ] Wochenplan mit `Clock`-Interface (Tests mit `FakeClock`), Start/Docken nach Plan
- [ ] Verlauf Batterie, Mähzeit, GPS-Qualität; Speicherung (JSON oder SQLite – entscheiden), Diagramme
- **Fertig, wenn:** der Zeitplan an einem realen Tag automatisch mäht.

## Phase 9 – MQTT-API (`mqttapi`)
- [ ] Kompatibel zur Legacy-API (alle Topics, Payloads)
- [ ] Kompatibilitätstests mit mitgeschnittenen Legacy-Payloads
- **Fertig, wenn:** die bestehende Home-Automation ohne Änderung funktioniert.

## Phase 10 – Abschluss
- [ ] Log-Ansicht mit eigener Befehlseingabe, Systeminfos (CPU, RAM, Temperatur), Feinschliff mobile Ansicht
- [ ] Releases: Binaries amd64/arm64, Docker-Image, systemd-Unit, Installationsanleitung
- [ ] Testlauf parallel zur Legacy-App, dann Umstieg; `CaSSAndRA/` erst danach entfernen

## Offene Entscheidungen
- Statistik-Speicherung: JSON oder SQLite (bis Phase 8)
- Phase 4: alle drei Verbindungswege sofort oder zuerst nur der genutzte
