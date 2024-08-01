import sqlite3

db = sqlite3.connect("../bot.db")
cursor = db.cursor()
cursor.execute("ALTER TABLE schedules ADD COLUMN show_without_marks INTEGER DEFAULT 0")
db.commit()
