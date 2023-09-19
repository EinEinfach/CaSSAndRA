
# CaSSAndRA

(Cascaded Sunray Server And Rover Application)

CaSSAndRA is a Python server application that allows you to control the Ardumower (or Alfred) with the Sunray firmware. The server application runs on a separate computer and can communicate with the Sunray firmware in one of three ways:
- HTTP (Post requests)
- MQTT
- UART (serial port)

[![introduction](https://img.youtube.com/vi/ZS4DnEkz1dI/0.jpg)](https://www.youtube.com/watch?v=ZS4DnEkz1dI)

## Important (Please read before installing):
Installation and use of the app is at your own risk. I assume no liability for any damage caused by using the app. This is my hobby project, which doesn't have to work for you. Your robot must be equipped with an emergency stop switch. When operating the robot from the app, please always keep visual contact with the robot and in the event of unexpected behavior switch it off immediately using the emergency stop switch. If you agree, then proceed with the installation.

## Installation
Installation for Linux-based operating systems (all commands are run in the terminal):
First the repository has to be cloned. (Warning! In this example, ardumower is the username under which everything is installed. Replace ardumower with your username under which the system is running).

	git clone https://github.com/EinEinfach/CaSSAndRA.git

Navigate to the cloned folder:

 	cd /home/ardumower/CaSSAndRA
Install the dependencies by entering the following in the terminal:

    pip3 install -r /home/ardumower/CaSSAndRA/requirements.txt
after that you can go get some coffee first, because that can take a while. Please ensure that the installation completes without errors (warnings can be ignored).

If the operating system greets you with -bash: pip command not found, you still have to install pip:

    sudo apt install python3-pip
Please check the library path of your pip installation with the following command:

	python3 -m site --user-site
Please switch to the library path (e.g.). Attention with the 64bit system the folder lib64 can be called:

	cd ./local/lib/python3.9/site-packages
Locate the dash_daq folder and go to it:

	cd dash_daq

Copy the dash_daq.min.js file from the repository you cloned into the dash_daq libraries folder and replace the existing file:

	cp /home/ardumower/CaSSAndRA/bugfix_dash_daq_min/dash_daq.min.js dash_daq.min.js

## Installation issues:

It turned out that Raspberry Pi OS 32bit (bullseye) in particular can cause problems when installing the Pandas library. It works much more smoothly with the 64-bit version. If you have problems with the installation on the Raspberry Pi OS, first check which version of Raspberry Pi OS is running on your single-board computer:

	uname -r

If the answer is armv7l, then you have the 32-bit version. If the answer is aarch64, then you have a 64-bit version and the cause of the problem lies elsewhere.

For the 32-bit Raspberry OS version of bullseye, the following must be additionaly installed:

	sudo apt install libatlas-base-dev libgeos-dev
    
## CaSSAndRA Start
Start CaSSAndRA for the first time (all commands except the last call (this is done in the browser) are executed in the terminal):

Go to the folder where your app.py file is located. If you haven't moved the folder after installation, then change to the folder as follows:

	cd /home/ardumower/CaSSAndRA/CaSSAndRA
Start app with:

	./app.py
At first time you will get follow message:

	You are starting CaSSAndRA without an existing external data directory

--------------------------------------------------------------------------------
    CaSSAndRA stores your data (settings, maps, tasks, logs, etc) separate from the app
    directory. This allows us to update the app without losing any data.

    Configured data_path: /home/lex/.cassandra (missing)

    If you continue, CaSSAndRA will:
     - Create /home/lex/.cassandra
     - Sync missing files from /src/data to /home/lex/.cassandra

    Each time you run CaSSAndRA, only missing files are copied and existing files aren't
    overwritten, so no data will be lost.

    If this is the first time you are seeing this message, you can also:
     - Review the readme at https://github.com/EinEinfach/CaSSAndRA#cassandra-starten
     - enter python app.py --help on the command line
--------------------------------------------------------------------------------
If you agree with creating a data path on suggested location just confirm start by pressing Y

The successful start is acknowledged with a few warnings and INFO Dash is running on xxx:8050:

	2023-04-28 08:38:24 INFO Dash is running on http://0.0.0.0:8050/
 	* Serving Flask app 'app'
 	* Debug mode: off
	2023-04-28 08:38:24 INFO Backend: Try initial HTTP request	
Congratulations, the app has started successfully and you can access the app in the browser of your choice: 

	http://IP-des-Rechners:8050
    
The app should now greet you with 3 red lights:

![first start](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/first_start.jpeg)

To stop cassandra press Strg+C
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

## CaSSAndRA as daemon service
To allow CaSSAndRA start each time on system boot you can create a deamon service. First you have to check is daemon service (systemd) is available on your OS:

	systemd --version

If you get a message that systemd was not found, then it needs to be installed or it is not supported by your operating system. Then please cancel at this point.

In next step we create a service file:

	sudo nano /etc/systemd/system/cassandra.service

Copy and paste the follow content in new file:

	[Unit]
	Description=CaSSAndRA
	After=multi-user.target

	[Service]
	#your username!
	User=ardumower 
	Type=simple
	Restart=always
	#ExecStart: your app.py directory!  
	ExecStart=python3 /home/ardumower/CaSSAndRA/CaSSAndRA/app.py
	[Install]
	WantedBy=multi-user.target

Save new file: Strg+o confirm with return and exit: Strg+x 

Reload systemd:

	sudo systemctl daemon-reload
Activate cassandra.service:

	sudo systemctl enable cassandra.service
Start cassandra.service:

	sudo systemctl start cassandra
Check current status:

	sudo systemctl status cassandra
Terminal output(important is state of 'Active' it should be active (running)):

	cassandra.service - CaSSAndRA service
     Loaded: loaded (/etc/systemd/system/cassandra.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2023-04-27 07:48:22 CEST; 1 day 5h ago

## Create docker container for CaSSAndRA

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


## Settings
### Establishing communication to the rover
Go to the "Settings" page or if you on mobile device click on burger menu and then "Settings". Go to "Connection" and choose one of possiblities. Input your specific data (please keep syntax suggestion alos for your data). At the end click on "save and reboot" and let cassandra restart backendserver:

![connection](https://raw.githubusercontent.com/EinEinfach/CaSSAndRA/master/docs/connection.jpeg)

If you have returned to the homepage (e.g. by clicking on CaSSAndRA in the navbar) and the connection worked, some traffic lights should no longer be red.

### Coverage path planner
Select "Coverage path planner" on "Settings" page. Here you can set default planner settings which are used after server restart. 

Pattern: Selection of [lines, squares, rings]

Mow width: positive value [0.0 - 1.0]

Mow angle: positive value [0 - 359]

Distance to border: positive value [0 - 5]. Defines distance to border for area to mow calculation (Distance to border * Mow width)

Mow cut edge border (laps): positive value [0 - 5]. Defines which lap should be mowed (first lap: border, second lap: border - mow width, third lap: border - 2*mow width)

Mow area: [on, off]. Should the area to be mowed 

Mow cut edge exclusion: [on, off]. Should exclusions and border to be mowed

Mow cut edge border in ccw: [on, off]. Should exclusions and border to be mowed counter clockwise

### App
Select “App” under Settings. Here you have the option to configure some frontend settings.

1. Mower picture: Select one image what should be shown in the App

2. Max age for measured data: Every day on 00:00 CaSSAndRA removes unneccasarry data from storage. Confugure here how long the measured data should be stored

3. Time to wait before offline: Configure here how long should CaSSAndRA wait before state is changed to offline. If you using CaSSAndRA connection over HTTP or MQTT and you WiFi coverage not the best one increase the time to avoiding toggling of state message

4. Min charge current: Configure here from which charge current is rover in charging state (Attention: charge current has to be negative value)

5. Voltage to SoC: Conversion of voltage to state of charge (simple linear interpolation). The recommended voltage min (0%) is the shutdown voltage from the config.h of your sunray FW +0.5V. The recommended voltage max (100%) is the final charging voltage from the config.h of your sunray FW -0.5V. The SoC display has no controlling function and only serves as an overview on the home page

## Mapping
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
