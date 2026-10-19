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
- [x] Checksumme, HTTP-Verschlüsselung (gegen Legacy-Algorithmus und Firmware geprüft)
- [x] Befehle bauen: AT+C (typsicher, Nullwert = „nichts ändern“), M, W/N/X (Karten-Upload in 30er-Paketen), P, Y
- [x] Antworten parsen: AT+V, S, T, S2, W-Bestätigung (inkl. älterer Firmware; zusätzliche Felder neuerer Firmware werden ignoriert)
- [x] Golden-Files in `tests/protocol/testdata/` (synthetisch nach Firmware-Format, siehe README dort)
- [x] Fuzz-Tests: kein Parser darf bei beliebigen Eingaben abstürzen (2 Funde behoben, als Regression im Korpus)
- [x] Echte Mitschnitte ergänzt: Sunray 1.0.324 (Linux-Simulation) für AT+V, AT+S, AT+T, AT+S2
- [ ] Mitschnitte von echter Hardware (Alfred/Ardumower) ergänzen
- **Ergebnis:** 100 % Abdeckung von `protocol`. Sunray-MQTT-JSON (State/Stats/Props) folgt mit `link/mqtt.go` in Phase 4, Karten-CRC-Vergleich in Phase 5.

## Phase 2 – Simulator & Robot-Zustand (`link`, `robot`)
- [x] `Link`-Interface (`Run` mit `Handler` für Meldungen, `Send` für Befehle) – passt für Anfrage/Antwort (HTTP, UART) und Push (MQTT)
- [x] `Poller`: macht aus einem `Transport` (eine Zeile hin, eine zurück) einen `Link`; Polling-Intervalle wie Legacy, Verschlüsselung, Wiederverbindung
- [x] `sim.go`: simulierter Roboter als `Transport` – versteht AT-Befehle, Karten-Upload, fährt Route und Dockpfad, lädt, Akku, Regen, Joystick, Fehler ohne Route; Zeit läuft nur über `Step` (deterministisch)
- [x] `robot`: Status wie Legacy (offline, idle, move, map upload, mow, transit, docking, charging, docked, error), SoC, Dock-Grund, Befehle
- [x] Sicherheit: nur `Stop` wird wiederholt (3×), `Stop` bricht laufenden Karten-Upload ab statt zu warten
- [x] `testkit.FakeClock`
- **Ergebnis:** `tests/integration` spielt Mähen → Stop → Docken (unverschlüsselt und verschlüsselt), Routenende, Regen und Verbindungsabbruch gegen den Simulator durch. Abdeckung `robot` 100 %, `link` 98 %.

## Phase 3 – Erster Durchstich bis zum Browser (`server`, Web)
- [x] SSE-Hub (`GET /api/events`) statt WebSocket – Begründung in `CLAUDE.md`
- [x] Robot-API: `GET /api/robot/state|map`, `POST /api/robot/<befehl>`, `move`, `mow-motor`, `speed`, `skip-to-progress`
- [x] `app` verdrahtet Simulator → Poller → Robot → Hub/Server; Demo-Garten (`link.DemoMap`) bis Karten existieren
- [x] UI: Live-Karte (Canvas, Zoom/Verschieben/Pinch, Hell/Dunkel), Status, Mähen/Stop/Docken, Joystick
- [x] Tests: Komponenten (jsdom), Zeichnen über aufzeichnenden Canvas-Kontext, E2E mit Klick auf Mähen/Stop/Docken und Joystick
- **Ergebnis:** `make dev` startet mit Simulator, der Roboter fährt im Browser. Backend 98 % Abdeckung, 124 Frontend-Tests, 5 E2E-Tests.
- Architektur-Review: Struktur trägt. Gefunden und behoben: Deadlock in `app.Run` bei Serverfehler, Endlosschleife im Karten-Effekt, schwacher Kontrast des Stop-Knopfs im Dunkelmodus.

## Phase 4 – Echte Verbindungen (`link`)
- [x] `http.go` (inkl. Verschlüsselung), `uart.go` (`LineTransport`, überspringt Konsolenausgaben), `mqtt.go` (Format der Legacy-Bridge)
- [x] Reconnect, Timeouts, alles über `context`; MQTT meldet online erst nach bestätigten Abos
- [x] Auswahl per `app.LinkConfig` / `--link`, Passwörter auch per Umgebungsvariable
- [x] Tests gegen echte Gegenstellen: Simulator hinter `httptest`, serielle Leitung über `net.Pipe`, eingebetteter MQTT-Broker (inkl. Broker-Neustart)
- [x] HTTP gegen echte Sunray-Firmware (1.0.324, Linux-Simulation): Verbindung, Zustand, Statistik, Stop, Mähen, Joystick. Fand einen Parser-Fehler (Zykluszeit in AT+T ist eine Kommazahl; im Bridge-JSON hätte das die ganze Statistik verworfen).
- [ ] **Test mit echtem Roboter**: HTTP auf Hardware, UART, MQTT über die Bridge (offen – braucht Roboter bzw. Bridge; nicht ohne Absprache, da beim Verbinden `AT+P` gesendet wird)
- **Ergebnis:** alle drei Wege implementiert und gegen Simulator/Broker getestet, Gesamtabdeckung 97 %.

## Phase 5 – Einstellungen & Karten (`settings`, `maps`)
- [x] Settings laden/speichern/in der UI bearbeiten: `settings.json` im Datenverzeichnis (`--data-dir`, Standard `~/.cassandra`); Passwörter verlassen das Backend nie; Verbindungswechsel ohne Neustart; Fahr-/Batteriewerte und Positionsmodus wirken sofort. Die `--link`-Flags sind entfallen.
- [x] Legacy-Import beim ersten Start: `user/*.json` (inkl. Zugangsdaten der MQTT-API für Phase 9) und `map/perimeter.json` + `tmp.json` (aktive Karte). Mit den echten Daten getestet: 21 Karten, keine Warnung. Tasks und Zeitplan importieren ihre Features in Phase 7/8 selbst.
- [x] Karten-Editor: Perimeter, Ausschlüsse, Dockpfad, Suchdraht; mehrere Karten; Undo/Redo, Ziehen, Roboterposition als Punkt; neue App-Hülle (Navigation, eigenes Design)
- [x] Upload zum Roboter (AT+W/N/X, 30er-Pakete) mit **exakter map_crc-Prüfung** (Arduino- und Linux-Variante der Firmware nachgebildet, Golden-Werte aus C-Referenz); Upload wird abgelehnt, solange der Roboter fährt
- [x] Upload gegen echte Sunray-Firmware geprüft: Karte „mika“ (127 Perimeterpunkte, 53 Ausschlüsse) an Sunray 1.0.324 (Linux-Simulation); gemeldete map_crc = Arduino-Variante, Prüfung bestanden
- [x] Live-Ansicht nachgeschärft: graue Palette, Rover-Bilder aus der Legacy-App (wählbar, Größe in cm, per SSE `settings` in allen Browsern), Roboter gleitet zwischen Meldungen (wie CaSSAndRA_native), Spur im Backend (neu beim Andocken oder per „Clear trail“), Joystick auch im Dock und nach Fehlern, Seiten bekommen beim Wiederöffnen sofort die letzten Events
- [ ] Optimierung: Zustandsabfragen während eines Uploads pausieren (Simulator ~0,5 s/Anfrage → Upload von „mika“ dauerte 27 s)
- [ ] Später: GeoJSON-/Sunray-Kartenimport und -export wie im Legacy-Code
- **Fertig, wenn:** die echte Karte importiert, angezeigt und zum Roboter übertragen wird. (erledigt)

## Phase 6 – Planner
- [x] Im Planner-Repo (in `main`, Release v1.4.0 inkl. PyPI-Wheel): C-API `planner_c.h` (Mähroute + A*-Weg), CMake-Target `planner_core` ohne pybind, GoogleTests (99 grün; drei alte Tests an die halbe Startlinie angepasst), Tippfehler `mowExclusionsBorder` korrigiert (Python behält den alten Namen), Version 1.4
- [x] Hier: Submodule `third_party/PathPlannerCore`, `planner/` (cgo kompiliert die Quellen selbst, Build-Tag `cpp`), `testkit.FakePlanner`, Golden-Routen aus dem Python-Modul, `make test-cpp`, `cassandra --check-planner`
- [x] CI: Tests mit und ohne Planner; statische Binaries für amd64 und arm64 (native GitHub-Runner) mit `--check-planner`, als Download
- [ ] Auf dem Pi starten: `cassandra-linux-arm64 --check-planner` (Artefakt aus der CI) – zurückgestellt, gerade kein Pi zur Hand
- [x] Planner-Repo: `c-api` nach `main` gemergt, Tag `v1.4.0` (Wheel auf PyPI); Submodule steht auf dem Tag-Commit
- [ ] 32-Bit-Pi (armv7): offen, ob nötig
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
- [ ] Kompatibilitätstests mit mitgeschnittenen Legacy-Payloads (Beispiele für alle Topics stehen in `~/.cassandra/log/cassandra.log*`, Zeilen „API failed to publish“)
- **Fertig, wenn:** die bestehende Home-Automation ohne Änderung funktioniert.

## Phase 10 – Abschluss
- [ ] Log-Ansicht mit eigener Befehlseingabe, Systeminfos (CPU, RAM, Temperatur), Feinschliff mobile Ansicht
- [ ] Releases: Binaries amd64/arm64, Docker-Image, systemd-Unit, Installationsanleitung
- [ ] Testlauf parallel zur Legacy-App, dann Umstieg; `CaSSAndRA/` erst danach entfernen

## Offene Entscheidungen
- UI-Sprache / Mehrsprachigkeit (vorerst Englisch wie Legacy)
- Eigenes Tag-Schema für den Neubau (Version kommt noch aus Legacy-Tags `v2.0.0-…`)
- Statistik-Speicherung: JSON oder SQLite (bis Phase 8)
