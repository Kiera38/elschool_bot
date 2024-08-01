import datetime
import logging
import time
import typing

import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from elschool_bot.repository import elschool_api


logger = logging.getLogger(__name__)


class Repo:
    def __init__(self, connection: aiosqlite.Connection):
        self.db = connection

    async def has_user(self, user_id):
        cursor = await self.db.execute(
            "SELECT EXISTS(SELECT id FROM users WHERE id=?)", (user_id,)
        )
        return (await cursor.fetchone())[0]

    async def get_user_data(self, user_id):
        cursor = await self.db.execute(
            "SELECT login, password FROM users WHERE id=?", (user_id,)
        )
        return await cursor.fetchone()

    async def check_register_user(self, login, password):
        elschool = elschool_api
        return await elschool.register(login, password)

    async def register_user(
        self, user_id, jwtoken, url, quarter, login=None, password=None
    ):
        class_id = self._class_id_from_url(url)
        await self.db.execute(
            "INSERT INTO users (id, jwtoken, url, class_id, quarter, login, password) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, jwtoken, url, class_id, quarter, login, password),
        )
        await self.db.commit()
        logger.info(f"пользователь с id {user_id} зарегистрировался")

    async def update_data(self, user_id, jwtoken, login=None, password=None):
        await self.db.execute(
            "UPDATE users SET jwtoken=?, login=?, password=?, url=NULL, last_cache=0 WHERE id=?",
            (jwtoken, login, password, user_id),
        )
        await self.db.commit()
        logger.info(f"пользователь с id {user_id} обновил свои данные")

    async def get_user_data_jwtoken(self, user_id):
        cursor = await self.db.execute(
            "SELECT login, password, jwtoken FROM users WHERE id=?", (user_id,)
        )
        return await cursor.fetchone()

    async def get_grades(self, user_id):
        logger.debug(f"пользователь с id {user_id} получает оценки")
        async with self.db.cursor() as cursor:
            cursor = typing.cast(aiosqlite.Cursor, cursor)
            await cursor.execute(
                "SELECT last_cache, cache_time, quarter, jwtoken, url FROM users WHERE id=?",
                (user_id,),
            )
            last_cache, cache_time, quarter, jwtoken, url = await cursor.fetchone()
            if time.time() - last_cache > cache_time:
                logger.debug("время кеширования прошло, нужно получить новые оценки")
                return await self._update_cache(cursor, user_id, quarter, jwtoken, url)

            logger.debug(
                "время кеширования ещё не прошло, отправляются сохранённые оценки"
            )
            await cursor.execute(
                "SELECT lesson_name, lesson_date, date, mark FROM grades WHERE user_id=?",
                (user_id,),
            )
            grades = {}
            async for lesson_name, lesson_date, date, mark in cursor:
                if lesson_name not in grades:
                    grades[lesson_name] = []
                grades[lesson_name].append(
                    {"lesson_date": lesson_date, "date": date, "mark": mark}
                )
            return grades

    async def update_cache(self, user_id):
        async with self.db.cursor() as cursor:
            await cursor.execute(
                "SELECT quarter, jwtoken, url FROM users WHERE id=?", (user_id,)
            )
            quarter, jwtoken, url = await cursor.fetchone()
            return self._update_cache(cursor, user_id, quarter, jwtoken, url)

    async def set_cache_time(self, user_id, cache_time):
        await self.db.execute(
            "UPDATE users SET cache_time=? WHERE id=?", (cache_time, user_id)
        )
        await self.db.commit()

    async def _update_cache(
        self, cursor: aiosqlite.Cursor, user_id, quarter, jwtoken, url
    ):
        elschool = elschool_api
        if url:
            grades = await elschool.get_grades(jwtoken, url, quarter)
            await cursor.execute(
                "UPDATE users SET last_cache=? WHERE id=?", (time.time(), user_id)
            )
        else:
            grades, url = await elschool.get_grades_and_url(jwtoken, quarter)
            class_id = self._class_id_from_url(url)
            await cursor.execute(
                "UPDATE users SET last_cache=?, url=?, class_id=? WHERE id=?",
                (time.time(), url, class_id, user_id),
            )
        data = []
        for name, marks in grades.items():
            if not marks:
                data.append((user_id, name, "00.00.0000", "00.00.0000", 0))
            for mark in marks:
                data.append(
                    (user_id, name, mark["lesson_date"], mark["date"], mark["mark"])
                )

        await cursor.execute("DELETE FROM grades WHERE user_id=?", (user_id,))
        await cursor.executemany("INSERT INTO grades VALUES (?, ?, ?, ?, ?)", data)
        await self.db.commit()
        return grades

    async def clear_cache(self, user_id):
        await self.db.execute("UPDATE users SET last_cache=0 WHERE id=?", (user_id,))
        await self.db.commit()

    async def check_get_grades(self, jwtoken):
        elschool = elschool_api
        return await elschool.get_grades_and_url(jwtoken)

    async def delete_data(self, user_id):
        await self.db.execute("DELETE FROM users WHERE id=?", (user_id,))
        await self.db.commit()

    async def get_quarters(self, user_id):
        elschool = elschool_api
        cursor = await self.db.execute(
            "SELECT jwtoken, url FROM users WHERE id=?", (user_id,)
        )
        jwtoken, url = await cursor.fetchone()
        grades = await elschool.get_grades(jwtoken, url, None)
        return list(grades.keys())

    async def update_quarter(self, user_id, quarter):
        await self.db.execute(
            "UPDATE users SET quarter=? WHERE id=?", (quarter, user_id)
        )
        await self.clear_cache(user_id)

    async def save_schedule(
        self,
        user_id,
        name,
        next_time,
        interval,
        show_mode,
        lessons,
        dates,
        marks,
        show_without_marks,
    ):
        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT id FROM schedules WHERE user_id=?", (user_id,))
            ids = {id[0] async for id in cursor}
            max_id = max(ids) if ids else 0
            id = 1
            for id in range(1, max_id + 2):
                if id not in ids:
                    break
            if not name or name == "None":
                name = f"отправка {id}"
            logger.info(
                f"пользователь с id {user_id} сохранил отправку с id {id} и названием {name}, "
                f"которая покажет оценки в {next_time} с повторениями {interval}"
            )
            await cursor.execute(
                "INSERT INTO schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    id,
                    name,
                    next_time,
                    interval,
                    show_mode,
                    lessons,
                    dates,
                    marks,
                    show_without_marks,
                ),
            )
        await self.db.commit()
        return id

    async def update_schedule(
        self,
        user_id,
        id,
        name,
        next_time,
        interval,
        show_mode,
        lessons,
        dates,
        marks,
        show_without_marks,
    ):
        logger.info(
            f"пользователь с id {user_id} изменил отправку с названием {name}, "
            f"которая покажет оценки в {next_time} с повторениями {interval}"
        )
        await self.db.execute(
            "UPDATE schedules SET name=?, next_time=?, interval=?, show_mode=?, "
            "lessons=?, dates=?, marks=?, show_without_marks=? WHERE user_id=? AND id=?",
            (
                name,
                next_time,
                interval,
                show_mode,
                lessons,
                dates,
                marks,
                show_without_marks,
                user_id,
                id,
            ),
        )
        await self.db.commit()

    async def schedule_names(self, user_id):
        cursor = await self.db.execute(
            "SELECT id, name FROM schedules WHERE user_id=?", (user_id,)
        )
        return await cursor.fetchall()

    async def remove_schedule(self, user_id, id):
        logger.info(f"пользователь с id {user_id} удалил отправку с id {id}")
        await self.db.execute(
            "DELETE FROM schedules WHERE user_id=? AND id=?", (user_id, id)
        )
        await self.db.commit()

    async def get_schedule(self, user_id, id):
        cursor = await self.db.execute(
            "SELECT * FROM schedules WHERE user_id=? AND id=?", (user_id, id)
        )
        return await cursor.fetchone()

    async def get_schedules_for_restore(self):
        cursor = await self.db.execute("SELECT user_id, id, next_time FROM schedules")
        schedules = {}
        async for user_id, id, next_time in cursor:
            if user_id not in schedules:
                schedules[user_id] = []
            schedules[user_id].append({"id": id, "next_time": next_time})

        cursor = await self.db.execute(
            "SELECT id, autosend_schedule_time FROM users WHERE autosend_schedule_time!=NULL"
        )
        async for user_id, time in cursor:
            if user_id not in schedules:
                schedules[user_id] = []
            schedules[user_id].append({"id": -1, "next_time": time})
        return schedules

    async def get_results(self, user_id):
        cursor = await self.db.execute(
            "SELECT jwtoken, url FROM users WHERE id=?", (user_id,)
        )
        jwtoken, url = await cursor.fetchone()
        elschool = elschool_api
        if url:
            return await elschool.get_results(jwtoken, url)
        else:
            results, url = await elschool.get_results_and_url(jwtoken)
            class_id = self._class_id_from_url(url)
            await self.db.execute(
                "UPDATE users SET url=?, class_id=? WHERE id=?",
                (url, class_id, user_id),
            )
            await self.db.commit()
            return results

    async def get_diaries(self, user_id, date: datetime.date):
        if date.isocalendar()[2] == 7:
            return "в этот день нет расписания. Тебе оно зачем понадобилось?"
        async with self.db.cursor() as cursor:
            diaries = await self._get_diaries(cursor, user_id, date)
            default_changes = await self._get_diaries_changes(
                cursor, user_id, date.isocalendar()[2]
            )
            changes = await self._get_diaries_changes(
                cursor, user_id, self._as_timestamp(date)
            )
            self._apply_diaries_changes(default_changes, diaries)
            self._apply_diaries_changes(changes, diaries)
            return diaries

    def _apply_diaries_changes(self, changes, diaries):
        for change in changes:
            number = change["number"]
            if change["remove"]:
                del diaries[number]
                continue
            if number not in diaries:
                diaries[number] = {
                    "number": number,
                    "name": "",
                    "start_time": "",
                    "end_time": "",
                    "homework": "",
                }
            if change["name"]:
                diaries[number]["name"] = change["name"]
            if change["start_time"]:
                diaries[number]["start_time"] = change["start_time"]
            if change["end_time"]:
                diaries[number]["end_time"] = change["end_time"]
            if change["homework"]:
                diaries[number]["homework"] = change["homework"]

    def _as_timestamp(self, date: datetime.date):
        return datetime.datetime(date.year, date.month, date.day).timestamp()

    async def check_class_id(self, class_id, user_id, need_commit=True):
        if class_id is None:
            cursor = await self.db.execute(
                "SELECT url FROM users WHERE id=?", (user_id,)
            )
            (url,) = await cursor.fetchone()
            class_id = self._class_id_from_url(url)
            await self.db.execute(
                "UPDATE users SET class_id=? WHERE id=?", (class_id, user_id)
            )
            if need_commit:
                await self.db.commit()
        return class_id

    async def _get_diaries_changes(self, cursor: aiosqlite.Cursor, user_id, timestamp):
        await cursor.execute("SELECT class_id FROM users WHERE id=?", (user_id,))
        class_id = await self.check_class_id((await cursor.fetchone())[0], user_id)
        await cursor.execute(
            "SELECT number, name, start_time, end_time, homework, remove FROM schedule_changes "
            "WHERE class_id=? AND date=?",
            (class_id, timestamp),
        )
        changes = list(await cursor.fetchall())
        changes = [
            {
                "number": number,
                "name": name,
                "start_time": start_time,
                "end_time": end_time,
                "homework": homework,
                "remove": remove,
            }
            for number, name, start_time, end_time, homework, remove in changes
        ]
        return changes

    async def _get_diaries(self, cursor, user_id, date: datetime.date):
        await cursor.execute(
            "SELECT schedule_last_cache, cache_time, jwtoken, url FROM users WHERE id=?",
            (user_id,),
        )
        last_cache, cache_time, jwtoken, url = await cursor.fetchone()
        if time.time() - last_cache > cache_time:
            logger.debug("время кеширования прошло, нужно получить новое")
            return await self._update_diaries_cache(cursor, user_id, jwtoken, url, date)

        await cursor.execute(
            "SELECT number, name, start_time, end_time, homework "
            "FROM schedule_cache WHERE user_id=? AND date=?",
            (user_id, date.strftime("%d.%m.%Y")),
        )
        diaries = {
            number: {
                "number": number,
                "name": name,
                "homework": homework,
                "start_time": start_time,
                "end_time": end_time,
            }
            async for number, name, start_time, end_time, homework in cursor
        }

        if not diaries:
            return await self._update_diaries_cache(cursor, user_id, jwtoken, url, date)

        return diaries

    def _class_id_from_url(self, url):
        return int(url.lower().split("departmentid")[1].split("&")[0][1:])

    async def _update_diaries_cache(
        self, cursor: aiosqlite.Cursor, user_id, jwtoken, url, date
    ):
        elschool = elschool_api
        if url:
            diaries = await elschool.get_diaries(jwtoken, url, date)
            await cursor.execute(
                "UPDATE users SET schedule_last_cache=? WHERE id=?",
                (time.time(), user_id),
            )
        else:
            diaries, url = await elschool.get_diaries_and_url(jwtoken, date)
            class_id = self._class_id_from_url(url)
            await cursor.execute(
                "UPDATE users SET schedule_last_cache=?, url=?, class_id=? WHERE id=?",
                (time.time(), url, class_id, user_id),
            )
        await cursor.execute("DELETE FROM schedule_cache WHERE user_id=?", (user_id,))
        data = []
        for day_date, day in diaries.items():
            if day is None:
                continue
            for lesson in day.values():
                data.append(
                    (
                        user_id,
                        day_date,
                        lesson["number"],
                        lesson["name"],
                        lesson["start_time"],
                        lesson["end_time"],
                        lesson["homework"],
                    )
                )
        await cursor.executemany(
            "INSERT INTO schedule_cache VALUES (?, ?, ?, ?, ?, ?, ?)", data
        )
        await self.db.commit()
        return diaries[date.strftime("%d.%m.%Y")]

    async def add_changes(
        self, user_id, date: typing.Union[datetime.date, int], changes
    ):
        if isinstance(date, int):
            await self._add_changes(user_id, date, changes)
        else:
            await self._add_changes(user_id, self._as_timestamp(date), changes)

        day = datetime.date.today() - datetime.timedelta(days=1)
        await self.db.execute(
            "DELETE FROM schedule_changes WHERE date<?", (self._as_timestamp(day),)
        )
        await self.db.commit()

    async def _add_changes(self, user_id, timestamp, changes):
        cursor = await self.db.execute(
            "SELECT class_id FROM users WHERE id=?", (user_id,)
        )
        (class_id,) = await cursor.fetchone()
        class_id = await self.check_class_id(class_id, user_id, False)
        data = [
            (
                class_id,
                timestamp,
                number,
                lesson.get("name"),
                lesson.get("start_time"),
                lesson.get("end_time"),
                lesson.get("homework"),
                lesson.get("homework_next"),
                lesson.get("remove"),
            )
            for number, lesson in changes.items()
        ]
        await self.db.executemany(
            "INSERT INTO schedule_changes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", data
        )

    async def save_homework(self, user_id, lesson, homework):
        day = datetime.date.today() + datetime.timedelta(days=1)
        for i in range(30):
            diaries = await self.get_diaries(user_id, day)
            if diaries is None or isinstance(diaries, str):
                day += datetime.timedelta(days=1)
                continue
            for day_lesson in diaries.values():
                if day_lesson["name"] == lesson:
                    if day_lesson["homework"]:
                        homework = "\n".join((day_lesson["homework"], homework))
                    await self.add_changes(
                        user_id,
                        day,
                        {
                            day_lesson["number"]: {
                                "homework": homework,
                                "homework_next": True,
                            }
                        },
                    )
                    return day
            day += datetime.timedelta(days=1)

    async def get_user_autosend_schedule(self, user_id):
        cursor = await self.db.execute(
            "SELECT autosend_schedule_time, autosend_schedule_interval FROM users WHERE id=?",
            (user_id,),
        )
        return await cursor.fetchone()

    async def set_user_autosend_schedule(self, user_id, time, interval):
        await self.db.execute(
            "UPDATE users SET autosend_schedule_time=?, autosend_schedule_interval=? WHERE id=?",
            (time, interval, user_id),
        )
        await self.db.commit()

    async def get_user_notify_change_schedule(self, user_id):
        cursor = await self.db.execute(
            "SELECT notify_change_schedule FROM users WHERE id=?", (user_id,)
        )
        return (await cursor.fetchone())[0]

    async def set_user_notify_change_schedule(self, user_id, notify_change_schedule):
        await self.db.execute(
            "UPDATE users SET notify_change_schedule=? WHERE id=?",
            (notify_change_schedule, user_id),
        )
        await self.db.commit()

    async def get_class_users_notify_change_schedule(self, user_id):
        cursor = await self.db.execute(
            "SELECT class_id FROM users WHERE id=?", (user_id,)
        )
        (class_id,) = await cursor.fetchone()
        class_id = await self.check_class_id(class_id, user_id)
        cursor = await self.db.execute(
            "SELECT id FROM users WHERE class_id=?" "AND notify_change_schedule",
            (class_id,),
        )
        return [i[0] async for i in cursor]


class RepoMiddleware(BaseMiddleware):
    def __init__(self, dbfile):
        self.dbfile = dbfile

    async def __call__(
        self,
        handler: typing.Callable[
            [TelegramObject, typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]
        ],
        event: TelegramObject,
        data: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        async with aiosqlite.connect(self.dbfile) as connection:
            data["repo"] = Repo(connection)
            return await handler(event, data)
