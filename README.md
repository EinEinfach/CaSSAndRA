
# CaSSAndRA

(Cascaded Sunray Server And Rover Application)

CaSSAndRA ist eine Python-Server-Anwedung, die es einem erlaubt den Ardumower (oder Alfred) mit der Sunray Firmware zu steuern. Die Serveranwendung läuft auf einem separatem Rechner und kann über einen der drei Wege mit der Sunray Firmware kommunizieren:
- HTTP (Post requests)
- MQTT
- UART (serieller Port)



## Wichtig (Bitte vor der Installation lesen):
Installation und Nutzung der App erfolgt auf eigene Gefahr. Ich übernehme keinerlei Haftung für die entstandenen Schäden durch die Nutzung der App. Es handelt sich hierbei um meinen Hobby-Projekt, der bei euch nicht funktionieren muss. Eurer Roboter muss mit einem Not-Aus Schalter ausgerüstet sein. Bei der Bedienung des Roboters aus der App bitte haltet immer Sichtkontakt zu dem Roboter und im Falle des unerewarteten Verhaltens schaltet diesen sofort über Not-Aus Schalter aus. Wenn Ihr damit einverstanden seid, dann fährt mit der Installation fort.
## Installation
Installation für linuxbasierte Betriebssysteme (alle Befehle werden im Terminal ausgeführt):
Als erstes muss die Repository heruntergeladen werden. Oder für die Profis unter euch einfach clonen.
Entpackt die Dateien in den Ordner eurer Wahl (z.B.):

	/home/ardumower/CaSSAndRa
Navigiert in den geclonten/entpackten Ordner:

 	cd /home/ardumower/CaSSAndRa
Installiert die Abhängigkeiten, dazu im Terminal folgendes eingeben:

    pip install -r /home/ardumower/CaSSAndRa/requirements.txt
danach könnt Ihr erst mal Kaffee holen gehen, denn das kann dauern. Bitte achtet drauf, dass die Installation ohne Fehlern abgeschlossen wird (Warnings können ignoriert werden).

Wenn euch das Betriebssystem mit -bash: pip command not found begrüßt, 	müsst Ihr noch pip nachinstallieren: 

    sudo apt install python3-pip

Prüft bitte mit folgendem Befehl den Bibliothekenpfad eurer pip-Installation:

	python3 -m site --user-site
Wechselt bitte in den Bibliothekenpfad(z.B.):

	cd ./local/lib/python3.9/site-packages
Sucht den dash_daq Ordner und wechselt dahin:

	cd dash_daq

Kopiert die dash_daq.min.js Datei aus der von euch geclonten Repository in den dash_daq Binliotheken-Ordner und ersetzt die vorhandene Datei:

	cp /home/ardumower/CaSSAndRA/bugfix_dash_daq_min/dash_daq.min.js dash_daq.min.js
    
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
   
## Authors

- [@EinEinfach](https://www.github.com/EinEinfach)
