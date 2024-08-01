import sqlite3

db = sqlite3.connect("../bot.db")
cursor = db.cursor()
cursor.execute("ALTER TABLE users ADD COLUMN autosend_schedule_time TEXT")
cursor.execute(
    "ALTER TABLE users ADD COLUMN autosend_schedule_interval INTEGER DEFAULT 1"
)
cursor.execute("ALTER TABLE users ADD COLUMN notify_change_schedule INTEGER")
# cursor.execute('ALTER TABLE users ADD COLUMN notify_lessons INTEGER')
db.commit()
