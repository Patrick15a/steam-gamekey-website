# GameKey-Website

Eine einfache Webanwendung zum Verwalten und Verteilen von Gamekeys.

## Funktionen

- Anfordern eines Steam Gamekeys aus einer Liste mithilfe eines einmaligen Schlüssels
- (Admin) Hinzufügen und Verwalten von Steam Gamekeys
- (Admin) Generieren und Verwalten von einmaligen Schlüsseln

## Installation und Ausführung

1. Stellen Sie sicher, dass Sie Debian 13 verwenden, und installieren Sie die benötigten Pakete:

   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-venv python3-pip
   ```

2. Klonen Sie das Repository nach `/opt/keys`:

   ```bash
   sudo git clone https://github.com/patrick15a/steam-gamekey-website.git /opt/keys
   cd /opt/keys
   ```

3. Erstellen Sie eine virtuelle Umgebung und installieren Sie die Abhängigkeiten:

   ```bash
   sudo python3 -m venv /opt/keys/venv
   sudo /opt/keys/venv/bin/python -m pip install -r /opt/keys/requirements.txt
   ```

4. Richten Sie das Admin-Passwort und den Secret Key ein:

   ```bash
   sudo /opt/keys/venv/bin/python /opt/keys/configure.py
   ```

   Geben Sie das gewünschte Admin-Passwort ein. Das Skript erstellt automatisch einen bcrypt-Passwort-Hash und einen zufälligen Secret Key in der Datei `/opt/keys/.env`. Der Secret Key schützt die Flask-Sitzungen und muss nicht aufgeschrieben werden.

   Öffnen Sie danach die Konfiguration:

   ```bash
   sudo nano /opt/keys/.env
   ```

   Ergänzen Sie folgende Einstellungen (eine später verwendete Domain muss ebenfalls bei `KEYS_TRUSTED_HOSTS` eingetragen werden):

   ```dotenv
   KEYS_DB_PATH=/var/lib/keys/gamekeys.db
   KEYS_TRUSTED_HOSTS=localhost,127.0.0.1
   KEYS_COOKIE_SECURE=1
   ```

   Die automatisch erstellten Werte `KEYS_SECRET_KEY` und `KEYS_ADMIN_PASSWORD_HASH` beibehalten. `KEYS_COOKIE_SECURE=1` ist für den Betrieb mit HTTPS vorgesehen; für einen lokalen HTTP-Test kann vorübergehend `0` verwendet werden.

5. Erstellen Sie einen eigenen Benutzer für die Anwendung und initialisieren Sie die Datenbank:

   ```bash
   sudo useradd --system --no-create-home --shell /usr/sbin/nologin keysapp
   sudo install -d -o keysapp -g keysapp -m 0750 /var/lib/keys
   sudo chown root:keysapp /opt/keys/.env
   sudo chmod 640 /opt/keys/.env
   sudo chmod 755 /opt/keys
   cd /opt/keys
   sudo -u keysapp /opt/keys/venv/bin/python -m flask --app app init-db
   ```

   Die SQLite-Datenbank wird unter `/var/lib/keys/gamekeys.db` angelegt. Die `.env`-Datei darf nicht auf GitHub hochgeladen werden.

6. Erstellen Sie den systemd-Dienst:

   ```bash
   sudo nano /etc/systemd/system/keys.service
   ```

   Fügen Sie folgenden Inhalt ein:

   ```ini
   [Unit]
   Description=Gamekey-Verwaltung (Flask / Gunicorn)
   After=network.target

   [Service]
   Type=simple
   User=keysapp
   Group=keysapp
   WorkingDirectory=/opt/keys
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/opt/keys/venv/bin/gunicorn --no-control-socket --workers 2 --bind 127.0.0.1:5123 --access-logfile - --error-logfile - app:app
   Restart=on-failure
   RestartSec=3
   NoNewPrivileges=true
   PrivateTmp=true
   ProtectSystem=full
   ProtectHome=true

   [Install]
   WantedBy=multi-user.target
   ```

7. Aktivieren und starten Sie die Anwendung:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now keys
   sudo systemctl status keys
   ```

   Die Anwendung ist nun lokal unter `http://127.0.0.1:5123` erreichbar. Der Dienst startet beim Hochfahren des Servers automatisch.

   Die Logs können bei Bedarf mit folgendem Befehl eingesehen werden:

   ```bash
   sudo journalctl -u keys -n 50 --no-pager
   ```

## Anpassung

Um die Anwendung anzupassen, können Sie den Code in `app.py` und die HTML-Vorlagen im Ordner `templates` ändern. Das Design befindet sich in `static/styles.css`. Einstellungen wie Datenbankpfad und Secret Key werden in der Datei `.env` verwaltet.

## Upgrading

Vor einem Upgrade muss die bestehende **`gamekeys.db` gesichert** werden. Anschließend ist eine **Neuinstallation wie oben beschrieben** erforderlich. Stoppen Sie den neuen Dienst und ersetzen Sie die neu angelegte `/var/lib/keys/gamekeys.db` durch die zuvor gesicherte Datenbank. Setzen Sie danach die Dateirechte mit `sudo chown keysapp:keysapp /var/lib/keys/gamekeys.db` und starten Sie den Dienst mit `sudo systemctl start keys` erneut. Dadurch bleiben die gespeicherten Gamekeys und einmaligen Schlüssel erhalten.

## Anmerkung

Ich bin Hobby-Entwickler. Der Code kann Fehler und unnötige Zeilen enthalten.
