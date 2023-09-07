import datetime
from typing import Dict

from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager, StartMode
from aiogram_dialog.widgets.kbd import Button, Checkbox, Row, Calendar, CalendarScope, Multiselect, SwitchTo, Group
from aiogram_dialog.widgets.kbd.calendar_kbd import CalendarScopeView, CalendarDaysView, CalendarMonthView, \
    CalendarYearsView
from aiogram_dialog.widgets.text import Const, Format, Text

from elschool_bot.dialogs.grades.show import ShowStates
from elschool_bot.dialogs.input_data import start_register
from elschool_bot.repository import RegisterError


class GradesStates(StatesGroup):
    SELECT = State()
    SELECT_LESSONS = State()
    SELECT_LESSON_DATE = State()
    SELECT_DATE = State()
    STATUS = State()


async def start_select_grades(manager: DialogManager):
    await manager.start(GradesStates.STATUS, mode=StartMode.RESET_STACK)
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
            await start_register(['логин', 'пароль'],(f'{text} У меня не сохранены твои данные', ''),
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
                await update_token(login, password, jwtoken, manager, 'всё')

    else:
        await show_select(grades, manager)


async def update_token(login, password, jwtoken, manager, save_data):
    repo = manager.middleware_data['repo']
    await manager.update({'status': 'обновление токена: попытка регистрации'})

    if save_data == 'всё':
        await repo.update_data(manager.event.from_user.id, jwtoken, login, password)
    elif save_data == 'логин':
        await repo.update_data(manager.event.from_user.id, jwtoken, login)
    elif save_data == 'пароль':
        await repo.update_data(manager.event.from_user.id, jwtoken, password=password)
    else:
        await repo.update_data(manager.event.from_user.id, jwtoken)
    await manager.update({'status': 'данные введены правильно, теперь попробую получить оценки'})
    try:
        grades = await repo.get_grades(manager.event.from_user.id)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        await manager.update({'text': f'{status}\n{message}'})
    else:
        await show_select(grades, manager)


async def on_process_result(start_data: dict, result, manager: DialogManager):
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
    await update_token(login, password, jwtoken, manager, save_data)


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

    marks_selected = {int(i) for i in manager.find('marks_selector').get_checked()}
    if marks_selected != {5, 4, 3, 2}:
        new_grades = {}
        for key, values in grades.items():
            new_values = []
            for value in values:
                mark = value['mark']
                if mark in marks_selected:
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
        text = []
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
    on_process_result=on_process_result,
    on_start=on_start
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(show.dialog)
