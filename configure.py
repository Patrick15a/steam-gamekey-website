"""Interaktive Einrichtung der Sicherheitseinstellungen."""
import getpass
import os
import secrets
from pathlib import Path

import bcrypt

out = Path(__file__).resolve().parent / '.env'
if out.exists():
    raise SystemExit('Die Datei .env existiert bereits. Sie wurde NICHT überschrieben.')

password = getpass.getpass('Admin-Passwort (Eingabe unsichtbar): ')
confirmation = getpass.getpass('Admin-Passwort wiederholen: ')
if password != confirmation:
    raise SystemExit('Die Passwörter stimmen nicht überein.')
if len(password) < 12 or len(password.encode('utf-8')) > 72:
    raise SystemExit('Bitte ein Passwort mit mindestens 12 Zeichen und maximal 72 UTF-8-Bytes wählen.')

hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('ascii')
config = (
    '# Nicht in Git/ZIP einfügen; Datei vor fremdem Zugriff schützen!\n'
    'KEYS_SECRET_KEY={}\n'
    'KEYS_ADMIN_PASSWORD_HASH={}\n'
    'KEYS_COOKIE_SECURE=1\n'
    '# KEYS_DB_PATH=/opt/keys/gamekeys.db\n'
    '# KEYS_TRUSTED_HOSTS=keys.example.de\n'
).format(secrets.token_hex(32), hashed)
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
fd = os.open(str(out), flags, 0o600)
with os.fdopen(fd, 'w', encoding='utf8') as f:
    f.write(config)
print('Konfiguration in {} angelegt (Dateirechte 0600).'.format(out))
print('Für HTTPS ist KEYS_COOKIE_SECURE=1 korrekt. Bei rein lokalem HTTP-Test auf 0 setzen.')
