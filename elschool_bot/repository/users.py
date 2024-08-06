import logging
import time
from dataclasses import dataclass

import aiosqlite


logger = logging.getLogger(__name__)


@dataclass
class UserData:
    login: str | None
    password: str | None
    jwtoken: str


@dataclass
class ApiData:
    quarter: str
    jwtoken: str
    url: str | None


@dataclass
class ApiAndCacheData:
    last_cache: int
    cache_time: int
    api: ApiData


def _class_id_from_url(url):
    return int(url.lower().split("departmentid")[1].split("&")[0][1:])


class UserRepo:
    def __init__(self, connection: aiosqlite.Connection, user_id: int):
        self.db = connection
        self.user_id = user_id

    async def has_user(self):
        cursor = await self.db.execute(
            "SELECT EXISTS(SELECT id FROM users WHERE id=?)", (self.user_id,)
        )
        return (await cursor.fetchone())[0]

    async def get_user_data(self):
        cursor = await self.db.execute(
            "SELECT login, password, jwtoken FROM users WHERE id=?", (self.user_id,)
        )
        return UserData(*await cursor.fetchone())

    async def add_user(
        self,
        jwtoken: str,
        url: str,
        quarter: str,
        login: str | None = None,
        password: str | None = None,
    ):
        class_id = _class_id_from_url(url)
        await self.db.execute(
            "INSERT INTO users (id, jwtoken, url, class_id, quarter, login, password) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.user_id, jwtoken, url, class_id, quarter, login, password),
        )
        await self.db.commit()
        logger.info(f"пользователь с id {self.user_id} зарегистрировался")

    async def update_data(self, data: UserData):
        await self.db.execute(
            "UPDATE users SET jwtoken=?, login=?, password=?, url=NULL, last_cache=0 WHERE id=?",
            (data.jwtoken, data.login, data.password, self.user_id),
        )
        await self.db.commit()
        logger.info(f"пользователь с id {self.user_id} обновил свои данные")

    async def set_cache_time(self, cache_time: int):
        await self.db.execute(
            "UPDATE users SET cache_time=? WHERE id=?", (cache_time, self.user_id)
        )
        await self.db.commit()

    async def clear_cache(self):
        await self.db.execute(
            "UPDATE users SET last_cache=0 WHERE id=?", (self.user_id,)
        )
        await self.db.commit()

    async def get_api_data(self):
        cursor = await self.db.execute(
            "SELECT quarter, jwtoken, url FROM users WHERE id=?", (self.user_id,)
        )
        quarter, jwtoken, url = await cursor.fetchone()
        return ApiData(quarter, jwtoken, url)

    async def get_api_and_cache_data(self):
        cursor = await self.db.execute(
            "SELECT last_cache, cache_time, quarter, jwtoken, url FROM users WHERE id=?",
            (self.user_id,),
        )
        last_cache, cache_time, quarter, jwtoken, url = await cursor.fetchone()
        return ApiAndCacheData(last_cache, cache_time, ApiData(quarter, jwtoken, url))

    async def get_api_and_schedule_cache_data(self):
        cursor = await self.db.execute(
            "SELECT schedule_last_cache, cache_time, quarter, jwtoken, url FROM users WHERE id=?",
            (self.user_id,),
        )
        last_cache, cache_time, quarter, jwtoken, url = await cursor.fetchone()
        return ApiAndCacheData(last_cache, cache_time, ApiData(quarter, jwtoken, url))

    async def update_cache(self, url: str | None = None):
        if url is None:
            await self.db.execute(
                "UPDATE users SET last_cache=? WHERE id=?", (time.time(), self.user_id)
            )
        else:
            class_id = _class_id_from_url(url)
            await self.db.execute(
                "UPDATE users SET last_cache=?, url=?, class_id=? WHERE id=?",
                (time.time(), url, class_id, self.user_id),
            )
        await self.db.commit()

    async def update_schedule_cache(self, url: str | None = None):
        if url is None:
            await self.db.execute(
                "UPDATE users SET last_schedule_cache=? WHERE id=?",
                (time.time(), self.user_id),
            )
        else:
            class_id = _class_id_from_url(url)
            await self.db.execute(
                "UPDATE users SET last_schedule_cache=?, url=?, class_id=? WHERE id=?",
                (time.time(), url, class_id, self.user_id),
            )
        await self.db.commit()

    async def set_url(self, url: str):
        class_id = _class_id_from_url(url)
        await self.db.execute(
            "UPDATE users SET url=?, class_id=? WHERE id=?",
            (url, class_id, self.user_id),
        )

    async def delete_user(self):
        await self.db.execute("DELETE FROM users WHERE id=?", (self.user_id,))
        await self.db.commit()

    async def set_quarter(self, quarter: str):
        await self.db.execute(
            "UPDATE users SET quarter=? WHERE id=?", (quarter, self.user_id)
        )
        await self.clear_cache()

    async def get_autosend_schedule(self):
        cursor = await self.db.execute(
            "SELECT autosend_schedule_time, autosend_schedule_interval FROM users WHERE id=?",
            (self.user_id,),
        )
        return await cursor.fetchone()

    async def set_autosend_schedule(self, time, interval):
        await self.db.execute(
            "UPDATE users SET autosend_schedule_time=?, autosend_schedule_interval=? WHERE id=?",
            (time, interval, self.user_id),
        )
        await self.db.commit()

    async def get_notify_change_schedule(self):
        cursor = await self.db.execute(
            "SELECT notify_change_schedule FROM users WHERE id=?", (self.user_id,)
        )
        return (await cursor.fetchone())[0]

    async def set_notify_change_schedule(self, notify_change_schedule):
        await self.db.execute(
            "UPDATE users SET notify_change_schedule=? WHERE id=?",
            (notify_change_schedule, self.user_id),
        )
        await self.db.commit()

    async def check_class_id(self, class_id: int | None, need_commit=True):
        if class_id is None:
            cursor = await self.db.execute(
                "SELECT url FROM users WHERE id=?", (self.user_id,)
            )
            (url,) = await cursor.fetchone()
            class_id = _class_id_from_url(url)
            await self.db.execute(
                "UPDATE users SET class_id=? WHERE id=?", (class_id, self.user_id)
            )
            if need_commit:
                await self.db.commit()
        return class_id

    async def get_class_id(self):
        cursor = await self.db.execute(
            "SELECT class_id FROM users WHERE id=?", (self.user_id,)
        )
        (class_id,) = await cursor.fetchone()
        class_id = await self.check_class_id(class_id)
        return class_id

    async def get_class_users_notify_change_schedule(self):
        class_id = await self.get_class_id()
        cursor = await self.db.execute(
            "SELECT id FROM users WHERE class_id=?" "AND notify_change_schedule",
            (class_id,),
        )
        return [i[0] async for i in cursor]
