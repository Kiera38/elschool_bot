import datetime

from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager, StartMode, ShowMode
from aiogram_dialog.widgets.kbd import Button, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.dialogs import input_data
from elschool_bot.repository import RegisterError
from elschool_bot.widgets import grades_select
from elschool_bot.widgets.ru_calendar import RuCalendar
from elschool_bot.windows import select_lessons, status
from .show import ShowStates, show_summary, show_detail, show_default


class GradesStates(StatesGroup):
    SELECT = State()
    SELECT_LESSONS = State()
    SELECT_LESSON_DATE = State()
    SELECT_DATE = State()
    STATUS = State()


async def start_get_grades(manager: DialogManager):
    repo = manager.middleware_data['repo']
    await status.update(manager, 'получаю оценки', ShowMode.EDIT)
    try:
        grades = await repo.get_grades(manager.event.from_user.id)
    except RegisterError as e:
        status_text = manager.dialog_data['status']
        message = e.args[0]
        text = f'{status_text}, произошла ошибка:\n{message}. Скорее всего elschool обновил токен.'
        login, password = await repo.get_user_data(manager.event.from_user.id)
        if login is None and password is None:
            await input_data.start(['логин', 'пароль'], (f'{text} У меня не сохранены твои данные', ''),
                                   manager, check_get_grades=False)
        elif login is None:
            manager.dialog_data.update(password=password)
            await input_data.start(['логин'], (f'{text} У меня не сохранён твой пароль', ''),
                                   manager, check_get_grades=False, value=password)
        elif password is None:
            manager.dialog_data.update(login=login)
            await input_data.start(['пароль'], (f'{text} У меня не сохранён твой логин', ''),
                                   manager, check_get_grades=False, value=login)
        else:
            await status.update(manager, f'{text}. Сейчас обновлю у себя', show_mode=ShowMode.EDIT)
            try:
                jwtoken = await repo.check_register_user(login, password)
            except RegisterError as e:
                status_text = manager.dialog_data['status']
                message = e.args[0]
                if e.login is not None and e.password is not None:
                    message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
                await status.update(manager, f'{status_text}\n{message}')
            else:
                return await update_token(login, password, jwtoken, manager, 'всё')

    else:
        return grades


async def start_select_grades(manager: DialogManager):
    await manager.start(GradesStates.STATUS, mode=StartMode.RESET_STACK)
    grades = await start_get_grades(manager)
    if grades is not None:
        await show_select(grades, manager)


async def update_token(login, password, jwtoken, manager, save_data):
    repo = manager.middleware_data['repo']
    await status.update(manager, 'обновление токена: попытка регистрации', show_mode=ShowMode.EDIT)
    user_id = manager.event.from_user.id

    if save_data == 'всё':
        await repo.update_data(user_id, jwtoken, login, password)
    elif save_data == 'логин':
        await repo.update_data(user_id, jwtoken, login)
    elif save_data == 'пароль':
        await repo.update_data(user_id, jwtoken, password=password)
    else:
        await repo.update_data(user_id, jwtoken)
    await status.update(manager, 'данные введены правильно, теперь попробую получить оценки')
    try:
        grades = await repo.get_grades(user_id)
    except RegisterError as e:
        status_text = manager.dialog_data['status']
        message = e.args[0]
        await status.update(manager, f'{status_text}\n{message}')
    else:
        return grades


async def process_result(start_data, result, manager: DialogManager):
    if not isinstance(start_data, dict):
        return
    input_data = start_data.get('inputs')
    if input_data is None:
        return
    login = result['login']
    password = result['password']
    jwtoken = result['jwtoken']
    if len(input_data) == 2:
        save_data = None
    elif input_data[0] == 'логин':
        save_data = 'пароль'
    else:
        save_data = 'логин'
    return await update_token(login, password, jwtoken, manager, save_data)


async def on_process_result(start_data: dict, result, manager: DialogManager):
    if result == 'change_settings':
        await manager.switch_to(GradesStates.STATUS)
        grades = await start_get_grades(manager)
        if grades is not None:
            await show_select(grades, manager)
        return
    grades = await process_result(start_data, result, manager)
    if grades:
        await show_select(grades, manager)
        return
    grades_select.process_result(result, manager)


async def show_select(grades, manager: DialogManager):
    status.set(
        manager, 'оценки получил, теперь можешь выбрать',
        checked_lessons='', checked_date_lesson='', checked_date='',
        grades=grades, lessons=[{'id': i, 'text': item} for i, item in enumerate(grades)]
    )
    await manager.switch_to(GradesStates.SELECT)
    await manager.show(ShowMode.EDIT)


def filter_grades(grades, filters, value_filters):
    filters = [filt for filt in filters if filt is not None]
    value_filters = [filt for filt in value_filters if filt is not None]

    if not filters and not value_filters:
        return grades

    def default_filter(*args):
        return True

    if not filters:
        filters = [default_filter]
    if not value_filters:
        value_filters = [default_filter]

    filtered_grades = {}
    for key, values in grades.items():
        new_values = []
        for value in values:
            if all(filt(value) for filt in value_filters):
                new_values.append(value)

        if all(filt(key, new_values) for filt in filters):
            filtered_grades[key] = new_values

    return filtered_grades


def filter_selected(selected):
    if not selected:
        return None

    def filt(name, values):
        return name in selected

    return filt


def filter_lesson_date(lesson_date, name):
    if not lesson_date:
        return None

    if 'months' in lesson_date:
        months = [
            'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
            'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
        ]
        months = [months.index(month) + 1 for month in lesson_date['months']]

        def filt_months(value):
            val_lesson_date = value[name]
            day, month, year = val_lesson_date.split('.')
            return int(month) in months

        return filt_months

    start = lesson_date['start']
    end = lesson_date['end']

    def filt_range(value):
        val_lesson_date = value[name]
        day, month, year = val_lesson_date.split('.')
        lesson_date = datetime.date(year, month, day)
        return start <= lesson_date <= end

    return filt_range


def filter_marks(marks_selected):
    def filt(value):
        mark = value['mark']
        return mark in marks_selected

    return filt


def filter_without_marks(disabled=False):
    if disabled:
        return None

    def filt(name, values):
        return values

    return filt


async def on_show(query, button, manager: DialogManager):
    grades = manager.dialog_data['grades']
    marks_selected = {int(mark) for mark in manager.find('marks_selector').get_checked()}

    if grades_select.is_summary_checked(manager):
        await show_summary(grades, manager, marks_selected)
        return

    selected = set()
    is_detail_checked = grades_select.is_detail_checked(manager)
    if not is_detail_checked and not manager.find('select_all').is_checked():
        selected = manager.find('select_lessons').get_checked()
        lesson_names = list(grades)
        selected = {lesson_names[int(i)] for i in selected}

    dates = manager.dialog_data.get('dates')
    lesson_dates = manager.dialog_data.get('lesson_dates')
    show_without_marks = grades_select.is_show_without_marks_checked(manager)

    grades = filter_grades(grades, (filter_selected(selected), filter_without_marks(show_without_marks)),
                           (filter_lesson_date(lesson_dates, 'lesson_date'),
                            filter_lesson_date(dates, 'date'), filter_marks(marks_selected)))

    if is_detail_checked:
        await show_detail(grades, manager)
        return

    await show_default(grades, manager)


async def on_start(data, manager: DialogManager):
    status.set(manager, 'оценки')
    await grades_select.on_start(manager)


async def getter_date(dialog_manager: DialogManager, **kwargs):
    dialog_data = dialog_manager.dialog_data
    if date := dialog_data.get('date'):
        return {'date': f'Выбранная дата {date:%d.%m.%Y}'}
    return {'date': ''}


async def getter_lesson_date(dialog_manager: DialogManager, **kwargs):
    dialog_data = dialog_manager.dialog_data
    if date := dialog_data.get('lesson_date'):
        return {'lesson_date': f'Выбранная дата {date:%d.%m.%Y}'}
    return {'lesson_date': ''}


dialog = Dialog(
    status.create(
        GradesStates.SELECT,
        Button(Const('показать'), 'show', on_click=on_show),
        *grades_select.create(GradesStates.SELECT_LESSONS, True)
    ),
    select_lessons.create(GradesStates.SELECT_LESSONS, GradesStates.SELECT),
    status.create(GradesStates.STATUS),
    on_process_result=on_process_result,
    on_start=on_start
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(show.dialog)
