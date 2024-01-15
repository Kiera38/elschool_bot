import datetime

from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.text import Format, Const, List, Multi

from elschool_bot.dialogs import grades
from elschool_bot.repository import Repo, RegisterError
from elschool_bot.widgets.ru_calendar import RuCalendar
from elschool_bot.windows import status


class ScheduleStates(StatesGroup):
    SELECT_DAY = State()
    STATUS = State()
    SHOW = State()
    SHOW_TIME_SCHEDULE = State()


async def start(manager: DialogManager):
    await manager.start(ScheduleStates.SELECT_DAY)


async def start_time_schedule(manager: DialogManager):
    await manager.start(ScheduleStates.STATUS, 'time')


async def on_select_day(event, calendar, manager: DialogManager, date):
    repo: Repo = manager.middleware_data['repo']
    await manager.switch_to(ScheduleStates.STATUS)
    schedule = await get_schedule(manager, repo, date)
    if schedule:
        await show_schedule(manager, schedule)


def as_datetime(time):
    hour, minute = time.split(':')
    return ((datetime.datetime.utcnow() + datetime.timedelta(hours=5))
            .replace(hour=int(hour), minute=int(minute), second=0, microsecond=0))


async def show_schedule(manager: DialogManager, schedule):
    lessons = [{'number': number, 'name': name, **lesson} for (number, name), lesson in schedule.items()]
    manager.dialog_data['lessons'] = lessons
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


async def get_schedule_after_error(manager, repo, date):
    try:
        schedule = await repo.get_schedule(manager.event.from_user.id, date)
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
    except RegisterError as e:
        if await grades.handle_register_error(manager, repo, e):
            return await get_schedule_after_error(manager, repo, date)
    else:
        return schedule


async def on_process_result(start_data, result, manager):
    if grades.process_results_without_grades(start_data, result, manager):
        repo = manager.middleware_data['repo']
        date = manager.dialog_data['date']
        schedule = await get_schedule_after_error(manager, repo, date)
        if schedule:
            await show_schedule(manager, schedule)


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
        schedule = await get_schedule(manager, repo, date)
        if schedule:
            await show_schedule(manager, schedule)


dialog = Dialog(
    Window(
        Const('выбери день'),
        RuCalendar('date_selector', on_click=on_select_day),
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
    on_process_result=on_process_result,
    on_start=on_start
)
