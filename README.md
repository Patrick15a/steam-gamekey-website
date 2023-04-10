# GameKey-Website

Eine einfache Webanwendung zum Verwalten und Verteilen von Gamekeys.

## Funktionen

- Hinzufügen und Verwalten von Gamekeys über eine benutzerfreundliche Admin-Seite
- Generieren und Verwalten von einmaligen Schlüsseln für Benutzer
- Benutzer können einen Gamekey mit ihrem einmaligen Schlüssel anfordern
- Anzeige der verfügbaren Spiele für Benutzer

## Installation und Ausführung

1. Stellen Sie sicher, dass Sie Python 2.7.13 und virtualenv auf Ihrem System installiert haben.

2. Klonen Sie das Repository:

git clone https://github.com/yourusername/gamekey-website.git
cd gamekey-website

markdown
Copy code

3. Erstellen Sie eine virtuelle Umgebung und installieren Sie die Abhängigkeiten:

virtualenv venv
source venv/bin/activate
pip install -r requirements.txt

markdown
Copy code

4. Initialisieren Sie die Datenbank:

python init_db.py

markdown
Copy code

5. Führen Sie die Anwendung aus:

python app.py

perl
Copy code

Die Anwendung ist jetzt unter http://127.0.0.1:5000 erreichbar.

## Anpassung
Um die Anwendung an Ihre Bedürfnisse anzupassen, können Sie den Code in `app.py` und die HTML-Vorlagen im `templates`-Ordner ändern. Das Styling der Anwendung kann in der `static/styles.css`-Datei angepasst werden.
