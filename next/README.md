# CaSSAndRA – Neubau (`next/`)

Go-Backend + Svelte-Frontend, ausgeliefert als **ein einziges Binary** (`bin/cassandra`) mit eingebauter Web-Oberfläche
und eingebautem C++-Planner. Alle Befehle unten laufen **aus diesem Ordner** (`next/`).

Architektur, Regeln und Hintergründe stehen in [`../CLAUDE.md`](../CLAUDE.md), der Stand der Arbeit in
[`ROADMAP.md`](ROADMAP.md).

## Kurz: Was starte ich wofür?

| Ich will … | Befehl | Dann im Browser |
|---|---|---|
| am Code arbeiten (Hot Reload) | `make dev` | http://localhost:5173 |
| die App so starten, wie sie ausgeliefert wird | `make build` und `bin/cassandra --data-dir ../.dev-data` | http://localhost:8050 |
| alle Tests laufen lassen | `make test` (dazu `make test-cpp`, `make test-e2e`) | – |
| ein Binary für den Raspberry Pi | CI-Artefakt `cassandra-linux-arm64` (oder `make build-static` auf Linux) | http://&lt;pi&gt;:8050 |

**Wichtig:** Ohne `--data-dir` benutzt das Binary `~/.cassandra` – das Datenverzeichnis der echten Installation
(Legacy-Daten werden beim ersten Start daraus importiert). Zum Ausprobieren immer ein eigenes Verzeichnis angeben.

## Einmalig einrichten

Voraussetzungen: Go ≥ 1.27, Node ≥ 24, ein C++20-Compiler (clang oder gcc), golangci-lint v2 (nur für `make lint`).

```sh
cd next
make setup        # holt das Planner-Submodule, npm ci, Playwright-Chromium
```

## Entwickeln: `make dev`

Startet zwei Prozesse, beendet beide mit Ctrl+C:

- **Backend** auf `127.0.0.1:8050` (mit Planner, Log-Level debug), Daten in `next/.dev-data/`
- **Vite-Devserver** auf http://localhost:5173 mit Hot Reload; leitet `/api` an das Backend weiter

Im Browser **http://localhost:5173** öffnen (nicht 8050 – dort läuft zwar auch eine Oberfläche, aber die zuletzt
gebaute, ohne Hot Reload). Backend-Änderungen brauchen einen Neustart von `make dev`.

Beim ersten Start ist der **simulierte Roboter** verbunden (Settings → Connection: „sim“). Er steht im Demo-Garten,
solange keine Karte aktiv ist; sonst startet er mit der aktiven Karte in deren Ladestation. Von vorn beginnen:
`make dev` beenden, `rm -rf .dev-data`, neu starten.

## Das Binary bauen und starten

```sh
make build                                    # Frontend bauen, einbetten, bin/cassandra mit Planner
bin/cassandra --data-dir ../.dev-data         # http://localhost:8050
```

Optionen von `bin/cassandra`:

| Flag | Standard | Bedeutung |
|---|---|---|
| `--data-dir` | `~/.cassandra` | Settings, Karten, Aufgaben; Legacy-Import beim ersten Start |
| `--host` | `0.0.0.0` | Adresse, auf der gelauscht wird (`127.0.0.1` = nur dieser Rechner) |
| `--port` | `8050` | Port |
| `--log-level` | `info` | `debug`, `info`, `warn`, `error` |
| `--version` | – | Version ausgeben und beenden |
| `--check-planner` | – | Route durch den Demo-Garten rechnen und beenden (prüft den eingebauten Planner) |

Ohne C++-Compiler: `make build GO_TAGS=` baut ohne Planner (Routen berechnen geht dann nicht, alles andere schon).

Die Verbindung zum Roboter (Simulator, HTTP, MQTT, UART) wird **in der Oberfläche unter Settings** gewählt, nicht per
Flag.

## Mit echten Daten ausprobieren, ohne sie anzufassen

```sh
mkdir -p /tmp/cassandra-test && cp -R ~/.cassandra/map /tmp/cassandra-test/
bin/cassandra --data-dir /tmp/cassandra-test
```

Importiert werden dann Karten und Aufgaben der Legacy-App (ohne `user/` keine Zugangsdaten). Der Roboter bleibt der
Simulator, bis unter Settings etwas anderes eingestellt wird.

## Raspberry Pi

Die CI baut bei jedem Push statische Binaries für `linux/amd64` und `linux/arm64` (Job `release-build`, Artefakte
`cassandra-linux-amd64` / `cassandra-linux-arm64` im GitHub-Actions-Lauf). Auf dem Pi (64-Bit-OS):

```sh
chmod +x cassandra-linux-arm64
./cassandra-linux-arm64 --check-planner      # prüft den Planner
./cassandra-linux-arm64 --data-dir ~/cassandra-next
```

Selbst bauen geht mit `make build-static` auf einem Linux-Rechner derselben Architektur.

## Tests und Prüfungen

| Befehl | Was |
|---|---|
| `make test` | Backend (`go test -race`) + Frontend (vitest), inkl. Architekturtests |
| `make test-cpp` | Backend-Tests mit dem echten C++-Planner |
| `make test-e2e` | baut das Binary und testet im Browser (Playwright, Port 4173, frisches `.e2e-data/`) |
| `make lint` | go vet, golangci-lint (mit/ohne Planner), svelte-check, prettier, eslint |
| `make fmt` | formatieren |
| `make coverage` | Backend-Coverage |
| `make help` | alle Ziele |

Einzeln: `cd backend && go test ./tests/robot/ -run TestStop` · `cd web && npx vitest --run tests/shared/api.test.ts`
· `cd web && npx playwright test tests/e2e/tasks.e2e.ts`.

## Ordner

```
next/
  backend/          Go: ein Ordner pro Feature (robot, maps, tasks, planner …), Tests in backend/tests/
  web/              Svelte + TypeScript: src/features/, src/shared/, src/routes/, Tests in web/tests/
  third_party/      PathPlannerCore (Git-Submodule, der C++-Planner)
  bin/              Build-Ausgabe (nicht eingecheckt)
  .dev-data/        Daten von make dev (nicht eingecheckt)
  .e2e-data/        Daten der E2E-Tests (nicht eingecheckt)
```
