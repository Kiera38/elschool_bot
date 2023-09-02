import sqlite3

db = sqlite3.connect('../bot.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    jwtoken TEXT,
    url TEXT,
    quarter TEXT,
    login TEXT,
    password TEXT,
    last_cache INTEGER NOT NULL DEFAULT 0,
    cache_time INTEGER DEFAULT 3600)''')
cursor.execute('''CREATE TABLE grades (
    user_id INTEGER,
    lesson_name TEXT,
    lesson_date TEXT,
    date TEXT,
    mark INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)''')
