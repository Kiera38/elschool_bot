from dataclasses import dataclass

import aiosqlite


@dataclass
class Mark:
    lesson_name: str
    lesson_date: str
    date: str
    mark: int


class GradesRepo:
    def __init__(self, connection: aiosqlite.Connection):
        self.db = connection

    async def get_from_user_id(self, user_id: int):
        cursor = await self.db.execute(
            "SELECT lesson_name, lesson_date, date, mark FROM grades WHERE user_id=?",
            (user_id,),
        )
        marks = [Mark(*row) for row in cursor]
        return marks

    async def update_for_user_id(self, user_id: int, marks: list[Mark]):
        await self.db.execute("DELETE FROM grades WHERE user_id=?", (user_id,))
        await self.db.executemany(
            "INSERT INTO grades (user_id, lesson_name, lesson_date, date, mark) VALUES (?, ?, ?, ?, ?)",
            [
                (user_id, mark.lesson_name, mark.lesson_date, mark.date, mark.mark)
                for mark in marks
            ],
        )
        await self.db.commit()
