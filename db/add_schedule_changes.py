import sqlite3

db = sqlite3.connect('../bot.db')
cursor = db.cursor()
cursor.execute('''ALTER TABLE users ADD COLUMN class_id INTEGER''')
cursor.execute('''CREATE TABLE IF NOT EXISTS schedule_changes (
    class_id INTEGER,
    date INTEGER,
    number INTEGER,
    name TEXT,
    start_time TEXT,
    end_time TEXT,
    homework TEXT,
    homework_next INTEGER,
    remove INTEGER,
    FOREIGN KEY (class_id) REFERENCES users(class_id) ON DELETE CASCADE
    )''')
db.commit()
