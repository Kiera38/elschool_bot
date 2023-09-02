import datetime
from typing import Dict

from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Checkbox, Row, Calendar, CalendarScope, Back, Multiselect, SwitchTo, \
    Group
from aiogram_dialog.widgets.kbd.calendar_kbd import CalendarScopeView, CalendarDaysView, CalendarMonthView, \
    CalendarYearsView
from aiogram_dialog.widgets.text import Const, Format, Text

from elschool_bot.dialogs.grades.data_getter import DataGetterStates
from elschool_bot.dialogs.grades.show import ShowStates
from elschool_bot.repository import RegisterError


class GradesStates(StatesGroup):
    SELECT = State()
    SELECT_LESSONS = State()
    SELECT_LESSON_DATE = State()
    SELECT_DATE = State()
    STATUS = State()


async def on_start(start_data, manager: DialogManager):
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
            await manager.start(DataGetterStates.INPUT_FIRST,
                                {'text': f'{text} У меня не сохранены твои данные', 'input_data': ['логин', 'пароль']})
        elif login is None:
            manager.dialog_data.update(password=password)
            await manager.start(DataGetterStates.INPUT_FIRST,
                                {'text': f'{text} У меня не сохранён твой пароль', 'input_data': ['логин']})
        elif password is None:
            manager.dialog_data.update(login=login)
            await manager.start(DataGetterStates.INPUT_FIRST,
                                {'text': f'{text} У меня не сохранён твой логин', 'input_data': ['пароль']})
        else:
            await manager.update({'status': 'попытка регистрации'})
            try:
                jwtoken = await repo.check_register_user(login, password)
            except RegisterError as e:
                status = manager.dialog_data['status']
                message = e.args[0]
                if e.login is not None and e.password is not None:
                    message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
                await manager.update({'text': f'{status}\n{message}'})
            else:
                await repo.update_data(manager.event.from_user.id, jwtoken, login, password)
                await manager.update({'status': 'данные введены правильно, теперь попробую получить оценки'})
                try:
                    grades = await repo.get_grades(manager.event.from_user.id)
                except RegisterError as e:
                    status = manager.dialog_data['status']
                    message = e.args[0]
                    await manager.update({'text': f'{status}\n{message}'})
                else:
                    await show_select(grades, manager)

    else:
        await show_select(grades, manager)


async def on_process_result(start_data: dict, result, manager: DialogManager):
    if not isinstance(start_data, dict):
        return
    input_data = start_data.get('input_data')
    if input_data is None:
        return
    if len(input_data) == 2:
        login, password = result
    elif input_data[0] == 'логин':
        login = result
        password = manager.dialog_data['password']
    else:
        password = result
        login = manager.dialog_data['login']
    await manager.update({'status': 'попытка регистрации'})
    repo = manager.middleware_data['repo']
    try:
        jwtoken = await repo.check_register_user(login, password)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        if e.login is not None and e.password is not None:
            message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
        await manager.update({'text': f'{status}\n{message}'})
    else:
        if len(input_data) == 2:
            await repo.update_data(manager.event.from_user.id, jwtoken)
        elif input_data[0] == 'логин':
            await repo.update_data(manager.event.from_user.id, jwtoken, password=password)
        else:
            await repo.update_data(manager.event.from_user.id, jwtoken, login)
        await manager.update({'status': 'данные введены правильно, теперь попробую получить оценки'})
        try:
            grades = await repo.get_grades(manager.event.from_user.id)
        except RegisterError as e:
            status = manager.dialog_data['status']
            message = e.args[0]
            await manager.update({'text': f'{status}\n{message}'})
        else:
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


async def on_select_lesson_date(event, widget, manager: DialogManager, date: datetime.date):
    manager.dialog_data['lesson_date'] = date
    await manager.switch_to(GradesStates.SELECT)


async def on_select_date(event, widget, manager: DialogManager, date: datetime.date):
    manager.dialog_data['date'] = date
    await manager.switch_to(GradesStates.SELECT)


def mean_mark(marks):
    if not marks:
        return 0
    values = [mark['mark'] for mark in marks]
    return sum(values) / len(values)


def fix_to4(grades):
    """Как можно исправить оценку до 4."""
    results = []
    count_5 = 0
    while True:
        new_grades = grades.copy()
        added_grades = []
        new_grades += [5] * count_5
        added_grades += [5] * count_5
        if sum(new_grades) / len(new_grades) >= 3.5:
            results.append(added_grades)
            break
        while sum(new_grades) / len(new_grades) < 3.5:
            new_grades.append(4)
            added_grades.append(4)
        results.append(added_grades)
        count_5 += 1
    return results


def fix_to5(grades):
    """Как можно исправить оценку до 5."""
    new_grades = grades.copy()
    added_grades = []
    while sum(new_grades) / len(new_grades) < 4.5:
        new_grades.append(5)
        added_grades.append(5)
    return [added_grades]


def format_fix_marks(added, mark):
    text = []
    for add in added:
        text.append(', '.join(str(i) for i in add))
    text = '\n'.join(text)
    return f'для исправления оценки до {mark} можно получить\n{text}'


def fix_text(marks, mean):
    marks = [mark['mark'] for mark in marks]
    if mean < 3.5:
        added_marks4 = fix_to4(marks)
        added_marks5 = fix_to5(marks)
        return f'{format_fix_marks(added_marks4, 4)}\n{format_fix_marks(added_marks5, 5)}'
    elif mean < 4.5:
        added_marks = fix_to5(marks)
        return format_fix_marks(added_marks, 5)
    else:
        return ''


async def on_show(query, button, manager: DialogManager):
    grades = manager.dialog_data['grades']
    if not manager.find('select_all').is_checked():
        selected = manager.find('select_lessons').get_checked()
        lesson_names = list(grades)
        selected = {lesson_names[int(i)] for i in selected}
        grades = {key: value for key, value in grades.items() if key in selected}

    if lesson_date := manager.dialog_data.get('lesson_date'):
        new_grades = {}
        for key, values in grades.items():
            new_values = []
            for value in values:
                val_lesson_date = value['lesson_date']
                day, month, year = val_lesson_date.split('.')
                if int(year) == lesson_date.year and int(month) == lesson_date.month and int(day) == lesson_date.day:
                    new_values.append(value)
            new_grades[key] = new_values
        grades = new_grades

    if date := manager.dialog_data.get('date'):
        new_grades = {}
        for key, values in grades.items():
            new_values = []
            for value in values:
                val_date = value['date']
                day, month, year = val_date.split('.')
                if int(year) == date.year and int(month) == date.month and int(day) == date.day:
                    new_values.append(value)
            new_grades[key] = new_values
        grades = new_grades

    if manager.find('summary').is_checked():
        text = ['кратко показываю оценки:']
        lessons = {5: [], 4: [], 3: [], 2: [], 0: []}
        for lesson, marks in grades.items():

            mean = mean_mark(marks)
            if not mean:
                lessons[0].append(lesson)
            elif mean >= 4.5:
                lessons[5].append(lesson)
            elif mean >= 3.5:
                lessons[4].append(lesson)
            elif mean >= 2.5:
                lessons[3].append(lesson)
            else:
                lessons[2].append(lesson)
        for mark, lessons in lessons.items():
            lessons = ', '.join(lessons)
            if mark == 0:
                text.append(f'нет оценок по {lessons}')
            else:
                text.append(f'{mark} выходит по {lessons}')
        await manager.start(ShowStates.SHOW_SMALL, '\n'.join(text))
    elif manager.find('detail').is_checked():
        lessons = {}
        for lesson, marks in grades.items():
            mean = mean_mark(marks)
            if not mean:
                lessons[lesson] = {'marks': f'{lesson} нет оценок', 'fix': ''}
                continue
            text = [f'{lesson}, средняя {mean: .2f}']
            for mark in marks:
                value = mark['mark']
                lesson_date = mark['lesson_date']
                date = mark['date']
                text.append(f'{value}, дата урока {lesson_date}, дата проставления {date}')
            lessons[lesson] = {'marks': '\n'.join(text), 'fix': fix_text(marks, mean)}
        await manager.start(ShowStates.SHOW_BIG, lessons)
    else:
        text = [{'marks': 'показываю оценки', 'fix': ''}]
        for lesson, marks in grades.items():
            mean = mean_mark(marks)
            if not mean:
                text.append({'marks': f'{lesson} нет оценок', 'fix': ''})
                continue
            values = ', '.join([str(mark['mark']) for mark in marks])
            text.append({'marks': f'{lesson} {values}, средняя {mean: .2f}', 'fix': fix_text(marks, mean)})

        await manager.start(ShowStates.SHOW, text)


async def on_selected_lessons_changed(event, select, manager: DialogManager, item_id):
    if select.is_checked(item_id):
        await manager.find('select_all').set_checked(False)


async def on_del_lesson_date(query, button, manager: DialogManager):
    manager.dialog_data.pop('lesson_date', None)
    await manager.switch_to(GradesStates.SELECT)


async def on_del_date(query, button, manager: DialogManager):
    manager.dialog_data.pop('date', None)
    await manager.switch_to(GradesStates.SELECT)


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
                                                 next_month_text='<<' + Month(),
                                                 prev_month_text=Month() + '>>'),
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
        Row(
            Checkbox(Const('✓ 5'), Const('5'), 'five', default=True),
            Checkbox(Const('✓ 4'), Const('4'), 'four', default=True),
            Checkbox(Const('✓ 3'), Const('3'), 'three', default=True),
            Checkbox(Const('✓ 2'), Const('2'), 'two', default=True)
        ),
        state=GradesStates.SELECT
    ),
    Window(
        Const('выбери уроки'),
        Checkbox(
            Format('✓ все'),
            Format('все'),
            'select_all',
            default=True
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
    on_start=on_start,
    on_process_result=on_process_result
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(show.dialog)
    router.include_router(data_getter.dialog)
