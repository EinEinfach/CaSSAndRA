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
- **Live-Daten:** Server-Sent Events auf `GET /api/events` (Backend → UI: Zustand, Position, Fortschritt), Befehle per REST (JSON). Bewusst kein WebSocket: Daten fließen nur in eine Richtung, SSE braucht keine Go-Bibliothek, der Browser verbindet sich selbst neu, und es ist mit `httptest` testbar. Neue Clients bekommen sofort das letzte Event jedes Typs.
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
    main.go          Nur Flags (--host, --port, --data-dir, --log-level), Logging, Signale; ruft app.Run auf.
    app/             Verdrahtet alle Features und startet sie – die einzige Stelle, die alle Features kennt. Testbar mit Port 0.
    geo/             Geometrie-Typen (Point, Polygon, LineString) – Shared Kernel, dünn halten
    jsonfile/        JSON-Dateien atomar lesen/schreiben (temp + rename, 0600) – Hilfspaket ohne Abhängigkeiten
    protocol/        Sunray-Protokoll: AT-Befehle bauen, Antworten parsen, Checksumme, HTTP-Verschlüsselung. Reine Funktionen.
    link/            Verbindung zum Roboter: Interface + http.go, mqtt.go, uart.go, sim.go (Simulator)
    robot/           Robot-Zustand, Statusableitung, Befehle (Mähen, Stop, Dock, Goto, Joystick …)
    maps/            Perimeter, Ausschlüsse, Dockpfad, Suchdraht; Kartenspeicher (eine Datei je Karte + active.json), Legacy-Import, API inkl. Upload zum Roboter
    planner/         C++-Planner (Mähroute, A*-Weg) über cgo hinter Build-Tag `cpp`; ohne Tag ErrUnavailable
    tasks/           Aufgaben (Teile aus Fläche + Parametern, tasks.json), Legacy-Import, Routenvorschau über planner (Event `plan`), Start
    schedule/        Zeitplan (Wochentag → Zeitfenster), startet Tasks
    settings/        Verbindungs-, Rover-, Batterie-, Planner- und API-Einstellungen (settings.json); Import aus Legacy-Daten; API ohne Passwörter
    stats/           Statistik und Verlauf (Batterie, Mähzeit, GPS-Qualität)
    mqttapi/         Externe MQTT-API (kompatibel zur Legacy-API, siehe unten)
    server/          HTTP-Handler, SSE-Hub, eingebettetes Frontend (`server/dist/`, Build-Ausgabe, gitignored); montiert die Routen der Features (`Options.Routes`)
    tests/           Spiegelt die Feature-Ordner, siehe „Testen“
  web/
    src/
      features/      dieselben Features wie im Backend, jeweils ein Ordner (Komponenten, Stores, API-Client)
      shared/        API-Client, Event-Stream, Kartenrenderer (Canvas: viewport.ts, drawMap.ts, MapCanvas.svelte)
      routes/        SvelteKit-Seiten, setzen nur Features zusammen
    tests/           Spiegelt src/: tests/features/<feature>/, tests/shared/, tests/e2e/, dazu architecture.test.ts
  third_party/
    PathPlannerCore/ Git-Submodule des Planner-Repos, auf einen Commit gepinnt
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
- **Persistenz:** über `jsonfile` (atomar, 0600). Ein Feature besitzt seine Dateien; Stores laden beim Öffnen, validieren beim Schreiben und melden Änderungen per `OnChange`. Ist eine Datei kaputt, startet die App nicht (lieber laut als still überschrieben).
- **Einstellungen zur Laufzeit:** Features bekommen veränderliche Werte über einen Setter (`robot.SetSettings`), nicht durch Neubau. Was in der Run-Schleife eines Links aufgerufen wird (z. B. `OnOnline` → `SendPositionMode`), darf nicht auf `cmdMu` warten.
- **HTTP-API eines Features** liegt im Feature (`robot/api.go`: `Handler()`, JSON-Typen mit camelCase-Tags). `app` montiert sie in `server`. Fehler-Mapping: offline → 503, Timeout → 504, sonstiger Link-Fehler → 502, ungültige Eingabe → 400, Body `{"error": "..."}`. JSON enthält nie `NaN` und nie `null` für Listen.
- **Goroutinen in `app`** laufen an einem eigenen Kontext und werden beim Beenden abgebrochen *und* abgewartet (`defer wg.Wait()` vor `defer cancel()` registrieren, damit `cancel` zuerst läuft). Request-Kontexte hängen über `BaseContext` am App-Kontext, sonst blockieren offene Event-Streams das Herunterfahren.
- **cgo nur in `planner/`**, hinter Build-Tag `cpp` (`cgo.go`, `core.cpp`; der Architekturtest prüft das). Alles andere bleibt reines Go und ist ohne C-Toolchain testbar.

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
- Echte Transporte werden gegen echte Gegenstellen getestet, nicht gegen Mocks: HTTP über `testkit.RobotHTTPServer` (Simulator hinter `httptest`), UART über `net.Pipe` mit einem Fake-Roboter, der Konsolenrauschen einstreut, MQTT gegen `testkit.StartBroker` (eingebetteter mochi-Broker).
- Test-HTTP-Handler, die auf `r.Context().Done()` warten, müssen vorher den Body lesen – sonst bemerkt der Server das Auflegen nicht und `httptest.Server.Close` hängt.
- Unit-Tests von `robot` nutzen einen Fake-`Sender` (`tests/robot/helpers_test.go`), der Fehler, eigene Antworten und Blockieren pro Befehl simuliert. Zusammenspiel robot + link + sim gehört nach `tests/integration`.
- Tests mit echten Timern (Poller) mit `-race -count=20` auf Wackeligkeit prüfen, bevor sie committet werden.
- Planner: `testkit.FakePlanner` für alle anderen Tests; echte cgo-Tests in `tests/planner` hinter Build-Tag `cpp`.
- Frontend: Seiten (`routes/`) bekommen den einen Event-Stream per Context (`#shared/streamContext.ts`, vom Layout bereitgestellt). Ebenso das Roboterbild (`#shared/robotPicture.svelte.ts`): Das Layout folgt dem SSE-Event `settings` (Settings ohne Passwörter, bei jeder Änderung), `MapCanvas` zeichnet das Bild statt des Pfeils. Die Bilder stammen aus der Legacy-App (`web/static/rovers/*.png`, Blickrichtung +x, Kantenlänge = `appearance.robotSizeCm`). Gemeinsame Formular-Bausteine stehen in `app.css` (`.card`, `.field` mit `.hint`, `.switch`). Design ist eigenständig, nicht an die Legacy-App gebunden: neutrale Grautöne in Ebenen (hell: helle Grautöne, dunkel: tiefes Schwarz), Primärfarbe Schwarz bzw. Weiß; Farbe nur mit Bedeutung (Stop rot, Dock blau, Bearbeitung orange, Verbindung `--ok`).
- Frontend: Logik gehört in `.ts`-Dateien (pure Funktionen, Klassen), Komponenten bleiben dünn. Abhängigkeiten werden übergeben statt importiert-und-gemockt: `fetch` als Parameter, `send`/`sender`/`loadMap` als Props bzw. Konstruktor-Argumente, Timer über ein `Scheduler`-Interface.
- Komponententests mit `@testing-library/svelte` in jsdom. Canvas wird über `tests/shared/recordingContext.ts` geprüft (zeichnet jeden Befehl auf), `ResizeObserver` per `vi.stubGlobal`.
- Svelte 5: Ein `$effect`, der State schreibt, den er auch liest, läuft endlos (`effect_update_depth_exceeded`). Gelesenen-und-geschriebenen State in `untrack(...)` lesen.
- Svelte 5: Keine Variable oder Prop `state` in einer Komponente, die `$state(...)` nutzt – Svelte liest das sonst als Store-Abo (`store_invalid_shape`). Prop beim Destrukturieren umbenennen (`state: robot`).
- Dateinamen dürfen sich nicht nur in Groß-/Kleinschreibung unterscheiden (`Joystick.svelte` + `joystick.ts` → gleiche Testdatei auf macOS).
- E2E: Playwright in `web/tests/e2e/` (`*.e2e.ts`) gegen das echte Binary (`make build`, Port 4173, frisches `--data-dir ../.e2e-data`) mit Simulator und Demo-Garten. Die Tests teilen sich den Roboter und laufen nacheinander (`workers: 1`); wer den Roboter verändert, stellt ihn danach wieder her (Verbindung kurz wechseln = frischer Simulator). Neue E2E-Tests mit `npx playwright test --repeat-each=3` auf Wackeligkeit prüfen.
- Testdaten aus echten Installationen nie 1:1 einchecken (Zugangsdaten!): Format nachbauen, Werte erfinden.
- `go test` läuft im Makefile mit `-timeout 120s`, damit ein hängender Test (Deadlock) nicht den ganzen Lauf blockiert.
- Bevor eine Aufgabe als erledigt gilt: Tests laufen grün, `go vet` und Linter sauber.

## Befehle

Alle aus `next/`. Einmalig: `make setup` (Submodule, npm ci, Playwright-Chromium). Go ≥ 1.27, golangci-lint v2, Node ≥ 24, C++20-Compiler (clang/gcc).

```
make test         # Backend (go test -race ./tests/...) + Frontend (vitest) – Unit- und Architektur-Tests
make test-e2e     # baut das Binary und führt Playwright dagegen aus
make test-cpp     # Backend inkl. echtem Planner (Build-Tag cpp)
make lint         # go vet + golangci-lint + svelte-check + prettier + eslint
make fmt          # Formatieren (golangci-lint fmt, prettier)
make coverage     # Backend-Coverage über alle Features (-coverpkg=./...)
make dev          # Backend :8050 mit Simulator + Vite-Devserver (Proxy /api → Backend)
make build        # Frontend bauen, nach backend/server/dist kopieren, bin/cassandra mit Planner bauen (GO_TAGS= ohne)
make build-static # auf Linux: statisches bin/cassandra-linux-<arch> (läuft z. B. auf Raspberry Pi OS)
```

Daten: `bin/cassandra --data-dir <dir>` (Standard `~/.cassandra`). Beim ersten Start (kein `settings.json` bzw. kein
`maps/`) werden Legacy-Daten aus demselben Verzeichnis importiert (`user/*.json`, `map/perimeter.json`, `map/tmp.json`).
Die Verbindung zum Roboter wird in der UI unter Settings gewählt (oder in `settings.json`), nicht per Flag.
`make dev` nutzt `.dev-data/`, E2E ein frisches `.e2e-data/` – nie `~/.cassandra`.

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
`<name>/command` (roh, ohne Prüfsumme, wie Legacy) – eigener `MQTTLink`. Online ist der Roboter dort, wenn der
Broker verbunden ist *und* `<name>/online` nicht `false` meldet; gemeldet wird erst nach bestätigten Abos. Hinweis: Die Sunray-Firmware hat zusätzlich ein eigenes,
viel einfacheres MQTT (`/op`, `/cmd` mit `start|stop|dock`), das CaSSAndRA nicht nutzt.

**Umsetzung:** `link/http.go` (POST, 6 s Timeout, leerer Body = Zeile abgelehnt), `link/uart.go` (`LineTransport`:
überspringt Konsolenausgaben bis zur passenden Antwort, öffnet den Port nach Fehlern neu), `link/mqtt.go`
(paho; Nachrichten laufen über einen Kanal, damit der Handler nur aus `Run` aufgerufen wird). Auswahl über die Einstellungen (`settings.Connection`); `app` startet den passenden Link und tauscht ihn bei Änderungen aus (`app/link.go`: `superviseLink`, `switchSender`).

**Karten-Upload und map_crc:** Nach AT+W/N/X meldet der Roboter in AT+S die `map_crc` = Summe aller Punkte in cm
(`map.cpp`: `Point::setXY`, `Point::crc`). Die Rechnung hängt von Plattform und Version ab: Arduino schneidet jede
Koordinate auf `short` ab (z. B. 40.94 → 4093), aktuelle Linux-Firmware addiert als `float` und schneidet erst die
Punktsumme ab. Sunray 1.0.324 unter Linux rechnet noch wie Arduino (am echten Simulator geprüft). `protocol.MapChecksum`
bildet beide exakt nach (float32), Golden-Werte stammen aus `tests/protocol/testdata/map_crc_reference.c`.
`robot.UploadMap` wartet danach (bis `MapCRCTimeout`) auf eine passende CRC – die einzige Prüfung, die auch über MQTT
greift – und lehnt Uploads ab, solange der Roboter fährt (AT+W mit Index 0 löscht seine Route). Legacy toleriert
stattdessen eine Abweichung < 200. Der Simulator rechnet wie Sunray unter Linux.

**Gefahrene Spur:** `robot` führt sie (`robot/trail.go`: 5 cm Mindestabstand, neue Spur nach Sprung > 5 m, max. 2000 Punkte)
und beginnt sie neu, sobald der Status auf docked/charging wechselt oder über `DELETE /api/robot/trail`. Der Zustand
trägt `trailId`; der Browser holt die Spur nur bei neuer Id (`GET /api/robot/trail`) und verlängert sie sonst selbst.

**Aufgaben (`tasks`):** Eine Aufgabe gehört zu einer Karte und hat Teile (Auswahl-Polygon, leer = ganzer Garten, +
Parameter wie `settings.Planner`; Ausschlussrunden = Randrunden, mindestens 1), wie die Legacy-„task nr“. Gespeichert in
`tasks.json` (Event `tasks`); Aufgaben gelöschter Karten verschwinden mit. Import beim ersten Start aus
`map/tasks.json` + `tasks_parameters.json` (Lasso und „range“ → Polygon, leerer Winkel → 0°, gecachte Routen verworfen,
Zuordnung über den Kartennamen).

**Routenvorschau:** `POST /api/tasks/preview` mit `parts` (im Browser gezeichnet) oder `taskIds` (gespeicherte Aufgaben
in dieser Reihenfolge); jeder Teil startet am Endpunkt des vorherigen (Legacy `calc_task`). Start wie Legacy: angedockt (oder < 1 m von der
Station) am Anfang des Dockpfads, außerhalb des Perimeters an der nächsten Ecke, sonst an der Position. Die Vorschau
liegt nur im Speicher, geht als Event `plan` an alle Browser und verfällt, wenn sich die aktive Karte ändert. Bei
überlappenden Anfragen bleibt die zuletzt gestellte. `POST /api/tasks/start` überträgt Karte + Route (`UploadMap`) und
startet das Mähen (`Mow`), je genau einmal; abgelehnt (409), wenn die Karte sich geändert hat oder der Startpunkt
sich seit der Vorschau um > 1 m verschoben hat (der Roboter führe sonst geradeaus zum Routenanfang, ggf. durch eine
Ausschlusszone), und solange ein Start läuft.

**Goto:** `POST /api/tasks/goto {x, y}`: Ziel muss auf dem Rasen liegen (im Perimeter, in keiner Ausschlusszone), der
Weg kommt aus `planner.Way` (A*, bevorzugt den Suchdraht) vom Startpunkt (wie oben, also im Dock vom Dockpfad aus);
gesendet werden Karte + Weg und `robot.Goto` (Mähmotor aus), je einmal. Legacy schickte nur den Zielpunkt und ließ die
Firmware den Weg suchen. In der UI zwei Schritte: Ziel antippen, dann „Drive there“; beim Wählen zeigt die
Live-Karte die aktive Karte. Fortschritt = `mowPointIndex / Anzahl Wegpunkte` (Live-Seite, mit
„Jump“ = `skip-to-progress` und „Skip point“).

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

Aufbau des Planner-Repos (Stand v1.4.0, Submodule steht auf diesem Tag):
- C++20, CMake; Kern in `src/` + `include/` (`Geometry`, `Environment`, `PathPlanner`, `PathService`),
  Clipper2 ist mit eingebettet. GoogleTest-Tests in `tests/` (`make test` dort).
- **C-API** `include/planner_c.h` / `src/planner_c.cpp`: `planner_compute` (= `PathService::computeFullTask`, Mähroute)
  und `planner_find_path` (A*, `PathPlanner::findPath`, für Goto/Anfahrten), nur flache Typen, keine Exception über
  die Grenze (Status + Meldung), Ergebnis mit `planner_free_path` freigeben. CMake-Target `planner_core` (statisch),
  pybind nur bei `PLANNER_BUILD_PYTHON=ON` (Standard, für das Wheel).
- `PathSettings::mowExclusionsBorder` (früher `mowExclusionsBoder`; das Python-Modul kennt den alten Namen weiter).
- `src/python_wrapper.cpp` ist die pybind-Anbindung für das Legacy-Wheel; `GeoJSONReader` + `main.cpp` nur für die Standalone-App.
- **Achtung:** Ein Tag `v*` dort veröffentlicht per GitHub Action ein Wheel auf PyPI. Tags nur nach Absprache.

Go-Anbindung (`backend/planner/`):
- Submodule `next/third_party/PathPlannerCore`, auf einen Commit gepinnt (`make setup` holt es).
- `planner.go` (reines Go): `Area`, `Settings`, Fehler (`ErrUnavailable`, `ErrInvalid`, `ErrNoPath`, `ErrFailed`),
  `Native` mit `Route` und `Way`. Eine Rechnung zur Zeit (Pi); ein abgelaufener Context kehrt sofort zurück, die
  C++-Rechnung läuft dann im Hintergrund zu Ende (nicht unterbrechbar).
- Hinter Build-Tag `cpp`: `cgo.go` (Übersetzung, Speicher für die C-Seite per `calloc`, da cgo keine Go-Zeiger in
  übergebenem Speicher erlaubt) und `core.cpp`, das die Planner-Quellen per `#include` einbindet – cgo kompiliert sie
  selbst, kein CMake-Schritt, Cross-Compiling wie bei jedem cgo-Paket. `nocpp.go` (`!cpp`) liefert `ErrUnavailable`.
- Features definieren ihr eigenes Interface (`Route`, `Way`); Tests nutzen `testkit.FakePlanner`.
- `Route` schneidet Mähflächen vorher auf den Rasen zu (`clip.cpp`, Clipper2: Perimeter minus Ausschlusszonen, wie
  Legacy mit shapely). Der Planner selbst tut das nicht: Ringe und Randabstand folgen dem Umriss der Mähfläche (Bahnen
  außerhalb des Gartens), und eine Ausschlusszone über dem Umriss liefert bei Ringen eine leere Route.
- `tests/planner/testdata/golden.json` stammt aus dem Python-Modul des Planners (`make_golden.py`) – unabhängiger
  Weg in denselben Kern. Nach einem Planner-Update neu erzeugen, mit `-ffp-contract=off`.
- `core.cpp` schaltet FMA per Pragma ab (cgo verbietet `-ffp-contract=off`): Sonst rechnet clang auf arm64 anders als
  gcc auf x86, und eine Rundung kann die Wahl der nächsten Bahn kippen – andere Route je Plattform.
- `make build` baut mit Planner; `make build-static` (auf Linux) ein statisches Binary, das auf jedem Linux läuft
  (CI-Job `release-build` für amd64 und arm64). Ein Segfault im C++-Code beendet den ganzen Prozess; falls das in der
  Praxis vorkommt, Planner als separaten Prozess aufrufen.

## Kompatibilität

- **MQTT-API** (Topics robot, map, maps, tasks, mowParameters, settings) bleibt kompatibel, damit
  bestehende Home-Automation-Integrationen weiter funktionieren. Abweichungen nur bewusst und dokumentiert.
- **Datenverzeichnis:** Beim ersten Start vorhandene Legacy-Daten (`~/.cassandra`: JSON-Configs, Karten, Tasks)
  importieren. Pickle-Messdaten dürfen verworfen werden.

## Konventionen

- Code, Bezeichner und Commit-Messages auf Englisch; Diskussion und diese Datei auf Deutsch.
- UI-Texte vorerst Englisch wie in der Legacy-App. Mehrsprachigkeit ist offen (siehe ROADMAP).
- Einheiten im Namen, wo nicht offensichtlich (`speedMps`, `angleRad`, `timeoutSec`).
- Sicherheit: Der Roboter ist eine Maschine mit Messer. Befehle, die Bewegung auslösen, nie automatisch
  wiederholen, ohne dass es explizit so entworfen ist; Stop hat immer Vorrang.
