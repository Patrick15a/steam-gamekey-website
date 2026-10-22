"""Gamekey administration and redemption (Python 3.13 / Flask 3)."""

import hmac
import os
import secrets
from functools import wraps
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / '.env')

secret_key = os.environ.get('KEYS_SECRET_KEY', '')
password_hash = os.environ.get('KEYS_ADMIN_PASSWORD_HASH', '')
if len(secret_key) < 32 or not password_hash:
    raise RuntimeError(
        'Sicherheitskonfiguration fehlt. Bitte zuerst "python configure.py" ausfuehren '
        'oder KEYS_SECRET_KEY und KEYS_ADMIN_PASSWORD_HASH als Umgebungsvariablen setzen.'
    )

# Absoluter Standardpfad verhindert eine unbemerkte zweite DB im Flask-instance-Ordner.
database_path = Path(os.environ.get('KEYS_DB_PATH', str(PROJECT_DIR / 'gamekeys.db'))).expanduser()
if not database_path.is_absolute():
    raise RuntimeError('KEYS_DB_PATH muss ein absoluter Pfad sein.')

app = Flask(__name__)
app.config.update(
    SECRET_KEY=secret_key,
    SQLALCHEMY_DATABASE_URI='sqlite:///' + database_path.as_posix(),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SQLALCHEMY_ENGINE_OPTIONS={'connect_args': {'timeout': 30}},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('KEYS_COOKIE_SECURE', '1') == '1',
    MAX_CONTENT_LENGTH=128 * 1024,
)
if os.environ.get('KEYS_TRUSTED_HOSTS'):
    app.config['TRUSTED_HOSTS'] = [s.strip() for s in
                                   os.environ['KEYS_TRUSTED_HOSTS'].split(',') if s.strip()]

db = SQLAlchemy(app)


# Bestehende Tabellennamen und Spalten bleiben exakt erhalten.
class GameKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String(255), nullable=False)
    key = db.Column(db.String(255), nullable=False)
    used = db.Column(db.Boolean, default=False)


class OneTimeKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), nullable=False)
    used = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<OneTimeKey id={}>'.format(self.id)


def csrf_token():
    token = session.get('_csrf_token')
    if token is None:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


app.jinja_env.globals['csrf_token'] = csrf_token


@app.before_request
def verify_csrf():
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        expected = session.get('_csrf_token', '')
        provided = request.form.get('csrf_token', '')
        if not expected or not hmac.compare_digest(expected, provided):
            abort(400, description='Formular abgelaufen oder Sicherheitsprüfung fehlgeschlagen. Bitte die Seite neu laden.')


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'no-referrer'
    if request.path != '/static' and not request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.errorhandler(400)
def bad_request(error):
    return render_template('error.html', message=getattr(error, 'description', 'Ungültige Anfrage.')), 400


@app.route('/')
def index():
    games = (db.session.query(GameKey.game_name)
             .filter(GameKey.used.is_(False))
             .distinct()
             .order_by(GameKey.game_name)
             .all())
    return render_template('index.html', games=games)


@app.route('/claim_key', methods=['POST'])
def claim_key():
    one_time_key = request.form.get('one_time_key', '').strip()
    game_name = request.form.get('game_name', '').strip()
    if not 1 <= len(one_time_key) <= 50 or not 1 <= len(game_name) <= 255:
        return render_template('error.html', message='Bitte einen gültigen Schlüssel und ein Spiel wählen.'), 400

    # Both conditional updates are committed together. Even if two requests race,
    # the same access code / Steam key can be successfully redeemed only once.
    try:
        game_key = (GameKey.query.filter_by(game_name=game_name, used=False)
                    .order_by(GameKey.id).first())
        if game_key is None:
            return render_template('error.html', message='Es sind keine Gamekeys für das ausgewählte Spiel verfügbar.')
        claimed = db.session.execute(
            update(OneTimeKey)
            .where(OneTimeKey.key == one_time_key, OneTimeKey.used.is_(False))
            .values(used=True)
        )
        if claimed.rowcount != 1:
            db.session.rollback()
            return render_template('error.html', message='Ungültiger oder bereits verwendeter einmaliger Schlüssel.')

        game_claimed = db.session.execute(
            update(GameKey)
            .where(GameKey.id == game_key.id, GameKey.used.is_(False))
            .values(used=True)
        )
        if game_claimed.rowcount != 1:
            db.session.rollback()
            return render_template('error.html', message='Dieser Gamekey ist inzwischen nicht mehr verfügbar. Bitte erneut versuchen.'), 409
        result = game_key.key
        db.session.commit()
        return render_template('key.html', game_name=game_name, game_key=result)
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception('Fehler beim atomaren Einlösen eines Gamekeys')
        return render_template('error.html', message='Datenbankfehler. Bitte erneut versuchen.'), 503


def check_auth(password):
    try:
        raw = password.encode('utf-8')
        return len(raw) <= 72 and bcrypt.checkpw(raw, password_hash.encode('ascii'))
    except (ValueError, TypeError):
        return False


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        if check_auth(password):
            session.clear()
            session['logged_in'] = True
            session['_csrf_token'] = secrets.token_urlsafe(32)
            return redirect(url_for('admin'))
        return render_template('error.html', message='Falsches Passwort!'), 401
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@requires_auth
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/add_game_key')
@requires_auth
def add_game_key():
    return render_template('add_game_key.html')


@app.route('/admin')
@requires_auth
def admin():
    return render_template('admin.html')


@app.route('/added_games')
@requires_auth
def added_games():
    games = GameKey.query.order_by(GameKey.id).all()
    return render_template('added_games.html', games=games)


@app.route('/update_game_status/<int:game_id>', methods=['POST'])
@requires_auth
def update_game_status(game_id):
    game = db.session.get(GameKey, game_id)
    if game is None:
        return render_template('error.html', message='Eintrag nicht gefunden'), 404
    game.used = not game.used
    db.session.commit()
    return redirect(url_for('added_games', _anchor='game-{}'.format(game_id)))


@app.route('/delete_game/<int:game_id>', methods=['POST'])
@requires_auth
def delete_game(game_id):
    game = db.session.get(GameKey, game_id)
    if game is None:
        return render_template('error.html', message='Eintrag nicht gefunden'), 404
    db.session.delete(game)
    db.session.commit()
    previous = (GameKey.query.filter(GameKey.id < game_id)
                .order_by(GameKey.id.desc()).first())
    following = (GameKey.query.filter(GameKey.id > game_id)
                 .order_by(GameKey.id).first()) if previous is None else None
    target = previous or following
    return redirect(url_for('added_games', _anchor='game-{}'.format(target.id) if target else 'games-table'))


@app.route('/delete_used_gamekeys', methods=['POST'])
@requires_auth
def delete_used_gamekeys():
    GameKey.query.filter(GameKey.used.is_(True)).delete(synchronize_session=False)
    db.session.commit()
    return redirect(url_for('added_games', _anchor='games-table'))


@app.route('/add_game_keys', methods=['POST'])
@requires_auth
def add_game_keys():
    names = request.form.getlist('game_names[]')
    keys = request.form.getlist('game_keys[]')
    if not names or len(names) != len(keys) or len(names) > 100:
        return render_template('error.html', message='Ungültige Anzahl an Spielen oder Gamekeys.'), 400
    for name, key in zip(names, keys):
        name, key = name.strip(), key.strip()
        if not name or not key or len(name) > 255 or len(key) > 255:
            db.session.rollback()
            return render_template('error.html', message='Spielname und Gamekey dürfen nicht leer oder zu lang sein.'), 400
        db.session.add(GameKey(game_name=name, key=key, used=False))
    db.session.commit()
    return render_template('success.html', message='Gamekeys erfolgreich hinzugefügt')


@app.route('/manage_one_time_keys')
@requires_auth
def manage_one_time_keys():
    one_time_keys = OneTimeKey.query.order_by(OneTimeKey.id.desc()).all()
    return render_template('manage_one_time_keys.html', one_time_keys=one_time_keys)


def generate_one_time_key():
    # 24 kryptografisch zufällige Zeichen (ungefähr 143 Bit), im Modell max. 50.
    return secrets.token_urlsafe(18)


@app.route('/add_one_time_key', methods=['POST'])
@requires_auth
def add_one_time_key():
    key = generate_one_time_key()
    while OneTimeKey.query.filter_by(key=key).first() is not None:
        key = generate_one_time_key()
    db.session.add(OneTimeKey(key=key, used=False))
    db.session.commit()
    return redirect(url_for('manage_one_time_keys'))


@app.route('/remove_used_keys', methods=['POST'])
@requires_auth
def remove_used_keys():
    OneTimeKey.query.filter(OneTimeKey.used.is_(True)).delete(synchronize_session=False)
    db.session.commit()
    return redirect(url_for('manage_one_time_keys'))


@app.route('/delete_one_time_key/<int:key_id>', methods=['POST'])
@requires_auth
def delete_one_time_key(key_id):
    key = db.session.get(OneTimeKey, key_id)
    if key is None:
        return render_template('error.html', message='Eintrag nicht gefunden'), 404
    db.session.delete(key)
    db.session.commit()
    return redirect(url_for('manage_one_time_keys'))


@app.cli.command('init-db')
def init_db():
    """Neue leere SQLite-Datenbank initialisieren (NICHT bei einer Migration verwenden)."""
    db.create_all()
    print('Tabellen initialisiert in {}'.format(database_path))


if __name__ == '__main__':
    # Der Flask-Entwicklungsserver ist nicht für den öffentlichen Betrieb gedacht.
    app.run(host='127.0.0.1', port=int(os.environ.get('KEYS_PORT', '5123')), debug=False)
