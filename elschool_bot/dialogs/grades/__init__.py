import datetime
from typing import Dict

from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, Checkbox, Row, Calendar, CalendarScope, Multiselect, SwitchTo, Group
from aiogram_dialog.widgets.kbd.calendar_kbd import CalendarScopeView, CalendarDaysView, CalendarMonthView, \
    CalendarYearsView
from aiogram_dialog.widgets.text import Const, Format, Text

from .show import ShowStates, show_summary, show_detail, show_default
from elschool_bot.dialogs.input_data import start_register
from elschool_bot.repository import RegisterError


class GradesStates(StatesGroup):
    SELECT = State()
    SELECT_LESSONS = State()
    SELECT_LESSON_DATE = State()
    SELECT_DATE = State()
    STATUS = State()


async def start_get_grades(manager: DialogManager):
    repo = manager.middleware_data['repo']
    await manager.update({'status': 'получаю оценки'})
    try:
        grades = await repo.get_grades(manager.event.from_user.id)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        login, password = await repo.get_user_data(manager.event.from_user.id)
        text = f'{status}, произошла ошибка:\n{message}. Скорее всего elschool обновил токен.'
        if login is None and password is None:
            await start_register(['логин', 'пароль'], (f'{text} У меня не сохранены твои данные', ''),
                                 manager, check_get_grades=False)
        elif login is None:
            manager.dialog_data.update(password=password)
            await start_register(['логин'], (f'{text} У меня не сохранён твой пароль', ''),
                                 manager, check_get_grades=False, value=password)
        elif password is None:
            manager.dialog_data.update(login=login)
            await start_register(['пароль'], (f'{text} У меня не сохранён твой логин', ''),
                                 manager, check_get_grades=False, value=login)
        else:
            await manager.update({'status': f'{text}. Сейчас обновлю у себя'})
            try:
                jwtoken = await repo.check_register_user(login, password)
            except RegisterError as e:
                status = manager.dialog_data['status']
                message = e.args[0]
                if e.login is not None and e.password is not None:
                    message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
                await manager.update({'text': f'{status}\n{message}'})
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
    await manager.update({'status': 'обновление токена: попытка регистрации'})
    user_id = manager.event.from_user.id

    if save_data == 'всё':
        await repo.update_data(user_id, jwtoken, login, password)
    elif save_data == 'логин':
        await repo.update_data(user_id, jwtoken, login)
    elif save_data == 'пароль':
        await repo.update_data(user_id, jwtoken, password=password)
    else:
        await repo.update_data(user_id, jwtoken)
    await manager.update({'status': 'данные введены правильно, теперь попробую получить оценки'})
    try:
        grades = await repo.get_grades(user_id)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        await manager.update({'text': f'{status}\n{message}'})
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
    grades = await process_result(start_data, result, manager)
    if grades:
        await show_select(grades, manager)


async def show_select(grades, manager):
    manager.dialog_data.update(
        status='оценки получил, теперь можешь выбрать',
        checked_lessons='',
        checked_date_lesson='',
        checked_date='',
        grades=grades,
        lessons=[{'id': i, 'text': item} for i, item in enumerate(grades)]
    )
    await manager.switch_to(GradesStates.SELECT)
    await manager.show()


async def on_select_lesson_date(event, widget, manager: DialogManager, date: datetime.date):
    manager.dialog_data['lesson_date'] = date
    await manager.switch_to(GradesStates.SELECT)


async def on_select_date(event, widget, manager: DialogManager, date: datetime.date):
    manager.dialog_data['date'] = date
    await manager.switch_to(GradesStates.SELECT)


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

    # filtered_grades = {}
    # for key, values in grades.items():
    #     if all(filt(key, values) for filt in filters):
    #         new_values = []
    #         for value in values:
    #             if all(filt(value) for filt in value_filters):
    #                 new_values.append(value)
    #         filtered_grades[key] = new_values
    #
    # return filtered_grades
    return {key: [value for value in values
                  if all(filt(value) for filt in value_filters)]
            for key, values in grades.items()
            if all(filt(key, values) for filt in filters)}


def filter_selected(selected):
    if not selected:
        return None

    def filt(name, values):
        return name in selected

    return filt


def filter_lesson_date(lesson_date):
    if not lesson_date:
        return None

    def filt(value):
        val_lesson_date = value['lesson_date']
        day, month, year = val_lesson_date.split('.')
        return int(year) == lesson_date.year and int(month) == lesson_date.month and int(day) == lesson_date.day

    return filt


def filter_date(date):
    if not date:
        return None

    def filt(value):
        val_date = value['date']
        day, month, year = val_date.split('.')
        return int(year) == date.year and int(month) == date.month and int(day) == date.day

    return filt


def filter_marks(marks_selected):
    if marks_selected == {5, 4, 3, 2}:
        return None

    def filt(value):
        mark = value['mark']
        return mark in marks_selected

    return filt


async def on_show(query, button, manager: DialogManager):
    grades = manager.dialog_data['grades']
    marks_selected = {int(mark) for mark in manager.find('marks_selector').get_checked()}

    if manager.find('summary').is_checked():
        grades = filter_grades(grades, (), (filter_marks(marks_selected),))
        await show_summary(grades, manager)
        return

    selected = set()
    if not manager.find('select_all').is_checked():
        selected = manager.find('select_lessons').get_checked()
        lesson_names = list(grades)
        selected = {lesson_names[int(i)] for i in selected}

    date = manager.dialog_data.get('date')
    lesson_date = manager.dialog_data.get('lesson_date')

    grades = filter_grades(grades, (filter_selected(selected),),
                           (filter_lesson_date(lesson_date), filter_date(date), filter_marks(marks_selected)))

    if manager.find('detail').is_checked():
        await show_detail(grades, manager)
        return

    await show_default(grades, manager)


async def on_selected_lessons_changed(event, select, manager: DialogManager, item_id):
    if select.is_checked(item_id):
        await manager.find('select_all').set_checked(False)


async def on_del_lesson_date(query, button, manager: DialogManager):
    manager.dialog_data.pop('lesson_date', None)
    await manager.switch_to(GradesStates.SELECT)


async def on_del_date(query, button, manager: DialogManager):
    manager.dialog_data.pop('date', None)
    await manager.switch_to(GradesStates.SELECT)


async def on_select_all(event, checkbox, manager: DialogManager):
    if checkbox.is_checked():
        select_lessons = manager.find('select_lessons')
        await select_lessons.reset_checked()


async def on_start(data, manager: DialogManager):
    manager.dialog_data['status'] = 'оценки'
    marks = manager.find('marks_selector')
    for i in range(2, 6):
        await marks.set_checked(str(i), True)


class WeekDay(Text):
    async def _render_text(self, data, manager: DialogManager) -> str:
        selected_date: datetime.date = data["date"]
        return ('пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс')[selected_date.weekday()]


class Month(Text):
    async def _render_text(self, data, manager: DialogManager) -> str:
        selected_date: datetime.date = data["date"]
        return ('январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль',
                'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь')[selected_date.month - 1]


class RuCalendar(Calendar):
    def _init_views(self) -> Dict[CalendarScope, CalendarScopeView]:
        return {
            CalendarScope.DAYS: CalendarDaysView(self._item_callback_data, self.config,
                                                 weekday_text=WeekDay(),
                                                 header_text=Month() + Format('{date: %Y}'),
                                                 prev_month_text='<<' + Month(),
                                                 next_month_text=Month() + '>>'),
            CalendarScope.MONTHS: CalendarMonthView(self._item_callback_data, self.config,
                                                    month_text=Month(),
                                                    this_month_text='[' + Month() + ']'),
            CalendarScope.YEARS: CalendarYearsView(self._item_callback_data, self.config)
        }


dialog = Dialog(
    Window(
        Format('{dialog_data[status]}'),
        Button(Const('показать'), 'show', on_click=on_show),
        Row(
            Checkbox(Const('✓ кратко'), Const('кратко'), 'summary'),
            Checkbox(Const('✓ подробно'), Const('подробно'), 'detail')
        ),
        SwitchTo(
            Format('выбрать из списка'),
            'lessons_picked',
            GradesStates.SELECT_LESSONS,
            when=lambda data, widget, manager: not manager.find('summary').is_checked()
        ),
        Row(
            SwitchTo(
                Format('{dialog_data[checked_date_lesson]} дата урока'),
                'date_lesson',
                GradesStates.SELECT_LESSON_DATE
            ),
            SwitchTo(
                Format('{dialog_data[checked_date]} дата проставления'),
                'date',
                GradesStates.SELECT_DATE
            ),
            when=lambda data, widget, manager: not manager.find('summary').is_checked()
        ),
        Multiselect(
            Format('✓ {item}'),
            Format('{item}'),
            'marks_selector',
            lambda item: item,
            (5, 4, 3, 2)
        ),
        state=GradesStates.SELECT
    ),
    Window(
        Const('выбери уроки'),
        Checkbox(
            Format('✓ все'),
            Format('все'),
            'select_all',
            default=True,
            on_state_changed=on_select_all
        ),
        Group(
            Multiselect(
                Format('✓ {item[text]}'),
                Format('{item[text]}'),
                'select_lessons',
                lambda item: item['id'],
                F['dialog_data']['lessons'],
                on_state_changed=on_selected_lessons_changed
            ),
            width=2
        ),
        SwitchTo(Const('назад'), '', GradesStates.SELECT),
        state=GradesStates.SELECT_LESSONS
    ),
    Window(
        Const('выбери дату урока. Можно выбрать 1 дату. Выбранная дата не отображается.'),
        RuCalendar('lesson_date_calendar', on_click=on_select_lesson_date),
        Button(Const('сбросить'), 'del_lesson_date', on_del_lesson_date),
        SwitchTo(Const('назад'), '', GradesStates.SELECT),
        state=GradesStates.SELECT_LESSON_DATE
    ),
    Window(
        Const('выбери дату проставления оценки. Можно выбрать 1 дату. Выбранная дата не отображается.'),
        RuCalendar('date_calendar', on_click=on_select_date),
        Button(Const('сбросить'), 'del_lesson_date', on_del_date),
        SwitchTo(Const('назад'), '', GradesStates.SELECT),
        state=GradesStates.SELECT_DATE
    ),
    Window(Format('{dialog_data[status]}'), state=GradesStates.STATUS),
    on_process_result=on_process_result,
    on_start=on_start
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(show.dialog)
