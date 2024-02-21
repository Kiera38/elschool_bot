import asyncio
import datetime
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import TelegramObject
from aiogram_dialog import DialogManager, Dialog, BaseDialogManager, StartMode

from elschool_bot.dialogs import schedule
from elschool_bot.dialogs.grades import (start_get_grades, process_result, show_default,
                                         filter_marks, filter_selected, filter_without_marks, show_statistics)
from elschool_bot.repository import Repo
from elschool_bot.windows import status


class SchedulerShowStates(StatesGroup):
    STATUS = State()


class Scheduler:
    def __init__(self):
        self.tasks = {}

    def add_id_task(self, manager: DialogManager, next_time, id):
        if next_time is None:
            raise ValueError('не выбрано время отправки')
        delay = self.get_delay(next_time)
        self.add_task(delay, id, manager)

    def add_task(self, delay, id, manager):
        task = asyncio.create_task(self.show_id(manager.bg(stack_id=''), id, delay))
        self.tasks[(manager.event.from_user.id, id)] = task

    def get_delay(self, next_time):
        next_time = self.get_next_time(next_time)
        return self.get_next_time_delay(next_time)

    def get_next_time(self, next_time):
        hour, minute = [int(i) for i in next_time.split('_')]
        next_time = datetime.datetime.today().replace(hour=hour - 5, minute=minute)
        return next_time

    def get_next_time_delay(self, next_time):
        now = datetime.datetime.utcnow()
        if next_time <= now:
            next_time += datetime.timedelta(days=1)
        return (next_time - now).total_seconds()

    def remove_id_task(self, user_id, id):
        if (user_id, id) in self.tasks:
            task = self.tasks.pop((user_id, id))
            task.cancel()

    def add_id_interval_task(self, manager: DialogManager, next_time, interval, id):
        next_time = self.get_next_time(next_time)
        if interval == 0:
            next_time += datetime.timedelta(days=1)
        elif interval == 1:
            next_time += datetime.timedelta(days=7)
        else:
            next_month = next_time.month + 1
            if next_month == 13:
                next_month = 1
                next_time = next_time.replace(year=next_time.year + 1)
            next_time = next_time.replace(month=next_month)
        delay = self.get_next_time_delay(next_time)
        self.add_task(delay, id, manager)

    async def show_id(self, manager: BaseDialogManager, id, delay):
        await asyncio.sleep(delay)
        await manager.start(SchedulerShowStates.STATUS, {'notifications': self, 'id': id}, StartMode.NEW_STACK)

    async def restore_id_task(self, manager: DialogManager):
        repo = manager.middleware_data['repo']
        schedules = await repo.get_schedules_for_restore()
        for user_id, user_schedules in schedules.items():
            bg = manager.bg(user_id, user_id, stack_id='')
            for schedule in user_schedules:
                id = schedule['id']
                delay = self.get_delay(schedule['next_time'])
                task = asyncio.create_task(self.show_id(bg, id, delay))
                self.tasks[(user_id, id)] = task


class SchedulerMiddleware(BaseMiddleware):
    def __init__(self, scheduler):
        self.scheduler = scheduler

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        data['notifications'] = self.scheduler
        await handler(event, data)


def filter_mark_date(date):
    if date is None:
        return None

    now = datetime.date.today()

    if date == 0:
        def filt(value):
            day, month, year = value['date'].split('.')
            return now == datetime.date(int(year), int(month), int(day))
        return filt

    if date == 1:
        def filt(value):
            day, month, year = value['date'].split('.')
            return now.weekday() == datetime.date(int(year), int(month), int(day)).weekday()
        return filt

    if date == 2:
        def filt(value):
            day, month, year = value['date'].split('.')
            return now.month == int(month) and now.year == int(year)
        return filt


async def select_grades(grades, manager: DialogManager):
    user_id = manager.event.from_user.id
    id = manager.start_data['id']
    scheduler = manager.start_data['notifications']
    repo: Repo = manager.middleware_data['repo']
    _, _, _, next_time, interval, show_mode, lessons, date, marks, show_without_marks = await repo.get_schedule(user_id, id)

    marks_selected = {int(mark) for mark in marks.split(',')}
    filters = (filter_without_marks(show_without_marks),)
    if show_mode != 0 and lessons != 'all':
        selected = lessons.split(',')
        filters += (filter_selected(selected),)

    value_filters = filter_marks(marks_selected), filter_mark_date(date)
    if show_mode == 0:
        await show_default(grades, manager, filters, value_filters, False)
    else:
        await show_statistics(grades, manager, marks_selected, filters, value_filters, False)

    if interval != -1:
        scheduler.add_id_interval_task(manager, next_time, interval, id)
    else:
        await repo.remove_schedule(user_id, id)
        scheduler.remove_id_task(user_id, id)


async def show_schedule(manager: DialogManager):
    date = datetime.date.today() + datetime.timedelta(days=1)
    await schedule.start_date(manager, date)

    repo = manager.middleware_data['repo']
    user_id = manager.event.from_user.id
    time, interval = await repo.get_user_autosend_schedule(user_id)
    scheduler = manager.start_data['notifications']

    if interval != -1:
        scheduler.add_id_interval_task(manager, time, interval, -1)
    else:
        await repo.set_user_autosend_schedule(user_id, None, -1)
        scheduler.remove_id_task(user_id, -1)


async def on_start(start_data, manager: DialogManager):
    if start_data['id'] == -1:
        await show_schedule(manager)
        return

    grades = await start_get_grades(manager)
    if grades:
        await select_grades(grades, manager)


async def on_process_result(start_data, result, manager: DialogManager):
    grades = await process_result(start_data, result, manager)
    if grades:
        await select_grades(grades, manager)


dialog = Dialog(
    status.create(SchedulerShowStates.STATUS),
    on_start=on_start,
    on_process_result=on_process_result
)
