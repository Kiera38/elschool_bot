import sqlite3

db = sqlite3.connect("../bot.db")
cursor = db.cursor()
cursor.execute(
    """CREATE TABLE IF NOT EXISTS users  (
    id INTEGER PRIMARY KEY,
    jwtoken TEXT,
    url TEXT,
    quarter TEXT,
    login TEXT,
    password TEXT,
    last_cache INTEGER NOT NULL DEFAULT 0,
    cache_time INTEGER DEFAULT 3600)"""
)
cursor.execute(
    """CREATE TABLE IF NOT EXISTS grades  (
    user_id INTEGER,
    lesson_name TEXT,
    lesson_date TEXT,
    date TEXT,
    mark INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"""
)
cursor.execute(
    """CREATE TABLE IF NOT EXISTS schedules  (
    user_id INTEGER,
    id INTEGER,
    name TEXT,
    next_time INTEGER,
    interval INTEGER,
    show_mode INTEGER,
    lessons TEXT,
    dates INTEGER,
    marks TEXT,
    show_without_marks INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, id))"""
)
db.commit()
