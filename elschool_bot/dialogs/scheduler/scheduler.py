import datetime
from typing import Callable, Dict, Any, Awaitable

import aioscheduler
from aiogram import BaseMiddleware
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import TelegramObject
from aiogram_dialog import DialogManager, Dialog, Window, BaseDialogManager
from aiogram_dialog.widgets.text import Format

from elschool_bot.dialogs.grades import start_get_grades, process_result, filter_selected, filter_grades, filter_marks, \
    show_default, show_summary, show_detail
from elschool_bot.repository import Repo


class SchedulerShowStates(StatesGroup):
    STATUS = State()


class Scheduler:
    def __init__(self):
        self.aioscheduler = aioscheduler.TimedScheduler()
        self.tasks = {}

    def add_grades_task(self, manager: DialogManager, next_time, id):
        next_time = self.get_next_time(next_time)
        task = self.aioscheduler.schedule(self.show_grades(manager.bg(), id), next_time)
        self.tasks[(manager.event.from_user.id, id)] = task

    def get_next_time(self, next_time):
        hour, minute = [int(i) for i in next_time.split('_')]
        next_time = datetime.datetime.today().replace(hour=hour - 5, minute=minute)
        if next_time <= datetime.datetime.utcnow():
            next_time += datetime.timedelta(days=1)
        return next_time

    def remove_grades_task(self, user_id, id):
        if (user_id, id) in self.tasks:
            del self.tasks[(user_id, id)]

    def add_grades_interval_task(self, manager: DialogManager, next_time, interval, id):
        hour, minute = [int(i) for i in next_time.split('_')]
        next_time = datetime.datetime.today().replace(hour=hour-5, minute=minute)
        if interval == 0:
            next_time += datetime.timedelta(days=1)
        elif interval == 1:
            next_time += datetime.timedelta(days=7)
        else:
            next_month = next_time.month + 1
            if next_month == 13:
                next_month = 1
                next_time = next_time.replace(year=next_time.year+1)
            next_time = next_time.replace(month=next_month)
        task = self.aioscheduler.schedule(self.show_grades(manager.bg(), id), next_time)
        self.tasks[(manager.event.from_user.id, id)] = task

    async def show_grades(self, manager: BaseDialogManager, id):
        await manager.start(SchedulerShowStates.STATUS, {'scheduler': self, 'id': id})

    async def restore_grades_task(self, manager: DialogManager):
        repo = manager.middleware_data['repo']
        schedules = await repo.get_schedules_for_restore()
        for user_id, user_schedules in schedules:
            bg = manager.bg(user_id, user_id)
            for schedule in user_schedules:
                id = schedule['id']
                next_time = self.get_next_time(schedule['next_time'])
                task = self.aioscheduler.schedule(self.show_grades(bg, id), next_time)
                self.tasks[user_id, id] = task



class SchedulerMiddleware(BaseMiddleware):
    def __init__(self, scheduler):
        self.scheduler = scheduler

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        data['scheduler'] = self.scheduler
        await handler(event, data)


async def select_grades(grades, manager: DialogManager):
    user_id = manager.event.from_user.id
    id = manager.start_data['id']
    repo: Repo = manager.middleware_data['repo']
    _, _, _, next_time, interval, show_mode, lessons, _, marks = await repo.get_schedule(user_id, id)

    selected = set()
    if not manager.find('select_all').is_checked():
        selected = manager.find('select_lessons').get_checked()
        lesson_names = list(grades)
        selected = {lesson_names[int(i)] for i in selected}

    marks_selected = {int(mark) for mark in marks.split(',')}
    grades = filter_grades(grades, (filter_selected(selected),), (filter_marks(marks_selected),))
    if show_mode == 0:
        await show_default(grades, manager)
    elif show_mode == 1:
        await show_summary(grades, manager)
    else:
        await show_detail(grades, manager)

    scheduler = manager.start_data['scheduler']
    if interval != -1:
        scheduler.add_grades_interval_task(manager, next_time, interval, id)
    else:
        await repo.remove_schedule(user_id, id)
        scheduler.remove_grades_task(user_id, id)


async def on_start(start_data, manager: DialogManager):
    grades = await start_get_grades(manager)
    if grades:
        await select_grades(grades, manager)


async def on_process_result(start_data, result, manager: DialogManager):
    grades = await process_result(start_data, result, manager)
    if grades:
        await select_grades(grades, manager)


dialog = Dialog(
    Window(Format('{dialog_data[status]}'), state=SchedulerShowStates.STATUS),
    on_start=on_start,
    on_process_result=on_process_result
)
