import datetime

from aiogram import F, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import ChatEvent, Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Format, Const, List, Multi
from aiogram_dialog.widgets.kbd import ManagedCalendar, Button, Select, SwitchTo, Group

from elschool_bot.dialogs import grades
from elschool_bot.repository import Repo, RegisterError
from elschool_bot.widgets.ru_calendar import RuCalendar
from elschool_bot.windows import status
from . import edit


class ScheduleStates(StatesGroup):
    SELECT_DAY = State()
    STATUS = State()
    SHOW = State()
    SHOW_TIME_SCHEDULE = State()
    SELECT_DEFAULT_EDIT_DAY = State()


async def start(manager: DialogManager):
    await manager.start(ScheduleStates.SELECT_DAY)


async def start_time_schedule(manager: DialogManager):
    await manager.start(ScheduleStates.STATUS, 'time')


async def on_select_day(event: ChatEvent, widget: ManagedCalendar, manager: DialogManager, date):
    repo: Repo = manager.middleware_data['repo']
    await manager.switch_to(ScheduleStates.STATUS)
    await manager.show()
    schedule = await get_schedule(manager, repo, date)
    if schedule:
        await show_schedule(manager, schedule)


def as_datetime(time):
    hour, minute = time.split(':')
    return ((datetime.datetime.utcnow() + datetime.timedelta(hours=5))
            .replace(hour=int(hour), minute=int(minute), second=0, microsecond=0))


async def show_schedule(manager: DialogManager, schedule):
    lessons = manager.dialog_data['lessons'] = list(schedule.values())
    manager.dialog_data['schedule'] = schedule
    if manager.dialog_data.get('time'):
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=5)
        end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = as_datetime(lessons[0]['start_time'])
        if end_time < now < start_time:
            current = 'сейчас пока нет уроков, следующий в ' + lessons[0]['start_time']
        else:
            for lesson in lessons:
                start_time = as_datetime(lesson['start_time'])
                number = lesson['number']
                name = lesson['name']
                if end_time < now < start_time:
                    current = f'сейчас перемена, следующий урок будет {number}. {name} в {lesson["start_time"]}'
                    break
                end_time = as_datetime(lesson['end_time'])
                if start_time < now < end_time:
                    current = f'сейчас идёт урок {number}. {name}. Он закончится в {lesson["end_time"]}'
                    break
            else:
                if now > end_time:
                    current = 'все уроки закончились. Может ты дома?'
                else:
                    current = ('я вроде все ситуации учитываю, но эту чего-то не знаю. '
                               'Когда она произошла? Это будет полезная информация для разработчика.')
        manager.dialog_data['current'] = current
        await manager.switch_to(ScheduleStates.SHOW_TIME_SCHEDULE)
    else:
        await manager.switch_to(ScheduleStates.SHOW)


async def get_schedule_after_error(manager, repo: Repo, date):
    try:
        schedule = await repo.get_diaries(manager.event.from_user.id, date)
        if isinstance(schedule, str):
            await status.update(manager, schedule)
            return None
    except RegisterError as e:
        status_text = manager.dialog_data['status']
        message = e.args[0]
        await status.update(manager, f'{status_text}\n{message}')
    else:
        return schedule


async def get_schedule(manager: DialogManager, repo: Repo, date):
    try:
        manager.dialog_data['date'] = date
        schedule = await repo.get_diaries(manager.event.from_user.id, date)
        if isinstance(schedule, str):
            await status.update(manager, schedule)
            return None
    except RegisterError as e:
        status.set(manager, 'получение расписания')
        if await grades.handle_register_error(manager, repo, e):
            return await get_schedule_after_error(manager, repo, date)
    else:
        return schedule


async def on_process_result(start_data, result, manager: DialogManager):
    if await grades.process_results_without_grades(start_data, result, manager):
        repo = manager.middleware_data['repo']
        date = manager.dialog_data['date']
        schedule = await get_schedule_after_error(manager, repo, date)
        if schedule:
            if manager.dialog_data['default_edit']:
                weekday = date.isocalendar()[2]
                await edit.start(schedule, weekday, manager)
            else:
                await show_schedule(manager, schedule)
    else:
        await manager.switch_to(ScheduleStates.SELECT_DAY)


async def on_edit(event, button, manager: DialogManager):
    await edit.start(manager.dialog_data['schedule'], manager.dialog_data['date'], manager)


async def on_default_edit(event, select, manager: DialogManager, item):
    weekday = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница'].index(item) + 1
    await manager.switch_to(ScheduleStates.STATUS)
    await manager.show()
    repo = manager.middleware_data['repo']
    today = datetime.date.today()
    today_weekday = today.isocalendar()[2]
    date = today - datetime.timedelta(days=today_weekday - weekday)
    manager.dialog_data['default_edit'] = True
    schedule = await get_schedule(manager, repo, date)
    if schedule:
        await edit.start(schedule, weekday, manager)


async def getter(dialog_manager, **kwargs):
    status = dialog_manager.dialog_data.get('status')
    if status:
        return {'status': status}
    return {'status': 'получение расписания'}


async def on_start(data, manager: DialogManager):
    if data == 'time':
        manager.dialog_data['time'] = True
        repo: Repo = manager.middleware_data['repo']
        date = datetime.date.today()
        await manager.switch_to(ScheduleStates.STATUS)
        schedule = await get_schedule(manager, repo, date)
        if schedule:
            await show_schedule(manager, schedule)


dialog = Dialog(
    Window(
        Const('выбери день'),
        RuCalendar('date_selector', on_click=on_select_day),
        SwitchTo(Const('стандартные изменения'), 'default_edit', ScheduleStates.SELECT_DEFAULT_EDIT_DAY),
        state=ScheduleStates.SELECT_DAY),
    Window(Format('{status}'), state=ScheduleStates.STATUS, getter=getter),
    Window(
        List(
            Multi(
                Format('{item[number]}. {item[name]}'),
                Format('{item[start_time]} - {item[end_time]}'),
                Const('домашнее задание:', when=F['item']['homework']),
                Format('{item[homework]}', when=F['item']['homework']),
            ),
            items=F['dialog_data']['lessons'],
            sep='\n\n'
        ),
        Button(Const('изменения в расписании'), 'edit', on_click=on_edit),
        SwitchTo(Const('другой день'), 'change_day', ScheduleStates.SELECT_DAY),
        state=ScheduleStates.SHOW
    ),
    Window(
        Format('{dialog_data[current]}'),
        List(
            Format('{item[number]}. {item[start_time]} - {item[end_time]}'),
            items=F['dialog_data']['lessons']
        ),
        state=ScheduleStates.SHOW_TIME_SCHEDULE
    ),
    Window(
        Const('выбери день, для которого хочешь указать изменения'),
        Group(
            Select(Format('{item}'), 'weekday_selector', lambda item: item,
                   ['понедельник', 'вторник', 'среда', 'четверг', 'пятница'],
                   on_click=on_default_edit),
            width=3
        ),
        state=ScheduleStates.SELECT_DEFAULT_EDIT_DAY
    ),
    on_process_result=on_process_result,
    on_start=on_start
)


def register_handlers(router: Router):
    router.include_router(dialog)
    router.include_router(edit.dialog)
