import sqlite3

db = sqlite3.connect("../bot.db")
cursor = db.cursor()
cursor.execute("SELECT id, url FROM users")
data = [
    (int(url.lower().split("departmentid")[1].split("&")[0][1:]), user_id)
    for user_id, url in cursor
]
cursor.executemany("UPDATE users SET class_id=? WHERE id=?", data)
db.commit()
