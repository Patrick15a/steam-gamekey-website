"""Run with: python -m unittest discover -s tests -v"""
import os
import re
import tempfile
import unittest
from pathlib import Path

import bcrypt

TEMP_DIR = tempfile.TemporaryDirectory()
os.environ['KEYS_SECRET_KEY'] = 'test-' + 'x' * 64
os.environ['KEYS_ADMIN_PASSWORD_HASH'] = bcrypt.hashpw(b'correct-test-password', bcrypt.gensalt(rounds=4)).decode('ascii')
os.environ['KEYS_COOKIE_SECURE'] = '0'
os.environ['KEYS_DB_PATH'] = str(Path(TEMP_DIR.name) / 'test.db')

from app import app, db, GameKey, OneTimeKey  # noqa: E402


class AppTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
            db.session.add(GameKey(game_name='Alpha', key='GAME-111', used=False))
            db.session.add(GameKey(game_name='Beta', key='GAME-222', used=False))
            db.session.add(OneTimeKey(key='ONCE-ABC', used=False))
            db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def csrf(self, path='/'):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        self.assertIsNotNone(match, path)
        return match.group(1).decode('ascii')

    def login(self):
        token = self.csrf('/login')
        response = self.client.post('/login', data={
            'csrf_token': token, 'password': 'correct-test-password'
        })
        self.assertEqual(response.status_code, 302)
        return self.csrf('/add_game_key')

    def test_redemption_consumes_both_keys(self):
        token = self.csrf()
        response = self.client.post('/claim_key', data={
            'csrf_token': token, 'one_time_key': 'ONCE-ABC', 'game_name': 'Alpha'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GAME-111', response.data)
        with app.app_context():
            self.assertTrue(OneTimeKey.query.filter_by(key='ONCE-ABC').first().used)
            self.assertTrue(GameKey.query.filter_by(key='GAME-111').first().used)
        second = self.client.post('/claim_key', data={
            'csrf_token': token, 'one_time_key': 'ONCE-ABC', 'game_name': 'Beta'
        })
        self.assertNotIn(b'GAME-222', second.data)
        with app.app_context():
            self.assertFalse(GameKey.query.filter_by(key='GAME-222').first().used)

    def test_no_key_available_does_not_consume_code(self):
        token = self.csrf()
        response = self.client.post('/claim_key', data={
            'csrf_token': token, 'one_time_key': 'ONCE-ABC', 'game_name': 'Unknown'
        })
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertFalse(OneTimeKey.query.filter_by(key='ONCE-ABC').first().used)

    def test_csrf_and_admin(self):
        unauthorized = self.client.get('/added_games')
        self.assertEqual(unauthorized.status_code, 302)
        self.assertEqual(self.client.post('/add_one_time_key').status_code, 400)
        token = self.login()
        response = self.client.post('/add_game_keys', data={
            'csrf_token': token,
            'game_names[]': ['Gamma', 'Delta'],
            'game_keys[]': ['GAME-333', 'GAME-444']
        })
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            self.assertEqual(GameKey.query.count(), 4)
        self.assertEqual(self.client.get('/added_games').status_code, 200)

    def test_generate_delete_and_toggle(self):
        token = self.login()
        response = self.client.post('/add_one_time_key', data={'csrf_token': token})
        self.assertEqual(response.status_code, 302)
        with app.app_context():
            entries = OneTimeKey.query.all()
            self.assertEqual(len(entries), 2)
            self.assertEqual(len([e.key for e in entries if len(e.key) == 24]), 1)
            key_id = entries[-1].id
            game_id = GameKey.query.filter_by(game_name='Beta').first().id
        self.assertEqual(self.client.post('/delete_one_time_key/{}'.format(key_id),
                                          data={'csrf_token': token}).status_code, 302)
        self.assertEqual(self.client.post('/update_game_status/{}'.format(game_id),
                                          data={'csrf_token': token}).status_code, 302)
        with app.app_context():
            self.assertIsNone(db.session.get(OneTimeKey, key_id))
            self.assertTrue(db.session.get(GameKey, game_id).used)


if __name__ == '__main__':
    unittest.main()
