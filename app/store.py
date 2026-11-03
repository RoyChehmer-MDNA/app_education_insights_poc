"""Local persistence, always scoped to the server-selected demonstration user."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS state (user TEXT, key TEXT, value TEXT, PRIMARY KEY(user,key))')
            db.execute('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, user TEXT, conversation TEXT, question TEXT, response TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
            db.execute('CREATE TABLE IF NOT EXISTS gaps (user TEXT, school TEXT, status TEXT DEFAULT "open", updated TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(user,school))')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.row_factory = sqlite3.Row
            with db:
                yield db
        finally:
            db.close()

    def get(self, user, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM state WHERE user=? AND key=?', (user, key)).fetchone()
        return json.loads(row['value']) if row else default

    def put(self, user, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO state VALUES (?,?,?)', (user, key, json.dumps(value, ensure_ascii=False)))

    def history(self, user, conversation):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM (SELECT * FROM messages WHERE user=? AND conversation=? ORDER BY id DESC LIMIT 50) ORDER BY id', (user, conversation)).fetchall()
        return [dict(r, response=json.loads(r['response'])) for r in rows]

    def save(self, user, conversation, question, response, rows):
        with self.connect() as db:
            db.execute('INSERT INTO messages(user,conversation,question,response) VALUES (?,?,?,?)', (user, conversation, question, json.dumps(response, ensure_ascii=False)))
            for row in rows:
                if row['previous'] - row['current'] >= 5:
                    db.execute('INSERT OR IGNORE INTO gaps(user,school) VALUES (?,?)', (user, row['school_id']))

    def gaps(self, user):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT school,status,updated FROM gaps WHERE user=? ORDER BY school', (user,))]

    def update_gap(self, user, school, status):
        with self.connect() as db:
            return db.execute('UPDATE gaps SET status=?,updated=CURRENT_TIMESTAMP WHERE user=? AND school=?', (status, user, school)).rowcount
