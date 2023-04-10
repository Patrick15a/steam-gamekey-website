import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, request, Response, session
from flask_sqlalchemy import SQLAlchemy
import random
import string
import bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gamekeys.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'S1$WKk8PVdzW9bv' # Dieser Secret Key wird verwendet um die Session des Admin Logins zu verschlüsseln. Wird er geändert müssen sich alle Clients neu anmelden.
db = SQLAlchemy(app) 

# Passwort Generator: 
gen_password = ''  # Ersetzen Sie dies durch Ihr eigenes Passwort
gen_hashed_password = bcrypt.hashpw(gen_password.encode('utf-8'), bcrypt.gensalt())
if gen_password is not '':
    print('\033[32mDein Verschlüsseltes Passwort: \033[33m' + gen_hashed_password + '\033[0m') # Das Verschlüsselte Passwort wird in der Konsole ausgegeben, setze dieses in der folgenden Zeile ein und lösche das Passwort oben wieder.
hashed_password = b'$2a$12$Ja0/Ugb4MwoG5Vv76oy2Deeg0ZvJAQRAtLrzNn48XkMoyJcjl9TFS' # Setzte hier das Verschlüsselte Passwort aus der Konsole ein.

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
        return "<OneTimeKey {}>".format(self.key)

@app.route('/')
def index():
    games = (GameKey.query
             .with_entities(GameKey.game_name)
             .filter(GameKey.used == False)
             .order_by(GameKey.game_name)
             .distinct()
             .all())
    return render_template('index.html', games=games)

@app.route('/claim_key', methods=['POST'])
def claim_key():
    one_time_key = request.form['one_time_key']
    game_name = request.form['game_name']

    # Überprüfe, ob der einmalige Schlüssel gültig ist
    ot_key = OneTimeKey.query.filter_by(key=one_time_key, used=False).first()
    if ot_key is None:
        return render_template('error.html', message='Ungültiger oder bereits verwendeter einmaliger Schlüssel.')

    # Finde den ersten nicht verwendeten Gamekey für das ausgewählte Spiel
    game_key = GameKey.query.filter_by(game_name=game_name, used=False).first()

    if game_key:
        game_key.used = True
        ot_key.used = True
        db.session.commit()
        return render_template('key.html', game_name=game_name, game_key=game_key.key)
    else:
        return render_template('error.html', message='Es sind keine Gamekeys für das ausgewählte Spiel verfügbar.')

def check_auth(password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


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
        password = request.form['password']
        if check_auth(password):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('error.html', message='Falsches Passwort!')

    return render_template('login.html')

@app.route('/logout')
@requires_auth
def logout():
    session.clear()  # Löscht alle Sitzungsdaten
    return redirect(url_for('index'))  # Leitet den Benutzer zur Startseite oder Anmeldeseite zurück

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
    games = GameKey.query.all()
    return render_template('added_games.html', games=games)

@app.route('/update_game_status/<int:game_id>', methods=['POST'])
@requires_auth
def update_game_status(game_id):
    game = GameKey.query.get(game_id)
    if game:
        game.used = not game.used
        db.session.commit()
        return redirect(url_for('added_games', _anchor='game-{}'.format(game_id)))
    else:
        return render_template('error.html', message="Eintrag nicht gefunden"), 404

@app.route('/delete_game/<int:game_id>', methods=['POST'])
@requires_auth
def delete_game(game_id):
    game = GameKey.query.get(game_id)
    if game:
        db.session.delete(game)
        db.session.commit()
        return redirect(url_for('added_games', _anchor='game-{}'.format(game_id-1)))
    else:
        return render_template('error.html', message="Eintrag nicht gefunden"), 404

@app.route('/delete_used_gamekeys', methods=['POST'])
@requires_auth
def delete_used_gamekeys():
    used_gamekeys = GameKey.query.filter(GameKey.used == True).all()
    for gamekey in used_gamekeys:
        db.session.delete(gamekey)
    db.session.commit()
    return redirect(url_for('added_games'))

@app.route('/add_game_keys', methods=['POST'])
@requires_auth
def add_game_keys():
    game_names = request.form.getlist('game_names[]')
    game_keys = request.form.getlist('game_keys[]')

    if len(game_names) != len(game_keys):
        return render_template('error.html', message='Anzahl der Spielnamen und Gamekeys stimmt nicht überein.')

    for i in range(len(game_names)):
        game_name = game_names[i]
        game_key = game_keys[i]
        new_game_key = GameKey(game_name=game_name, key=game_key, used=False)
        db.session.add(new_game_key)

    db.session.commit()
    return render_template('success.html', message='Gamekeys erfolgreich hinzugefügt')

@app.route('/manage_one_time_keys')
@requires_auth
def manage_one_time_keys():
    one_time_keys = OneTimeKey.query.all()
    return render_template('manage_one_time_keys.html', one_time_keys=one_time_keys)

def generate_one_time_key(length=10):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/add_one_time_key', methods=['POST'])
@requires_auth
def add_one_time_key():
    key = generate_one_time_key()
    new_key = OneTimeKey(key=key, used=False)
    db.session.add(new_key)
    db.session.commit()
    return redirect(url_for('manage_one_time_keys'))
    
@app.route('/remove_used_keys', methods=['POST'])
@requires_auth
def remove_used_keys():
    used_keys = OneTimeKey.query.filter(OneTimeKey.used == True).all()
    for key in used_keys:
        db.session.delete(key)
    db.session.commit()
    return redirect(url_for('manage_one_time_keys'))

@app.route('/delete_one_time_key/<int:key_id>', methods=['POST'])
@requires_auth
def delete_one_time_key(key_id):
    key = OneTimeKey.query.get(key_id)
    if key:
        db.session.delete(key)
        db.session.commit()
        return redirect(url_for('manage_one_time_keys'))
    else:
        return render_template('error.html', message="Eintrag nicht gefunden"), 404

def create_tables():
    db.create_all()

if __name__ == '__main__':
    create_tables()
    app.run(debug=False, port=5000)
