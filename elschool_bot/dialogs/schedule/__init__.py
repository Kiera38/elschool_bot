import datetime

from aiogram import F, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import ChatEvent, Dialog, Window, DialogManager, BaseDialogManager, StartMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Format, Const, List, Multi
from aiogram_dialog.widgets.kbd import ManagedCalendar, Button, Select, SwitchTo, Group, Checkbox, Row, Column

from elschool_bot.dialogs import grades
from elschool_bot.repository import Repo, RegisterError
from elschool_bot.widgets.ru_calendar import RuCalendar
from elschool_bot.windows import status
from . import edit
from ..grades.show import fix_text, mean_mark


class ScheduleStates(StatesGroup):
    SELECT_DAY = State()
    STATUS = State()
    SHOW = State()
    SHOW_TIME_SCHEDULE = State()
    SELECT_DEFAULT_EDIT_DAY = State()
    SELECT_LESSON_HOMEWORK = State()
    INPUT_LESSON_HOMEWORK = State()


async def start(manager: DialogManager):
    await manager.start(ScheduleStates.SELECT_DAY)


async def start_time_schedule(manager: DialogManager):
    await manager.start(ScheduleStates.STATUS, 'time')


async def start_input_homework(manager: DialogManager):
    await manager.start(ScheduleStates.STATUS, 'homework')


async def start_date(manager: DialogManager, date):
    await manager.start(ScheduleStates.STATUS, {'type': 'date', 'date': date})


async def start_schedule(manager: BaseDialogManager, schedule, day):
    await manager.start(ScheduleStates.STATUS, {'type': 'schedule', 'schedule': schedule, 'day': day},
                        mode=StartMode.NEW_STACK)


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


def save_lessons(schedule, manager: DialogManager):
    lessons = list(schedule.values())
    lessons.sort(key=lambda item: item['number'])
    manager.dialog_data['lessons'] = lessons
    manager.dialog_data['schedule'] = schedule
    return lessons


async def show_schedule(manager: DialogManager, schedule):
    lessons = save_lessons(schedule, manager)
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
    elif manager.dialog_data.get('homework'):
        await manager.switch_to(ScheduleStates.SELECT_LESSON_HOMEWORK)
    else:
        await manager.switch_to(ScheduleStates.SHOW)


async def get_schedule_after_error(manager, repo: Repo, date):
    try:
        schedule = await repo.get_diaries(manager.event.from_user.id, date)
        if not await check_schedule(schedule, manager):
            return None
    except RegisterError as e:
        status_text = manager.dialog_data['status']
        message = e.args[0]
        await status.update(manager, f'{status_text}\n{message}')
    else:
        return schedule


async def check_schedule(schedule, manager):
    if schedule is None:
        await status.update(manager, 'не найдено расписание на этот день')
        return False
    if isinstance(schedule, str):
        await status.update(manager, schedule)
        return False
    return True


async def get_schedule(manager: DialogManager, repo: Repo, date):
    try:
        manager.dialog_data['day'] = date
        schedule = await repo.get_diaries(manager.event.from_user.id, date)
        if not await check_schedule(schedule, manager):
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
        date = manager.dialog_data['day']
        if manager.dialog_data.get('marks'):
            marks = await get_marks_after_error(manager, repo, manager.event.from_user.id)
            if marks:
                await show_marks(marks, manager)
            return
        schedule = await get_schedule_after_error(manager, repo, date)
        if schedule:
            if manager.dialog_data.get('default_edit'):
                weekday = date.isocalendar()[2]
                await edit.start(schedule, weekday, manager)
            else:
                await show_schedule(manager, schedule)
    elif manager.dialog_data.get('default_edit'):
        await manager.switch_to(ScheduleStates.SELECT_DAY)
    elif result != 'cancel':
        save_lessons(result, manager)
        user_id = manager.event.from_user.id
        repo = manager.middleware_data['repo']
        await notify_users(manager, repo, user_id)


async def notify_users(manager, repo, user_id):
    class_users = await repo.get_class_users_notify_change_schedule(user_id)
    schedule = manager.dialog_data['schedule']
    day = manager.dialog_data['day']
    for user in class_users:
        await start_schedule(manager.bg(user, user, ''), schedule, day)


async def on_edit(event, button, manager: DialogManager):
    manager.dialog_data['has_marks'] = False
    await edit.start(manager.dialog_data['schedule'].copy(), manager.dialog_data['day'], manager)


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
    if isinstance(data, dict):
        if data['type'] == 'date':
            manager.dialog_data['date'] = True
            repo: Repo = manager.middleware_data['repo']
            date = data['date']
            await manager.switch_to(ScheduleStates.STATUS)
            schedule = await get_schedule(manager, repo, date)
            if schedule:
                await show_schedule(manager, schedule)
        elif data['type'] == 'schedule':
            manager.dialog_data['day'] = data['day']
            await show_schedule(manager, data['schedule'])

    if data in ('time', 'homework'):
        manager.dialog_data[data] = True
        repo: Repo = manager.middleware_data['repo']
        date = datetime.date.today()
        await manager.switch_to(ScheduleStates.STATUS)
        schedule = await get_schedule(manager, repo, date)
        if schedule:
            await show_schedule(manager, schedule)


async def get_marks(manager, repo, user_id):
    try:
        marks = await repo.get_grades(user_id)
    except RegisterError as e:
        status.set(manager, 'получение оценок')
        if await grades.handle_register_error(manager, repo, e):
            return await get_marks_after_error(manager, repo, user_id)
    else:
        return marks


async def get_marks_after_error(manager, repo, user_id):
    try:
        marks = await repo.get_grades(user_id)
    except RegisterError as e:
        status_text = manager.dialog_data['status']
        message = e.args[0]
        await status.update(manager, f'{status_text}\n{message}')
    else:
        return marks


async def on_marks(event, checkbox, manager: DialogManager):
    if checkbox.is_checked() and not manager.dialog_data.get('has_marks'):
        repo: Repo = manager.middleware_data['repo']
        await manager.switch_to(ScheduleStates.STATUS)
        status.set(manager, 'получение оценок', marks=True)
        grades = await get_marks(manager, repo, event.from_user.id)
        if grades:
            await show_marks(grades, manager)


async def show_marks(grades, manager):
    del manager.dialog_data['marks']
    for lesson in manager.dialog_data['lessons']:
        marks = grades[lesson['name']]
        mean = mean_mark(marks)
        if mean == 0:
            lesson['marks'] = 'нет'
            lesson['fix'] = ''
        else:
            lesson['marks'] = ', '.join(str(mark['mark']) for mark in marks)
            lesson['fix'] = fix_text(marks, mean)
    manager.dialog_data['has_marks'] = True
    await manager.switch_to(ScheduleStates.SHOW)


def need_marks(data, widget, manager: DialogManager):
    return manager.find('marks').is_checked()


async def on_select_homework_lesson(event, select, manager: DialogManager, item):
    manager.dialog_data['selected_lesson'] = manager.dialog_data['schedule'][int(item)]['name']
    await manager.switch_to(ScheduleStates.INPUT_LESSON_HOMEWORK)


async def on_input_homework(event, text_input, manager: DialogManager, text):
    repo: Repo = manager.middleware_data['repo']
    lesson = manager.dialog_data['selected_lesson']
    day = await repo.save_homework(event.from_user.id, lesson, text)
    if day:
        manager.dialog_data['status'] = f'домашнее задание сохранено на {day: %d.%m.%Y}'
    else:
        manager.dialog_data['status'] = (f'не найден день, когда урок {lesson} будет в следующий раз. '
                                         f'Можешь попробовать сам найти')
    await manager.switch_to(ScheduleStates.STATUS)


dialog = Dialog(
    Window(
        Const('выбери день'),
        RuCalendar('date_selector', on_click=on_select_day),
        SwitchTo(Const('стандартные изменения'), 'default_edit', ScheduleStates.SELECT_DEFAULT_EDIT_DAY),
        state=ScheduleStates.SELECT_DAY),
    Window(Format('{status}'), state=ScheduleStates.STATUS, getter=getter),
    Window(
        Format('расписание на {dialog_data[day]: %d.%m.%Y}'),
        List(
            Multi(
                Format('{item[number]}. {item[name]}'),
                Format('{item[start_time]} - {item[end_time]}'),
                Const('домашнее задание:', when=F['item']['homework']),
                Format('{item[homework]}', when=F['item']['homework']),
                Format('оценки {item[marks]}{item[fix]}', when=need_marks),
            ),
            items=F['dialog_data']['lessons'],
            sep='\n\n'
        ),
        Button(Const('изменения в расписании'), 'edit', on_click=on_edit),
        Row(
            Checkbox(Const('✓ оценки'), Const('оценки'), 'marks', on_state_changed=on_marks),
            SwitchTo(Const('другой день'), 'change_day', ScheduleStates.SELECT_DAY),
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
    Window(
        Const('выбери урок, для которого хочешь записать домашнее задание'),
        Column(
            Select(
                Format('{item[number]}. {item[name]}'),
                'homework_lessons',
                lambda item: item['number'],
                F['dialog_data']['lessons'],
                on_click=on_select_homework_lesson
            ),
        ),
        state=ScheduleStates.SELECT_LESSON_HOMEWORK
    ),
    Window(
        Format('введи домашку для урока {dialog_data[selected_lesson]}'),
        TextInput('input_homework', on_success=on_input_homework),
        state=ScheduleStates.INPUT_LESSON_HOMEWORK
    ),
    on_process_result=on_process_result,
    on_start=on_start
)


def register_handlers(router: Router):
    router.include_router(dialog)
    router.include_router(edit.dialog)
