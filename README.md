# GameKey-Website

Eine einfache Webanwendung zum Verwalten und Verteilen von Gamekeys.

## Funktionen

- Anfordern eines Steam Game Key aus einer Liste mittels einmaligen Schlüssel
- (Admin) Hinzufügen und Verwalten von Stean Game Keys
- (Admin) Generieren und Verwalten von einmaligen Schlüsseln

## Demo Server
Unter https://demokeys.myfilehost.de habe ich einen Demo Server bereitgestellt. Mit dem Passwort `Admin` können dort alle Funktionen getestet werden.
Die Datenbank des Demo Servers wird Stündlich zurückgesetzt.

## Installation und Ausführung

1. Stellen Sie sicher, dass Sie Python 2.7.13 und virtualenv auf Ihrem System installiert haben.

2. Klonen Sie das Repository:
```
git clone https://github.com/patrick15a/steam-gamekey-website.git
cd steam-gamekey-website
```

3. Erstellen Sie eine virtuelle Umgebung und installieren Sie die Abhängigkeiten:
```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. Initialisieren Sie die Datenbank:
```
python init_db.py
```

5. Führen Sie die Anwendung aus:
```
python app.py
```

Die Anwendung ist jetzt unter http://127.0.0.1:5000 erreichbar.
Du kannst den Port in der app.py in der letzten Zeile ändern.
```
app.run(debug=True, port=5000)
```


## Anpassung
Um die Anwendung an Ihre Bedürfnisse anzupassen, können Sie den Code in `app.py` und die HTML-Vorlagen im `templates`-Ordner ändern. Das Styling der Anwendung kann in der `static/styles.css`-Datei angepasst werden.

## Anmerkung
Ich bin Hobby Entwickler. Der Code kann Fehler und unnötige Zeilen enthalten.
