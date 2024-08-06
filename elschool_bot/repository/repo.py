import datetime
import logging
import time
import typing

import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from elschool_bot.repository import elschool_api
from elschool_bot.repository.base_api import Api
from elschool_bot.repository.diaries import DiariesRepo
from elschool_bot.repository.grades import GradesRepo, Mark
from elschool_bot.repository.notifications import NotificationsRepo, Notification
from elschool_bot.repository.users import UserRepo, UserData, ApiData

logger = logging.getLogger(__name__)


class Repo:
    def __init__(
        self,
        user: UserRepo,
        grades: GradesRepo,
        notifications: NotificationsRepo,
        diaries: DiariesRepo,
        api: Api,
    ):
        self.user = user
        self.grades = grades
        self.notifications = notifications
        self.diaries = diaries
        self.api = api

    async def has_user(self, user_id):
        assert user_id == self.user.user_id
        return await self.user.has_user()

    async def get_user_data(self, user_id):
        assert user_id == self.user.user_id
        data = await self.user.get_user_data()
        return data.login, data.password

    async def check_register_user(self, login, password):
        elschool = elschool_api
        return await elschool.register(login, password)

    async def register_user(
        self, user_id, jwtoken, url, quarter, login=None, password=None
    ):
        assert user_id == self.user.user_id
        await self.user.add_user(jwtoken, url, quarter, login=login, password=password)

    async def update_data(self, user_id, jwtoken, login=None, password=None):
        assert user_id == self.user.user_id
        await self.user.update_data(UserData(login, password, jwtoken))

    async def get_user_data_jwtoken(self, user_id):
        assert user_id == self.user.user_id
        data = await self.user.get_user_data()
        return data.login, data.password, data.jwtoken

    async def get_grades(self, user_id):
        assert user_id == self.user.user_id
        logger.debug(f"пользователь с id {user_id} получает оценки")
        data = await self.user.get_api_and_cache_data()
        if time.time() - data.last_cache > data.cache_time:
            logger.debug("время кеширования прошло, нужно получить новые оценки")
            return await self._update_cache(data.api)

        grades_cache = await self.grades.get_from_user_id(self.user.user_id)
        grades = {}
        for mark in grades_cache:
            if mark.lesson_name not in grades:
                grades[mark.lesson_name] = []
            grades[mark.lesson_name].append(
                {"lesson_date": mark.lesson_date, "date": mark.date, "mark": mark}
            )
        return grades

    async def update_cache(self, user_id):
        assert user_id == self.user.user_id
        logger.debug(f"пользователь с id {user_id} обновляет кеш")
        data = await self.user.get_api_data()
        await self._update_cache(data)

    async def set_cache_time(self, user_id, cache_time):
        assert user_id == self.user.user_id
        logger.debug(f"пользователь с id {user_id} меняет время кеширования")
        await self.user.set_cache_time(cache_time)

    async def _update_cache(self, data: ApiData):
        if data.url:
            grades = await self.api.get_grades(data.jwtoken, data.url)
            await self.user.update_cache()
        else:
            grades, url = await self.api.get_grades_and_url(data.jwtoken)
            await self.user.update_cache(url)
        grades = grades[data.quarter]
        data = []
        for name, marks in grades.items():
            if not marks:
                data.append(Mark(name, "00.00.0000", "00.00.0000", 0))
            for mark in marks:
                data.append(Mark(name, mark["lesson_date"], mark["date"], mark["mark"]))
        await self.grades.update_for_user_id(self.user.user_id, data)
        return data

    async def clear_cache(self, user_id):
        assert user_id == self.user.user_id
        await self.user.clear_cache()

    async def check_get_grades(self, jwtoken):
        return await self.api.get_grades_and_url(jwtoken)

    async def delete_data(self, user_id):
        assert user_id == self.user.user_id
        logger.info(f"пользователь с id {user_id} удалился")
        await self.user.delete_user()

    async def get_quarters(self, user_id):
        assert user_id == self.user.user_id
        data = await self.user.get_api_data()
        grades = await self.api.get_grades(data.jwtoken, data.url)
        return list(grades.keys())

    async def update_quarter(self, user_id, quarter):
        assert user_id == self.user.user_id
        await self.user.set_quarter(quarter)

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
        assert user_id == self.user.user_id
        return await self.notifications.add_notification(
            user_id,
            Notification(
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
        assert user_id == self.user.user_id
        await self.notifications.update_notification(
            user_id,
            id,
            Notification(
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

    async def schedule_names(self, user_id):
        assert user_id == self.user.user_id
        names = await self.notifications.names(user_id)
        return [(name.id, name.name) for name in names]

    async def remove_schedule(self, user_id, id):
        assert user_id == self.user.user_id
        await self.notifications.delete_notification(user_id, id)

    async def get_schedule(self, user_id, id):
        assert user_id == self.user.user_id
        return await self.notifications.get_notification(user_id, id)

    async def get_schedules_for_restore(self):
        return await self.notifications.get_notifications_for_restore()

    async def get_results(self, user_id):
        assert user_id == self.user.user_id
        data = await self.user.get_api_data()
        if data.url:
            return await self.api.get_results(data.jwtoken, data.url)
        else:
            results, url = await self.api.get_results_and_url(data.jwtoken)
            await self.user.set_url(url)
            return results

    async def get_diaries(self, user_id, date: datetime.date):
        assert user_id == self.user.user_id
        return await self.diaries.get_diaries(date)

    async def check_class_id(self, class_id, user_id, need_commit=True):
        assert user_id == self.user.user_id
        return await self.user.check_class_id(class_id, need_commit)

    async def add_changes(
        self, user_id, date: typing.Union[datetime.date, int], changes
    ):
        assert user_id == self.user.user_id
        class_id = await self.user.get_class_id()
        await self.diaries.changes.add_changes(class_id, date, changes)

    async def save_homework(self, user_id, lesson, homework):
        assert user_id == self.user.user_id
        await self.diaries.save_homework(lesson, homework)

    async def get_user_autosend_schedule(self, user_id):
        assert user_id == self.user.user_id
        return await self.user.get_autosend_schedule()

    async def set_user_autosend_schedule(self, user_id, time, interval):
        assert user_id == self.user.user_id
        await self.user.set_autosend_schedule(time, interval)

    async def get_user_notify_change_schedule(self, user_id):
        assert user_id == self.user.user_id
        return await self.user.get_notify_change_schedule()

    async def set_user_notify_change_schedule(self, user_id, notify_change_schedule):
        assert user_id == self.user.user_id
        await self.user.set_notify_change_schedule(notify_change_schedule)

    async def get_class_users_notify_change_schedule(self, user_id):
        assert user_id == self.user.user_id
        return self.user.get_class_users_notify_change_schedule()


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
