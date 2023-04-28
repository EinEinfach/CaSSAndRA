
# CaSSAndRA

(Cascaded Sunray Server And Rover Application)

CaSSAndRA ist eine Python-Server-Anwedung, die es einem erlaubt den Ardumower (oder Alfred) mit der Sunray Firmware zu steuern. Die Serveranwendung läuft auf einem separatem Rechner und kann über einen der drei Wege mit der Sunray Firmware kommunizieren:
- HTTP (Post requests)
- MQTT
- UART (serieller Port)



## Wichtig (Bitte vor der Installation lesen):
## Installation
Installation für linuxbasierte Betriebssysteme (alle Befehle werden im Terminal ausgeführt):
Als erstes muss die Repository heruntergeladen werden. Oder für die Profis unter euch einfach clonen.
Entpackt die Dateien in den Ordner eurer Wahl (z.B.):

	/home/ardumower/CaSSAndRa
Navigiert in den geclonten/entpackten Ordner:

 	cd /home/ardumower/CaSSAndRa
Installiert die Abhängigkeiten, dazu im Terminal folgendes eingeben:

    pip install -r /home/ardumower/CaSSAndRa/requirements.txt
danach könnt Ihr erst mal Kaffee holen, denn das kann dauern. Bitte achtet drauf, dass die Installation ohne Fehlern abgeschlossen wird (Warnings können ignoriert werden).

Wenn euch das Betriebssystem mit -bash: pip command not found begrüßt, 	müsst Ihr noch pip nachinstallieren: 

    sudo apt install python3-pip

Prüft bitte mit folgendem Befehl den Bibliothekenpfad eurer pip-Installation:

	python3 -m site --user-site
Wechselt bitte in den Bibliothekenpfad und dort in den dash_daq Ordner (z.B.):

	cd ./local/lib/python3.9/site-packages
Sucht den dash_daq Ordner und wechselt dahin:

	cd dash_daq

Kopiert die dash_daq.min.js Datei in den dash_daq Ordner und ersetzt die vorhandene Datei:

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
![alt text](https://github.com/EinEinfach/CaSSAndRA/tree/master/docs/first_start.jpeg?raw=true)
