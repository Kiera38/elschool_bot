import datetime
import logging
import time
import typing
from dataclasses import dataclass

import aiosqlite

from elschool_bot.repository.base_api import Api
from elschool_bot.repository.users import UserRepo


logger = logging.getLogger(__name__)


@dataclass
class Lesson:
    number: int
    name: str
    homework: str
    start_time: str
    end_time: str


class DiariesCacheRepo:
    def __init__(self, connection: aiosqlite.Connection):
        self.db = connection

    async def get_diaries(self, user_id: int, date: datetime.date):
        cursor = await self.db.execute(
            "SELECT number, name, start_time, end_time, homework "
            "FROM schedule_cache WHERE user_id=? AND date=?",
            (user_id, date.strftime("%d.%m.%Y")),
        )
        diaries = {
            number: Lesson(number, name, homework, start_time, end_time)
            async for number, name, start_time, end_time, homework in cursor
        }
        return diaries

    async def set_diaries(self, user_id: int, diaries):
        await self.db.execute("DELETE FROM schedule_cache WHERE user_id=?", (user_id,))
        data = []
        for day_date, day in diaries.items():
            if day is None:
                continue
            for lesson in day.values():
                data.append(
                    (
                        user_id,
                        day_date,
                        lesson.number,
                        lesson.name,
                        lesson.start_time,
                        lesson.end_time,
                        lesson.homework,
                    )
                )
        await self.db.executemany(
            "INSERT INTO schedule_cache VALUES (?, ?, ?, ?, ?, ?, ?)", data
        )
        await self.db.commit()


@dataclass
class LessonChanges:
    number: int
    name: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    homework: str | None = None
    homework_next: bool = False
    remove: bool = False


def _as_timestamp(date: datetime.date):
    return datetime.datetime(date.year, date.month, date.day).timestamp()


class DiariesChangesRepo:
    def __init__(self, connection: aiosqlite.Connection):
        self.db = connection

    async def add_changes(
        self, class_id, date: typing.Union[datetime.date, int], changes
    ):
        if isinstance(date, int):
            await self._add_changes(class_id, date, changes)
        else:
            await self._add_changes(class_id, _as_timestamp(date), changes)

        day = datetime.date.today() - datetime.timedelta(days=1)
        await self.db.execute(
            "DELETE FROM schedule_changes WHERE date<? AND date>7",
            (_as_timestamp(day),),
        )
        await self.db.commit()

    async def _add_changes(self, class_id, timestamp, changes):
        data = [
            (
                class_id,
                timestamp,
                number,
                lesson.name,
                lesson.start_time,
                lesson.end_time,
                lesson.homework,
                lesson.homework_next,
                lesson.remove,
            )
            for number, lesson in changes.items()
        ]
        await self.db.executemany(
            "INSERT INTO schedule_changes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", data
        )

    async def get_diaries_changes(self, class_id, timestamp):
        if not isinstance(timestamp, int):
            timestamp = _as_timestamp(timestamp)

        cursor = await self.db.execute(
            "SELECT number, name, start_time, end_time, homework, remove FROM schedule_changes "
            "WHERE class_id=? AND date=?",
            (class_id, timestamp),
        )
        changes = list(await cursor.fetchall())
        changes = [
            LessonChanges(number, name, start_time, end_time, homework, remove=remove)
            for number, name, start_time, end_time, homework, remove in changes
        ]
        return changes


class DiariesRepo:
    def __init__(
        self,
        cache: DiariesCacheRepo,
        changes: DiariesChangesRepo,
        api: Api,
        user: UserRepo,
    ):
        self.cache = cache
        self.changes = changes
        self.api = api
        self.user = user

    async def get_diaries(self, date: datetime.date):
        if date.isocalendar()[2] == 7:
            return "в этот день нет расписания. Тебе оно зачем понадобилось?"
        diaries = self._get_diaries(date)
        class_id = await self.user.get_class_id()
        default_changes = await self.changes.get_diaries_changes(
            class_id, date.isocalendar()[2]
        )
        changes = await self.changes.get_diaries_changes(class_id, date)
        self._apply_changes(default_changes, diaries)
        self._apply_changes(changes, diaries)
        return diaries

    async def _update_diaries_cache(self, data, date):
        if data.url:
            diaries = await self.api.get_diaries(data.api.jwtoken, data.api.url, date)
            await self.user.update_schedule_cache()
        else:
            diaries, url = await self.api.get_diaries_and_url(data.api.jwtoken, date)
            await self.user.update_schedule_cache(url)

        data = {}
        for day_date, day in diaries.items():
            if day is None:
                continue
            data_day = {}
            for number, lesson in day.items():
                data_day[number] = Lesson(
                    lesson["number"],
                    lesson["name"],
                    lesson["homework"],
                    lesson["start_time"],
                    lesson["end_time"],
                )
            data[day_date] = data_day

        await self.cache.set_diaries(date, diaries)
        return data

    async def _get_diaries(self, date):
        data = await self.user.get_api_and_schedule_cache_data()
        if time.time() - data.last_cache > data.cache_time:
            logger.debug("время кеширования прошло, нужно получить новое")
            return await self._update_diaries_cache(data, date)

        diaries = await self.cache.get_diaries(self.user.user_id, date)
        if not diaries:
            return await self._update_diaries_cache(data, date)

        return diaries

    def _apply_changes(self, changes, diaries):
        for change in changes:
            number = change.number
            if change.remove:
                del diaries[number]
                continue
            if number not in diaries:
                diaries[number] = Lesson(number, "", "", "", "")
            if change["name"]:
                diaries[number].name = change.name
            if change["start_time"]:
                diaries[number].start_time = change.start_time
            if change["end_time"]:
                diaries[number].end_time = change.end_time
            if change["homework"]:
                diaries[number].homework = change.homework

    async def save_homework(self, lesson, homework):
        day = datetime.date.today() + datetime.timedelta(days=1)
        class_id = await self.user.get_class_id()
        for i in range(30):
            diaries = await self.get_diaries(day)
            if diaries is None or isinstance(diaries, str):
                day += datetime.timedelta(days=1)
                continue
            for day_lesson in diaries.values():
                if day_lesson["name"] == lesson:
                    if day_lesson["homework"]:
                        homework = "\n".join((day_lesson["homework"], homework))
                    await self.changes.add_changes(
                        class_id,
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
