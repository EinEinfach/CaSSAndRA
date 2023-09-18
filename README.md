
# CaSSAndRA

(Cascaded Sunray Server And Rover Application)

CaSSAndRA ist eine Python-Server-Anwedung, die es einem erlaubt den Ardumower (oder Alfred) mit der Sunray Firmware zu steuern. Die Serveranwendung läuft auf einem separatem Rechner und kann über einen der drei Wege mit der Sunray Firmware kommunizieren:
- HTTP (Post requests)
- MQTT
- UART (serieller Port)

[![introduction](https://img.youtube.com/vi/ZS4DnEkz1dI/0.jpg)](https://www.youtube.com/watch?v=ZS4DnEkz1dI)

## Wichtig (Bitte vor der Installation lesen):
Installation und Nutzung der App erfolgt auf eigene Gefahr. Ich übernehme keinerlei Haftung für die entstandenen Schäden durch die Nutzung der App. Es handelt sich hierbei um meinen Hobby-Projekt, der bei euch nicht funktionieren muss. Eurer Roboter muss mit einem Not-Aus Schalter ausgerüstet sein. Bei der Bedienung des Roboters aus der App bitte haltet immer Sichtkontakt zu dem Roboter und im Falle des unerewarteten Verhaltens schaltet diesen sofort über Not-Aus Schalter aus. Wenn Ihr damit einverstanden seid, dann fährt mit der Installation fort.
## Installation
Installation für linuxbasierte Betriebssysteme (alle Befehle werden im Terminal ausgeführt):
Als erstes muss die Repository heruntergeladen werden. Oder für die Profis unter euch einfach clonen (Achtung! In diesem Beispiel ist ardumower der Username unter dem alles installiert wird. Ersetzt ardumower durch euren Username unter dem das System läuft).

Entpackt die Dateien in den Ordner eurer Wahl (z.B.):

	/home/ardumower/CaSSAndRA
Navigiert in den geclonten/entpackten Ordner:

 	cd /home/ardumower/CaSSAndRA
Installiert die Abhängigkeiten, dazu im Terminal folgendes eingeben:

    pip install -r /home/ardumower/CaSSAndRA/requirements.txt
danach könnt Ihr erst mal Kaffee holen gehen, denn das kann dauern. Bitte achtet drauf, dass die Installation ohne Fehlern abgeschlossen wird (Warnings können ignoriert werden).

Wenn euch das Betriebssystem mit -bash: pip command not found begrüßt, 	müsst Ihr noch pip nachinstallieren: 

    sudo apt install python3-pip

Prüft bitte mit folgendem Befehl den Bibliothekenpfad eurer pip-Installation:

	python3 -m site --user-site
Wechselt bitte in den Bibliothekenpfad(z.B.). Achtung beim 64bit System kann der Ordner lib64 heißen:

	cd ./local/lib/python3.9/site-packages
Sucht den dash_daq Ordner und wechselt dahin:

	cd dash_daq

Kopiert die dash_daq.min.js Datei aus der von euch geclonten Repository in den dash_daq Bibliotheken-Ordner und ersetzt die vorhandene Datei:

	cp /home/ardumower/CaSSAndRA/bugfix_dash_daq_min/dash_daq.min.js dash_daq.min.js

## Probleme bei der Installation:

Es hat sich herausgestellt, dass besonders Raspberry Pi OS 32bit (bullseye) bei der Installation der Pandas Bibliothek Probleme bereiten kann. Deutlich reibungsloser funktioniert es mit der 64bit Version. Solltet Ihr Probleme bei der Installation auf der Raspberry Pi OS haben, prüft als erstes welche Version von Raspberry Pi OS auf eurem Einplatinencomputer läuft:  

	uname -r

Kommt als Antwort armv7l, dann habt Ihr 32bit Version. Kommt als Antwort aarch64, dann habt Ihr 64bit Version und die Ursache für das Problem liegt woanders.

Für die 32bit Version von bullseye müssen vorher auf dem Raspberry Pi noch folgendes nachinstalliert werden:
		
		sudo apt install libatlas-base-dev libgeos-dev
    
## CaSSAndRA starten
CaSSAndRA das erste mal starten (alle Befehle, bis auf den letzten Aufruf (dieser erfolgt im Browser) werden im Terminal ausgeführt):

Wechselt in den Ordner, wo eure app.py Datei liegt. Habt Ihr nach der Installation den Ordner nicht verschoben dann ist in den Ordner wie folgt zu wechseln:

	cd /home/ardumower/CaSSAndRA/CaSSAndRA
Startet die App mit:

	python3 app.py
Der erfolgreiche Start wird mit ein paar Warnings und INFO Dash is running on xxx:8050 quitiert:

	2023-04-28 08:38:24 INFO Dash is running on http://0.0.0.0:8050/
 	* Serving Flask app 'app'
 	* Debug mode: off
	2023-04-28 08:38:24 INFO Backend: Try initial HTTP request	
Herzlichen Glückwunsch die App ist erfolgreich gestartet und man kann die App im Browser eurer Wahl aufrufen: 

	http://IP-des-Rechners:8050
    
Die App sollte euch jetzt mit 3 roten Ampeln begrüßen:

![first start](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/first_start.jpeg)

Um den Server zu stoppen drück im Terminal Strg+C


### CaSSAndRA Start Options

You can see all the options available when starting CaSSAndRA by executing:

```
python app.py --help
Usage: app.py [OPTIONS]

  Start the CaSSAndRA Server

  Only some Dash server options are handled as command-line options. All other
  options should use environment variables. Find supported environment
  variables here: https://dash.plotly.com/reference#app.run

Options:
  -h, --host TEXT                 [default: 0.0.0.0]
  -p, --port INTEGER              [default: 8050]
  --proxy TEXT                    format={{input}}::{{output}} example=http://
                                  0.0.0.0:8050::https://my.domain.com
  --data_path TEXT                [default: /Users/<username>/.cassandra]
  --debug                         Enables debug mode for dash application
  --app_log_level [DEBUG|INFO|WARN|ERROR|CRITICAL]
                                  [default: DEBUG]
  --app_log_file_level [DEBUG|INFO|WARN|ERROR|CRITICAL]
                                  [default: INFO]
  --server_log_level [DEBUG|INFO|WARN|ERROR|CRITICAL]
                                  [default: ERROR]
  --pil_log_level [DEBUG|INFO|WARN|ERROR|CRITICAL]
                                  [default: WARN]
  --init                          Accepts defaults when initializing app for
                                  the first time
  --help                          Show this message and exit.

```

The `data_path` option is important to review. We are now storing your data and configuration in your user folder `~/.cassandra`. This will persist this data separate from the application, so that you can update the app without losing data.

### Advanced CaSSAndRA Start Examples

Custom port
`python app.py --port=8060`

Using custom data location:
`python app.py --data_path=/Users/myusername/my_app_data/cassandra`

Run two instances of CaSSAndRA:

- Terminal 1: `python app.py` (data in ~/.cassandra)
- Terminal 2: `python app.py --data_path=/Users/myusername/.cassandra2` (data in ~/.cassandra2)

## CaSSAndRA als daemon Service einrichten
Um CaSSAndRA bei jedem Systemstart automatisch ausführen. Kann die Ausführung der Anwendung über systemd realisiert werden. Checkt, ob auf eurem System systemd vorhanden ist:

	systemd --version

Sollte eine Meldung kommen, dass systemd nicht gefunden wurde, dann muss dieser nachinstalliert werden, oder wird dieser von eurem Betriebssystem nichzt unterstützt. Dann bitte an dieser Stelle abbrechen.

Als nächstes legen wir eine neue service Datei an:

	sudo nano /etc/systemd/system/cassandra.service

Die geöfnete Datei füllt Ihr mit folgenden Iformationen:

	[Unit]
	Description=CaSSAndRA
	After=multi-user.target

	[Service]
	#Euer Benutzername
	User=ardumower 
	Type=simple
	Restart=always
	#ExecStart: ggf. Pfad zu eurer app.py anpassen 
	ExecStart=python3 /home/ardumower/CaSSAndRA/CaSSAndRA/app.py
	[Install]
	WantedBy=multi-user.target

Datei speichern und schliessen.

Als nächstes muss daemon neuegeladen werden:

	sudo systemctl daemon-reload
Aktiviert die Ausführung bei jedem Start:

	sudo systemctl enable cassandra.service
Und zum Schluss startet den Service:

	sudo systemctl start cassandra
Prüft den Status:

	sudo systemctl status cassandra
Als Ausgabe kommt(wichtig ist das Wort active(running)):

	cassandra.service - CaSSAndRA service
     Loaded: loaded (/etc/systemd/system/cassandra.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2023-04-27 07:48:22 CEST; 1 day 5h ago

## CaSSAndRA im Docker Container einrichten

Change to the project directory. Example: `cd /Users/<username>/projects/CaSSAndRA`

Build the docker image
```
docker build . -t cassandra
```

### Simple docker example
This example is fine to use with MacOS, where docker automatically handles user permissions.

```
docker run -it \
	-v /Users/<myusername>/.cassandra:/home/cassandra/.cassandra \
	cassandra
```

### Advanced docker example. 
This example shows how you can:
* use a different port (`8080`) on your host system and map that to the default cassandra port of `8050`.
* pass in an environment variable `TZ` for the timezone (see [options](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones))
* pass in Host user and group ids
  * The dockerfile creates a `cassandra` user for everyone
  * This means the data_path in the container will be `/home/cassandra/.cassandra`
  * The entrypoint script will then update the `cassandra` user within the container to use the same user and group ids as the host system
```
docker run -it \
	-p 8080:8050 \
	-v /path/to/my/data:/home/cassandra/.cassandra \
	-e TZ=Europe/Berlin \
	-e HOST_UID=$(id -u) \
	-e HOST_GID=$(id -g) \
	cassandra
```


## Bedienung
### Einrichten der Kommunikation
In der App klickt auf "Settings". Auf der Seite wählt "Communication". Sucht euch eine der Möglichkeiten aus, trägt die Daten ein (bitte haltet die Syntax, was CaSSAndRA euch vorschlägt,bei) und anschliessend mit "save and reboot" werden die Einstellungen übernommen und der Server neuegestartet:

![connection](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/connection.jpeg)

Wenn Ihr zurück auf die Startseite wechselt (z.B. durch click in der Navbar auf CaSSAndRA) und die Verbindung hat geklappt, sollten einige Ampeln nicht mehr auf rot sein.

### Einrichten Map and position
Unter Settings "Map and position" wählen. Hier bitte eure Positionsberechnung unbedingt anpassen (absolute oder relative). Die restliche Einstellungen sind selbserklärend. Einige Einstellungen werden akutell bei der Berechnung der Mähwege nicht berücksichtigt. Vor dem schliessen mit "save and reboot" die Änderungen spechern und den Server neuestarten

### Einrichten der App
Unter Settings "App" wählen. Hier gibt es die Möglichkeiten einige Anzeigen in der App eurer Konfiguration anzupassen.

1. Maximale Haltedauer eurer Messdaten ein. Abhängig von euren zur Verfügung stehenden Ressourcen (Der notwendiger Speicherplatz muss noch ermittelt werden, sollte um die 100MB bis 200MB pro Monat betragen)

2. Die Zeit "ab Verbindung verloren bis Status wechselt zu offline". Läuft die Verbindung über MQTT oder HTTP und Ihr habt keine flächendeckende WiFi Abdeckung im Garten, wählt die Zeit entsprechend hoch

3. Mindeststromstärke, ab der die Anzeige vom "docked" zu "charging" wechseln soll (Achtung: es muss ein negativer Wert sein)

4. SoC Anzeige. Umrechnung Spannung zu Ladezustand (einfache lineare Interpolation). Als Voltage min (0%) wird die Abschaltspannung aus der config.h eurer sunray FW +0,5V empfohlen. Als Voltage max (100%) wird die Ladeschlussspannung aus der config.h eurer sunray FW -0,5V empfohlen. Die SoC Anzeige hat keinerlei steuerende Funktion und dient lediglich einer Übersicht auf der Startseite

### Erstellen einer Karte
Eine neue Karte oder bereits vorhandene Karte kann im Bereich Mapping erstellt/geändert werden. 

In der App klickt auf "Mapping". Um eine vorhandene Karte zu ändern, wählt im Bereich "saved perimeters" die gewünschte Karte. Nun kann mit der Bearbeitung gestartet werden. Eine zusätzliche Sicherung der vorhandenen Karte vor der Bearbeitung ist nicht notwendig. Nach dem Fertigstellen der Karte wird man aufgefordert die bearbeitete Karte in einem separaten Slot zu speichern. Um eine neue Karte zu erstellen klickt auf das Dateisymbol mit dem Plus im Berech "saved perimeters". 

![create_new_perimeter](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/create_new_perimeter.jpeg) 

Positioniert den Roboter an der Stelle, wo ein neuer Punkt aufgezeichnet soll und drückt auf "add new point" zum hinzufügen einer neuen Koordinate oder "remove last point" zum Löschen der letztgesetzten Koordinate.

![add_remove_point](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/add_remove_point.jpeg) 

Ist die Figur fertig kann diese der Fläche hinzugefügt werden (Perimeter), oder aus der Fläche entfernt werden (Exclusion). Hierzu klickt auf die entsprechende Buttons.

![add_remove_figure](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/add_remove_figure.jpeg) 

Um eine Figur zu erstellen können bereits bekannte Werkzeuge Box-Select oder Lasso-Select genutzt werden. So funiktioniert z.B. auch das Löschen einer Exclusion umkreist die Exclusion mit Lasso-Select und wählt zur Fläche hinzufügen. Die neue Figur wird dem Perimeter hinzugefügt und überklebt sozusagen die vorhandene Exclusion. 

Um einen Dockpfad aufzuzeichnen selektiert hierzu das Symbol mit dem Haus. Danach kann mit den Buttons "add new point" und "remove last point" der neue Dockpfad aufgezeichnet werden. Wenn ein neuer Dockpfad aufgenommen wurde oder ein vohandener überarbeitet wurde merkt das CaSSAndRA und beim Speichern des neuen Perimeters verschiebt CaSSAndRA den letzten Dockpoint automatisch um 10cm in die Dockrichtung um das sichere Andocken zu gewährleisten. 

Wenn das neue Perimeter aufgenommen wurde kann das mit entsprechednen Button bestätigt werden und CaSSAndRA fordert euch auf einen neuen Namen für die erstellte Karte zu wählen.

![save_new_perimeter](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/save_new_perimeter.jpeg) 

### Importieren einer Karte
Es gibt die Möglichkeit eine Karte, die in der Sunray App ersstellt wurde zu importtieren. 

Im Bereich "Upload sunray file" klickt auf den Button mit "txt-Datei-Icon". 

Wählt eure Sunray-Export Datei. 

Im Dropdownmenü könnt Ihr jetzt die gewünschte Karte auswählen. 

Ein Vorschau der Karte wird in Rot angezeigt mit dem Hinweis "From upload (please save first)".

![upload](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/upload.jpeg) 

Um die gewünschte Karte zu speichern klickt auf die Wolke mit Plus. 

Im poup-Menü wählt einen eineindeutigen Namen und klickt OK. 

Die Karte wird gespeichert und kann im Berech "Saved perimeters" im Dropdownmenü ausgewählt werden. 

Mit der Wolke mit dem ausgehenden Pfeil kann die Karte aktiv geschaltet werden. 

Wechselt auf die Startseite. Die neue Karte wird in der Übersicht angezeigt und kann verwendet werden.

## Starten einer Aufgabe

Auf der Übersichtsseite (zu erreichen über Betätigen CaSSAndRA Schriftzug im oberen Bildschirmberech) kann dem Roboter eine Aufgabe zugewiesen werden.

![using_app_overview](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/using_app_overview.jpeg) 

### Zur Ladestation zurückkehren
Klickt auf das Häuschen-Symbol und anschliessend auf Play -> Der Mäher kehrt zur Ladestation zurück

### Mähe die gesamte Fläche
Klickt auf das Karten-Symbol (rechts neben dem Häuschen-Symbol). CaSSAndRA berechnet die Mähwege nach euren Einstellungen. Je nach Leistung eures Rechners bzw. der Größe der Karte kann die Berechnung etwas dauern. Die berechneten Wege erscheinen grün auf der Karte. Anschliessend klickt auf Play -> der Mäher fängt an die gesamte Fläche zu mähen

![using_app_mow](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/using_app_mow.jpeg) 

### Mähe ausgewählte FLäche
Klickt auf das Karten-Symbol mit einer Pinnadel (rechts neben dem Karten-Symbol). Wählt im oberen Kartenbereich Box Select oder Lasso Select Werkzeug. Markiert anschliessend auf der Karte die gewünschte Fläche. Je nach Leistung eures Rechners bzw. der Größe der Karte kann die Berechnung etwas dauern. Die berechneten Wege erscheinen grün auf der Karte. Anschliessend klickt auf Play -> der Mäher fängt an die ausgewählte Fläche zu mähen

![using_app_mow_zone](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/using_app_mow_zone.jpeg) 

### Mäher zum beliebigen Punkt auf der Karte fahren lassen
Klickt auf das Positions-Symbol (rechts neben dem Karten-Symbol mit einer Pinnadel). Klickt auf der Karte auf die gewünschte Position. Anschliessend klickt auf Play -> der Mäher fährt zu der gewünschten Position auf der Karte

![using_app_goto](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/using_app_goto.jpeg) 

Aktuelle Einschränkungen: Befindet sich die Ladestation außerhalb des Perimeters und der Mäher soll aus der Ladestation zum gewünschten Punkt fahren, wird die Aufgabe mit einem Fehler abgebrochen

### Temporäre Mäheinstellungen
Klickt auf das Zahnradsysmbol. Es können diverse Mäheinstellungen vorgenommen werden. Diese Einstellungen werden nicht gespeichert und wirken sich nur temporär aus. Wird der Server neuegestartet so werden die Werte aus dem Settingsbereich übernommen

### Auswahl abbrechen
Klickt auf das Symbol mit dem X (rechts neben der Zahnradsymbol) so wird die ausgewählte, nicht gestartete Aufgabe abgebrochen

## Taksplanner
Klickt auf Burgermenü und wählt Taskplanner. 

### Erstellen einer Aufgabe
Sollte bereits eine Aufgabe geladen sein, dann klickt auf das Blattpapier-Button mit dem Plus Zeichen im "saved tasks" Bereich. Benutzt das Zahnrad um die Mäheinstellungen für die geplannte Aufgabe anzupassen. Klickt anschliessend auf den Button Karte (links neben dem Zahnradsymbol) für die Aufgabe auf der ganzen Karte oder selektiert mit Lasso-Werkzeug oder Boxselect-Werkzeug den gewünschten Bereich auf der Karte. Ein Vorschau der Aufgabe erscheint in rot. Um die Aufgabe zu speichern klickt im Bereich "saved tasks" auf die Wolke mit dem Plus Zeichen. Gibt der Aufgabe einen eindeutigen Namen. Jetzt kann die Aufgabe im Dropdown Menü ausgewählt werden.

![create_task](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/create_task.jpeg) 

### Aufgabe erweitern
Soll eine bestehende Aufgabe erweitert werden. Wählt im Dropdownmenü die zu ändernde Aufgabe. Diese erscheint grün auf der Karte. Erzeugt zusätzliche Aufgabe wie unter "Erstellen einer Aufgabe" beschrieben eine zusätzliche Aufgabe. Diese erscheint rot auf der Karte. Speichert die Aufgabe unter einem neune Namen in dem Ihr auf die Wolke mit dem Plus Zeichen drückt.

![extend_task](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/extend_task.jpeg) 

### Aufgabe starten
Wählt im Dropdown Menü die gewünschte Aufgabe. Klickt auf die Wolke mit dem ausgehenden Pfeil im "saved tasks" Bereich

### Aufgabe löschen
Wählt im Dropdown Menü zu löschende Aufgabe. Klickt auf die Wolke mit Minus Zeichen im "saved tasks" Bereich

### Allgemeine Hinweise zum Taskplanner
Die Aufgaben sind aktuell geladednen Karte zugeordnet, sollte diese Umgeschaltet werden, stehe die Aufgaben erst dann zur Verfügung wenn die Karte wieder geladen ist.

Wird eine Karte gelöscht, so werden ohne Vorwarnung auch alle Aufgaben gelöscht, die mit dieser Karte erstellt wurden

Der Taskplanner rechnen die Mähwege immer neue nach dem die Aufgabe gestartet wurde. Es werden keine gespeicherten Wege geladen. Je nach Umfang der Aufgabe und die Leistung eures Rechners kann das einige Zeit in Anspruch nehmen

## Update

### New Approach
After you data has been moved to an external data folder, like `~/.cassandra`, you no longer need to copy your data folder when updating. 

```
ctrl-c (Stop the server)
git pull
python app.py
```

If your data folder is still in /src/data, then do the following:

### Old Approach

Die App wird von mir in kleinen Schritten verbessert bzw. die gemeldeten Probleme behoben. Um die Änderungen auch bei euch produktiv zu schalten, geht beim Update wie folgt vor. 
1. Sichert euren /src/data Ordner
2. Clont erneuet die Repository und ersetzt alle Dateien und Ordner in eurem Produktivverzeichnis durch die neuen heruntergeladenen Dateien.
3. Ersetzt den herunntergeladenen /src/data Ordner durch den im Schritt 1 von euch gesichrten Ordner.
4. App kann wie gwohnt gestartet werden
## Authors

- [@EinEinfach](https://www.github.com/EinEinfach)
