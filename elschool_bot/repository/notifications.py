import logging
from dataclasses import dataclass

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    name: str
    next_time: int
    interval: int
    show_mode: int
    lessons: str
    dates: str
    marks: str
    show_without_marks: bool


@dataclass
class NotificationName:
    id: str
    name: str


@dataclass
class NotificationWithId:
    notification: Notification
    id: int
    user_id: int


@dataclass
class NotificationForRestore:
    id: int
    next_time: int


class NotificationsRepo:
    def __init__(self, connection: aiosqlite.Connection):
        self.db = connection

    async def add_notification(self, user_id: int, notification: Notification):
        async with self.db.cursor() as cursor:
            await cursor.execute("SELECT id FROM schedules WHERE user_id=?", (user_id,))
            ids = {id[0] async for id in cursor}
            max_id = max(ids) if ids else 0
            id = 1
            for id in range(1, max_id + 2):
                if id not in ids:
                    break
            if not notification.name or notification.name == "None":
                notification.name = f"отправка {id}"
            logger.info(
                f"пользователь с id {user_id} сохранил отправку с id {id} и названием {notification.name}, "
                f"которая покажет оценки в {notification.next_time} с повторениями {notification.interval}"
            )
            await cursor.execute(
                "INSERT INTO schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    id,
                    notification.name,
                    notification.next_time,
                    notification.interval,
                    notification.show_mode,
                    notification.lessons,
                    notification.dates,
                    notification.marks,
                    notification.show_without_marks,
                ),
            )
        await self.db.commit()
        return id

    async def update_notification(
        self, user_id: int, notification_id: int, notification: Notification
    ):
        logger.info(
            f"пользователь с id {user_id} изменил отправку с названием {notification.name}, "
            f"которая покажет оценки в {notification.next_time} с повторениями {notification.interval}"
        )
        await self.db.execute(
            "UPDATE schedules SET name=?, next_time=?, interval=?, show_mode=?, "
            "lessons=?, dates=?, marks=?, show_without_marks=? WHERE user_id=? AND id=?",
            (
                notification.name,
                notification.next_time,
                notification.interval,
                notification.show_mode,
                notification.lessons,
                notification.dates,
                notification.marks,
                notification.show_without_marks,
                user_id,
                notification_id,
            ),
        )
        await self.db.commit()

    async def names(self, user_id: int):
        cursor = await self.db.execute(
            "SELECT id, name FROM schedules WHERE user_id=?", (user_id,)
        )
        return [NotificationName(*row) async for row in cursor]

    async def delete_notification(self, user_id: int, notification_id: int):
        logger.info(
            f"пользователь с id {user_id} удалил отправку с id {notification_id}"
        )
        await self.db.execute(
            "DELETE FROM schedules WHERE user_id=? AND id=?", (user_id, notification_id)
        )
        await self.db.commit()

    async def get_notification(self, user_id: int, notification_id: int):
        cursor = await self.db.execute(
            "SELECT * FROM schedules WHERE user_id=? AND id=?",
            (user_id, notification_id),
        )
        return await cursor.fetchone()

    async def get_notifications_for_restore(self):
        cursor = await self.db.execute("SELECT user_id, id, next_time FROM schedules")
        schedules = {}
        async for user_id, id, next_time in cursor:
            if user_id not in schedules:
                schedules[user_id] = []
            schedules[user_id].append(NotificationForRestore(id, next_time))

        cursor = await self.db.execute(
            "SELECT id, autosend_schedule_time FROM users WHERE autosend_schedule_time!=NULL"
        )
        async for user_id, time in cursor:
            if user_id not in schedules:
                schedules[user_id] = []
            schedules[user_id].append(NotificationForRestore(-1, time))
        return schedules
