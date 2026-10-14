# CLAUDE.md

## Projekt

CaSSAndRA steuert Ardumower/Alfred-Mähroboter mit **Sunray-Firmware** über eine Web-Oberfläche
(Kartenerstellung, Bahnplanung, Aufgaben/Zeitplan, Live-Status, Fernsteuerung, MQTT-API für
Home-Automation). Läuft typischerweise auf einem Raspberry Pi im lokalen Netz.

**Wir schreiben das Projekt komplett neu.** Ziele, in dieser Reihenfolge:
1. **Wartbar** – klare Modulgrenzen, keine globalen Zustände, kleine Pakete mit einer Aufgabe.
2. **Testbar** – jede Logik ohne Roboter, Netzwerk oder Browser testbar.
3. **Schnell** – UI reagiert sofort (kein Server-Roundtrip pro Klick), Backend sparsam auf dem Pi.

## Repo-Aufteilung

| Pfad | Status |
|---|---|
| `CaSSAndRA/` | **Legacy** (Python/Dash, v0.302.x). Nur noch Referenz für Verhalten und Protokoll. Nicht erweitern, nicht refactoren. |
| `next/` | **Neubau.** Alle neue Arbeit passiert hier. |

Wenn Verhalten unklar ist: im Legacy-Code nachsehen, wie es dort gelöst ist – aber die
Struktur nicht übernehmen. Relevante Legacy-Stellen:
- Sunray-Protokoll: `CaSSAndRA/src/backend/comm/sunraycommstack.py`, `connections.py`
- Planner-Aufruf: `CaSSAndRA/src/backend/map/path.py` (`calc_cpp`, `shapely_to_cpp_env`)
- MQTT-API: `CaSSAndRA/src/backend/comm/api.py`, `apitopics/`
- Konfigurationsformate: `CaSSAndRA/src/data/user/*.json`

## Stack

- **Backend:** Go (aktuelle stabile Version), ein einziges Binary.
- **Frontend:** Svelte + TypeScript (SvelteKit mit `adapter-static`), Build wird per `go:embed` ins Binary eingebettet.
- **Live-Daten:** WebSocket (Backend → UI: Zustand, Position, Fortschritt). Befehle per REST (JSON).
- **Kartendarstellung:** Canvas-basiert im Browser, Koordinaten in Metern (lokales System des Roboters).
- **Bahnplanung:** C++-Planner aus dem eigenen Repo [CaSSAndRA_PathPlannerCore](https://github.com/EinEinfach/CaSSAndRA_PathPlannerCore), angebunden über **cgo**. Das ist das einzige Stück, das nicht neu geschrieben wird (siehe „Planner-Anbindung“).
- **Persistenz:** Dateien im Datenverzeichnis (Standard `~/.cassandra`), JSON für Config/Karten/Tasks. Kein pickle, keine DataFrames. Zeitreihen ggf. später SQLite.

## Architektur: flach und feature-basiert

Der Code ist **nach Features geschnitten, nicht nach technischen Schichten**. Jedes Feature ist genau
ein Ordner auf oberster Ebene, ohne Unterordner. Darin liegt alles, was das Feature braucht: Typen,
Logik, Persistenz, REST-/WebSocket-Handler. Es gibt kein `internal/`, `pkg/`, `services/`,
`handlers/` oder `models/`.

```
next/
  backend/
    main.go          Nur Flags/Logging/Signale, ruft app.Run auf.
    app/             Verdrahtet alle Features und startet sie – die einzige Stelle, die alle Features kennt. Testbar mit Port 0.
    geo/             Geometrie-Typen (Point, Polygon, LineString) – Shared Kernel, dünn halten
    protocol/        Sunray-Protokoll: AT-Befehle bauen, Antworten parsen, Checksumme, HTTP-Verschlüsselung. Reine Funktionen.
    link/            Verbindung zum Roboter: Interface + http.go, mqtt.go, uart.go, sim.go (Simulator)
    robot/           Robot-Zustand, Statusableitung, Befehle (Mähen, Stop, Dock, Goto, Joystick …)
    maps/            Perimeter, Ausschlüsse, Dockpunkte, Suchdraht; Kartenverwaltung und Upload zum Roboter
    planner/         Planner-Interface + cgo-Anbindung (Build-Tag `cpp`)
    tasks/           Aufgaben (Teilflächen + Parameter), Reihenfolge, Routenberechnung über planner
    schedule/        Zeitplan (Wochentag → Zeitfenster), startet Tasks
    settings/        App-, Rover-, Verbindungs- und Planner-Einstellungen; Import aus Legacy-Daten
    stats/           Statistik und Verlauf (Batterie, Mähzeit, GPS-Qualität)
    mqttapi/         Externe MQTT-API (kompatibel zur Legacy-API, siehe unten)
    server/          HTTP-Handler, WebSocket-Hub, eingebettetes Frontend (`server/dist/`, Build-Ausgabe, gitignored); montiert die Routen der Features
    tests/           Spiegelt die Feature-Ordner, siehe „Testen“
  web/
    src/
      features/      dieselben Features wie im Backend, jeweils ein Ordner (Komponenten, Stores, API-Client)
      shared/        UI-Bausteine, Kartenrenderer (Canvas), WebSocket-Client
      routes/        SvelteKit-Seiten, setzen nur Features zusammen
    tests/           Spiegelt src/: tests/features/<feature>/, tests/shared/, tests/e2e/, dazu architecture.test.ts
  third_party/
    PathPlannerCore/ Git-Submodule des Planner-Repos, auf einen Commit/Tag gepinnt
```

Frontend-Importe laufen über Node-Subpath-Imports aus `package.json` (SvelteKit 3), mit Dateiendung:
`import { fetchHealth } from '#shared/api.ts'`, `'#features/robot/…'`. Ohne Endung findet TypeScript sie nicht.

Die Liste der Features ist der Startpunkt. Neue Features bekommen einen neuen Ordner auf oberster
Ebene, hier eintragen. Wenn die Struktur abweicht, diese Datei aktualisieren.

## Architekturregeln

- **Ein Feature, ein Ordner, keine Unterordner.** Wird ein Feature zu groß, wird es in zwei Features geteilt, nicht verschachtelt.
- **Abhängigkeiten zeigen nur nach unten:** `geo` und `protocol` hängen von nichts ab. `link` nutzt `protocol`. Fachliche Features (`robot`, `maps`, `tasks` …) dürfen sich gegenseitig nutzen, aber ohne Zyklen. `server` und `mqttapi` stehen ganz oben und werden nur von `app` importiert.
- **Jedes Feature hat eine kleine öffentliche API** (Konstruktor + Methoden). Andere Features nutzen nur diese, nie Interna.
- **Kein globaler Zustand.** Abhängigkeiten werden im Konstruktor übergeben (Legacy nutzt Modul-Globals wie `cmdlist.cmd_mow = True` – genau das vermeiden).
- **Interfaces dort, wo sie gebraucht werden:** z. B. definiert `tasks` das `Planner`-Interface, das es braucht; `robot` definiert `Sender` (nur `Send`), obwohl `link.Link` mehr kann.
- **Zeit ist injizierbar:** Features nehmen `Now func() time.Time` in ihrer Config (Default `time.Now`), Tests übergeben `testkit.FakeClock.Now`. Simulationszeit läuft nur über `Sim.Step`.
- **Protokoll ist pur:** `protocol` macht kein I/O. String rein → Struct raus und umgekehrt.
- **Nebenläufigkeit:** ein Goroutine pro Verbindung/Loop, Kommunikation über Channels oder klar gekapselten Zustand mit Mutex. Alle Loops hängen an einem `context.Context` für sauberes Herunterfahren.
- **Fehler** werden zurückgegeben und mit `fmt.Errorf("...: %w", err)` angereichert, nicht geloggt-und-verschluckt.
- **Logging** über `log/slog`, strukturiert.
- **cgo nur in `planner/`**, in einer Datei hinter Build-Tag `cpp`. Alles andere bleibt reines Go und ist ohne C-Toolchain testbar.

## Testen

**Tests liegen nicht neben dem Code, sondern in `tests/`, das die Feature-Struktur 1:1 spiegelt:**

```
backend/tests/
  architecture/      Erzwingt die Regeln dieser Datei (Spiegelung, flache Features, keine Tests in Features, Abhängigkeitsrichtung)
  app/
  protocol/          protocol_test.go, testdata/ (echte AT-Strings, Golden Files)
  link/
  robot/
  maps/
  planner/
  tasks/
  schedule/
  settings/
  stats/
  mqttapi/
  server/
  integration/       Feature-übergreifend: Backend komplett mit sim-Link
  testkit/           Gemeinsame Fakes und Helfer (FakeClock, FakePlanner, Fixtures). Kein Test-Code in den Features selbst.
```

- Gibt es `backend/<feature>/`, gibt es auch `backend/tests/<feature>/`. Dasselbe gilt für `web/src/features/<feature>/` und `web/tests/features/<feature>/` sowie für jede Datei in `web/src/shared/`.
- **Die Regeln sind selbst Tests:** `backend/tests/architecture` und `web/tests/architecture.test.ts` schlagen fehl, wenn die Struktur verletzt wird. Neue Regeln dort ergänzen (`allowedDeps`, `topLevel`), nicht nur hier beschreiben.
- **Folge in Go:** Tests in einem anderen Ordner sind ein eigenes Package und sehen **nur die exportierte API** des Features. Das ist gewollt (Black-Box-Tests gegen die öffentliche Schnittstelle). Wenn etwas nur testbar ist, indem man Interna exportiert, ist das ein Hinweis, das Design zu ändern, nicht die Sichtbarkeit.
- Table-driven Tests sind Standard.
- `tests/protocol`: **Golden-Tests** mit Antwortzeilen in `testdata/` (inkl. alter Firmware-Varianten). Erwartete Werte kommen aus einer unabhängigen Quelle (Firmware-Format, Legacy-Algorithmus), nie aus dem Code unter Test.
- **Fuzz-Tests** für alles, was Daten von außen parst (`FuzzParseReplies`). Gefundene Abstürze bleiben im Korpus `testdata/fuzz/`. Länger laufen lassen: `go test ./tests/protocol -run XXX -fuzz FuzzParseReplies -fuzztime 60s`.
- `link/sim.go`: simulierter Roboter als `Transport`. Er läuft durch denselben `Poller` wie HTTP/UART, d. h. Tests mit dem Simulator prüfen den echten Code-Pfad. Für Fehlerfälle gibt es `SetOffline`, `SetBatteryVoltage`, `TriggerRain`.
- Unit-Tests von `robot` nutzen einen Fake-`Sender` (`tests/robot/helpers_test.go`), der Fehler, eigene Antworten und Blockieren pro Befehl simuliert. Zusammenspiel robot + link + sim gehört nach `tests/integration`.
- Tests mit echten Timern (Poller) mit `-race -count=20` auf Wackeligkeit prüfen, bevor sie committet werden.
- Planner: `testkit.FakePlanner` für alle anderen Tests; echte cgo-Tests in `tests/planner` hinter Build-Tag `cpp`.
- Frontend: Vitest für Logik/Stores in `web/tests/features/…`. Abhängigkeiten wie `fetch` als Parameter übergeben (siehe `#shared/api.ts`), damit sie ohne Mocks auf Modulebene testbar sind.
- E2E: Playwright in `web/tests/e2e/` (`*.e2e.ts`) gegen das echte Binary (`make build`, Port 4173), ab Phase 2 mit sim-Link.
- Bevor eine Aufgabe als erledigt gilt: Tests laufen grün, `go vet` und Linter sauber.

## Befehle

Alle aus `next/`. Einmalig: `make setup` (npm ci + Playwright-Chromium). Go ≥ 1.27, golangci-lint v2, Node ≥ 24.

```
make test         # Backend (go test -race ./tests/...) + Frontend (vitest) – Unit- und Architektur-Tests
make test-e2e     # baut das Binary und führt Playwright dagegen aus
make test-cpp     # Backend inkl. echtem Planner (Build-Tag cpp) – ab Phase 6
make lint         # go vet + golangci-lint + svelte-check + prettier + eslint
make fmt          # Formatieren (golangci-lint fmt, prettier)
make coverage     # Backend-Coverage über alle Features (-coverpkg=./...)
make dev          # Backend :8050 + Vite-Devserver (Proxy /api → Backend)
make build        # Frontend bauen, nach backend/server/dist kopieren, bin/cassandra bauen
```

Einzelnes Feature: `cd backend && go test ./tests/robot/`, einzelner Test: `go test ./tests/robot/ -run TestStop`.
Frontend einzeln: `cd web && npx vitest --run tests/shared/api.test.ts`.
CI: `.github/workflows/next.yml` (Backend, Web, E2E) bei Änderungen unter `next/`.

## Domänenwissen: Sunray-Protokoll

Kommunikationswege zum Roboter: **HTTP** (POST an Roboter-IP), **MQTT**, **UART** (seriell). Alle drei
müssen unterstützt werden; die Kernlogik darf nicht wissen, welcher aktiv ist.

**Aufbau in `link`:** `Link` = `Run(ctx, Handler)` + `Send(ctx, payload) (reply, error)`. HTTP und UART sind
Anfrage/Antwort und implementieren nur `Transport.Exchange(line) → line`; der `Poller` macht daraus einen
`Link` (fragt AT+S jede 1 s, AT+S2 alle 10 s, AT+T alle 60 s, wie Legacy). Bei MQTT schickt eine Bridge
State/Stats/Props als JSON auf `<name>/state|stats|props|online`, Befehle gehen ohne Antwort auf
`<name>/command` – das wird ein eigener `Link`. Hinweis: Die Sunray-Firmware hat zusätzlich ein eigenes,
viel einfacheres MQTT (`/op`, `/cmd` mit `start|stop|dock`), das CaSSAndRA nicht nutzt.

**Befehle wiederholen:** `Link.Send` wiederholt nie. Nur `robot.Stop` versucht es bis zu 3×, weil er
idempotent ist. `Stop` bricht einen laufenden Karten-Upload ab, statt hinter ihm zu warten.

**Referenz ist die Firmware**, nicht der Legacy-Code: `sunray/comm.cpp` in github.com/Ardumower/Sunray
(`processCmd`, `cmdAnswer`, `cmd*`). Implementiert in `backend/protocol/`.

**Nachrichtenformat:** ASCII, `PAYLOAD,0xCS`. CS = Summe der Payload-Bytes modulo 256, die Firmware sendet
zwei Hex-Ziffern klein, Antworten enden mit `\r\n`. Wir senden immer mit Prüfsumme: HTTP prüft sie,
UART/Konsole entfernt sie ungeprüft.

**HTTP-Verschlüsselung:** `AT+V` ist nie verschlüsselt und liefert `V,<fw>,<version>,<encrypt>,<challenge>,…`.
Bei `encrypt=1`: `key = password % challenge` (Firmware wählt die Challenge so, dass key in 1..94 liegt).
Verschlüsselt wird die komplette Zeile inkl. Prüfsumme, nur Zeichen 32..126: `c → c + key`, über 126 hinaus
zurück auf 32 (`- 95`). Antworten kommen unverschlüsselt.

**Wichtige Befehle:**
| Befehl | Zweck |
|---|---|
| `AT+V` | Version/Props, Verbindungsaufbau |
| `AT+S` | Zustand (Batterie, Position x/y, Lösung, Job, Mähpunkt-Index, Sensor, Ziel, Genauigkeit, Satelliten, Strom, map_crc, lateral_error, timetable …) |
| `AT+T` | Statistik (Dauern, Zähler, Temperaturen …) |
| `AT+C,mow,op,speed,fixTimeout,finishAndRestart,progress,skip,...,` | Steuerung; `-1` = unverändert. Stop `AT+C,0,0,-1…`, Dock `AT+C,0,4,…`, Mähen `AT+C,1,1,…`, Goto `AT+C,0,1,…` |
| `AT+M,x,y` | manuelle Bewegung (Joystick) |
| `AT+W,startIdx,x,y,x,y,…` | Wegpunkte übertragen, Pakete à 30 Punkte |
| `AT+N,perim,excl,dock,way,0` | Punktanzahlen der Karte |
| `AT+X,0,n1,n2,…` | Punktanzahl je Ausschlusszone |
| `AT+P,mode,lon,lat` | Positionsmodus (absolut/relativ) |
| `AT+Y` / `AT+Y2` / `AT+Y3` | Reboot / GPS-Reboot / Shutdown |

AT+S hat 19 Felder (ältere Firmware 16 oder 17), AT+T 31 (älter 24 oder 25). Geparst wird ab der Mindestlänge,
fehlende Felder sind 0, zusätzliche Felder neuerer Firmware werden ignoriert. Beim Laden steht der Ladestrom
negativ in `amps` (Firmware schreibt `"-"` davor, daher auch `"--x"` möglich). Über MQTT kommen State/Stats/Props
als JSON auf `<mower_name>/<topic>` (Phase 4).

## Domänenwissen: Bahnplanung

Planner-Eingaben (siehe `calc_cpp`): `Environment` aus Perimeter, Hindernissen (Polygon-Interiors),
Mähflächen (eine oder mehrere) und optionalem virtuellen Draht (Suchdraht); `PathSettings` mit
`offset` (= Schnittbreite), `angle` (rad; zufällig wenn nicht gesetzt), `distanceToBorder`
(= Faktor × Breite), `mowArea`, `mowBorder`/`borderLaps`, `mowExclusionsBorder`/`exclusionsBorderLaps`,
`pattern` (`lines`, `squares`, `rings`), `mowBorderCcw`; Startpunkt = aktuelle Roboterposition.
Ergebnis ist eine Punktfolge (die Route), die per `AT+W` übertragen wird.

## Planner-Anbindung

Quelle: https://github.com/EinEinfach/CaSSAndRA_PathPlannerCore (eigenes Repo, gleicher Autor; Änderungen
dort sind erlaubt und erwünscht, wenn die Anbindung sie braucht).

Aufbau des Planner-Repos (Stand v1.3):
- C++20, CMake; Kern in `src/` + `include/` (`Geometry`, `Environment`, `PathPlanner`, `PathService`),
  Clipper2 ist mit eingebettet. GoogleTest-Tests in `tests/`.
- Öffentlicher Einstieg: `Planner::PathService::computeFullTask(env, settings, startPos)` →
  `PlanningResult { path, slices, debugLines, debugLinesSec }`. Für uns zählt `path`.
- `PathSettings`: `pattern`, `offset`, `angle`, `distanceToBorder`, `mowArea`, `mowBorder`, `mowBorderCcw`,
  `borderLaps`, `mowExclusionsBoder` (sic, Tippfehler im Original), `mowExclusionsBorderCcw`, `exclusionsBorderLaps`.
- `src/python_wrapper.cpp` ist die pybind-Anbindung für das Legacy-Wheel; `GeoJSONReader` + `main.cpp` nur für die Standalone-App.
- `PathPlanner` enthält auch A*-Wegfindung (`findAStarPath`, `isPathClear`) – Kandidat für Goto/Anfahrtswege, statt das in Go nachzubauen.

Vorgehen für die Go-Anbindung:
1. **C-API im Planner-Repo** ergänzen (`include/planner_c.h`, `src/planner_c.cpp`): `extern "C"`, nur flache Typen
   (Punkt-Arrays als `double*` + Länge, Settings als C-Struct, Ergebnis-Puffer + Free-Funktion, Fehler als Rückgabecode
   statt C++-Exceptions über die Grenze). Dazu ein CMake-Target als **statische Library** ohne pybind-Abhängigkeit
   (pybind/Python-Suche nur, wenn das Python-Modul gebaut wird).
2. Planner-Repo als **Git-Submodule** unter `next/third_party/PathPlannerCore` einbinden, auf Tag gepinnt.
3. `backend/planner/cgo.go` (Build-Tag `cpp`) linkt die statische Library (`-lstdc++` bzw. `-lc++`) und übersetzt
   zwischen `geo`-Typen und der C-API. Ohne Tag gibt es nur das Interface; Tests nutzen `testkit.FakePlanner`.
4. Planner läuft in eigener Goroutine, das Ergebnis kommt über einen Channel, die UI bleibt bedienbar. Die C-API fängt
   alle C++-Exceptions ab. Achtung: ein Segfault im C++-Code beendet den ganzen Go-Prozess. Falls das in der Praxis
   vorkommt, Planner stattdessen als separaten Prozess aufrufen (Standalone-Binary mit JSON über stdin/stdout).

## Kompatibilität

- **MQTT-API** (Topics robot, map, maps, tasks, mowParameters, settings) bleibt kompatibel, damit
  bestehende Home-Automation-Integrationen weiter funktionieren. Abweichungen nur bewusst und dokumentiert.
- **Datenverzeichnis:** Beim ersten Start vorhandene Legacy-Daten (`~/.cassandra`: JSON-Configs, Karten, Tasks)
  importieren. Pickle-Messdaten dürfen verworfen werden.

## Konventionen

- Code, Bezeichner und Commit-Messages auf Englisch; Diskussion und diese Datei auf Deutsch.
- Einheiten im Namen, wo nicht offensichtlich (`speedMps`, `angleRad`, `timeoutSec`).
- Sicherheit: Der Roboter ist eine Maschine mit Messer. Befehle, die Bewegung auslösen, nie automatisch
  wiederholen, ohne dass es explizit so entworfen ist; Stop hat immer Vorrang.
