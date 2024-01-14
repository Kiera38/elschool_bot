import sqlite3

db = sqlite3.connect('../bot.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS schedule_cache (
    user_id INTEGER,
    date TEXT,
    number INTEGER,
    name TEXT,
    start_time TEXT,
    end_time TEXT,
    homework TEXT
)''')
cursor.execute('ALTER TABLE users ADD COLUMN schedule_last_cache INTEGER NOT NULL DEFAULT 0')
db.commit()
