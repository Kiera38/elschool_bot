from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Row, Checkbox, SwitchTo, Group, Radio
from aiogram_dialog.widgets.text import Text, Format, Const, List, Case


class ShowStates(StatesGroup):
    SHOW_SMALL = State()
    SHOW = State()
    SHOW_BIG = State()
    SELECT_CURRENT_LESSON = State()


def mean_mark(marks):
    if not marks:
        return 0
    values = [mark['mark'] for mark in marks]
    return sum(values) / len(values)


def fix_to3(grades):
    results = []
    start_count = len(grades)
    count_5 = 0
    while True:
        new_grades = grades.copy()
        new_grades += [5] * count_5
        if sum(new_grades) / len(new_grades) >= 2.5:
            results.append(new_grades[start_count:])
            return results
        count_4 = 0
        while True:
            new_grades2 = new_grades.copy()
            new_grades2 += [4] * count_4
            if sum(new_grades2) / len(new_grades2) >= 2.5:
                results.append(new_grades2[start_count:])
                break
            while sum(new_grades2) / len(new_grades2) < 2.5:
                new_grades2.append(3)
            results.append(new_grades2[start_count:])
            count_4 += 1
        count_5 += 1


def fix_to4(grades):
    """Как можно исправить оценку до 4."""
    results = []
    start_count = len(grades)
    count_5 = 0
    while True:
        new_grades = grades.copy()
        new_grades += [5] * count_5
        if sum(new_grades) / len(new_grades) >= 3.5:
            results.append(new_grades[start_count:])
            break
        while sum(new_grades) / len(new_grades) < 3.5:
            new_grades.append(4)
        results.append(new_grades[start_count:])
        count_5 += 1
    return results


def fix_to5(grades):
    """Как можно исправить оценку до 5."""
    new_grades = grades.copy()
    start_count = len(grades)
    while sum(new_grades) / len(new_grades) < 4.5:
        new_grades.append(5)
    return [new_grades[start_count:]]


def format_fix_marks(added, mark):
    text = []
    for add in added:
        text.append(', '.join(str(i) for i in add))
    text = '\n'.join(text)
    return f'для исправления оценки до {mark} можно получить\n{text}'


def fix_text(marks, mean):
    marks = [mark['mark'] for mark in marks]
    if mean < 2.5:
        added_marks3 = fix_to3(marks)
        added_marks4 = fix_to4(marks)
        added_marks5 = fix_to5(marks)
        return (f'\n{format_fix_marks(added_marks3, 3)}\n'
                f'{format_fix_marks(added_marks4, 4)}\n{format_fix_marks(added_marks5, 5)}')
    if mean < 3.5:
        added_marks4 = fix_to4(marks)
        added_marks5 = fix_to5(marks)
        return f'\n{format_fix_marks(added_marks4, 4)}\n{format_fix_marks(added_marks5, 5)}'
    elif mean < 4.5:
        added_marks = fix_to5(marks)
        return '\n' + format_fix_marks(added_marks, 5)
    else:
        return ''


async def show_default(grades, manager, show_back=True):
    text = []
    for lesson, marks in grades.items():
        mean = mean_mark(marks)
        if not mean:
            text.append({'marks': f'{lesson} нет оценок', 'fix': ''})
            continue
        values = ', '.join([str(mark['mark']) for mark in marks])
        text.append({'marks': f'{lesson} {values}, средняя {mean: .2f}', 'fix': fix_text(marks, mean)})
    await manager.start(ShowStates.SHOW, {'text': text, 'show_back': show_back})


async def show_detail(grades, manager: DialogManager, show_back=True):
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
    await manager.start(ShowStates.SHOW_BIG, {'lessons': lessons, 'show_back': show_back})


async def show_summary(grades, manager, marks_selected, show_back=True):
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
        if mark not in marks_selected:
            continue
        lessons = ', '.join(lessons)
        if mark == 0:
            text.append(f'нет оценок по {lessons}')
        else:
            text.append(f'{mark} выходит по {lessons}')
    await manager.start(ShowStates.SHOW_SMALL, {'grades': '\n'.join(text), 'show_back': show_back})


class TextFromGetter(Text):
    def __init__(self, text_getter, when=None):
        super().__init__(when)
        self.text_getter = text_getter

    async def _render_text(self, data, manager: DialogManager) -> str:
        return self.text_getter(data, self, manager)


async def on_start(start_data, manager: DialogManager):
    if isinstance(start_data, dict) and 'lessons' in start_data:
        manager.dialog_data['current_lesson'] = list(start_data['lessons'])[0]
        manager.dialog_data['current_lesson_index'] = 0


async def on_back(query, button, manager: DialogManager):
    current_lesson_index = manager.dialog_data['current_lesson_index']
    current_lesson_index -= 1
    lessons = manager.start_data['lessons']
    if current_lesson_index == 0:
        current_lesson_index = len(lessons) - 1
    manager.dialog_data['current_lesson'] = list(lessons)[current_lesson_index]
    manager.dialog_data['current_lesson_index'] = current_lesson_index


async def on_next(query, button, manager: DialogManager):
    current_lesson_index = manager.dialog_data['current_lesson_index']
    current_lesson_index += 1
    lessons = manager.start_data['lessons']
    if current_lesson_index == len(lessons):
        current_lesson_index = 0
    manager.dialog_data['current_lesson'] = list(lessons)[current_lesson_index]
    manager.dialog_data['current_lesson_index'] = current_lesson_index


async def on_select_current_lesson(event, select, manager: DialogManager, item):
    item = int(item)
    manager.dialog_data['current_lesson'] = list(manager.start_data['lessons'])[item]
    manager.dialog_data['current_lesson_index'] = item
    await manager.switch_to(ShowStates.SHOW_BIG)


async def on_show_fix(event, checkbox, manager: DialogManager):
    await manager.update({'show_fix': checkbox.is_checked()})


def text_getter(data, text, manager: DialogManager):
    lessons = data['start_data']['lessons']
    text = lessons[data['dialog_data']['current_lesson']]
    show_fix = data['dialog_data'].get('show_fix')
    if show_fix:
        mark = text['marks']
        fix = text['fix']
        return f'{mark}\n{fix}'
    return text['marks']


async def on_change_settings(query, button, manager: DialogManager):
    await manager.done('change_settings')


dialog = Dialog(
    Window(
        Format('{start_data[grades]}'),
        Button(Const('изменить настройки'), 'change_settings_small',
               on_change_settings, when=F['start_data']['show_back']),
        state=ShowStates.SHOW_SMALL
    ),
    Window(
        Const('показываю оценки'),
        List(
            Case({
                True: Format('{item[marks]}{item[fix]}\n'),
                False: Format('{item[marks]}'),
            }, F['data']['dialog_data'].get('show_fix', False)),
            F['start_data']['text']
        ),
        Checkbox(
            Const('✓ подсказки по исправлению'),
            Const('подсказки по исправлению'),
            'show_fix',
            on_state_changed=on_show_fix
        ),
        Button(Const('изменить настройки'), 'change_settings',
               on_change_settings, when=F['start_data']['show_back']),
        state=ShowStates.SHOW
    ),
    Window(
        TextFromGetter(text_getter),
        Row(
            Button(Const('<<'), 'back', on_back),
            SwitchTo(Format('{dialog_data[current_lesson]}'), 'switch', ShowStates.SELECT_CURRENT_LESSON),
            Button(Const('>>'), 'next', on_next),
        ),
        Checkbox(
            Const('✓ подсказки по исправлению'),
            Const('подсказки по исправлению'),
            'show_fix',
            on_state_changed=on_show_fix
        ),
        Button(Const('изменить настройки'), 'change_settings_big',
               on_change_settings, when=F['start_data']['show_back']),
        state=ShowStates.SHOW_BIG
    ),
    Window(
        Const('выбери урок'),
        Group(
            Radio(
                Format('✓ {item[1]}'),
                Format('{item[1]}'),
                'select',
                lambda item: item[0],
                lambda data: list((i, lesson) for i, lesson in enumerate(data['start_data']['lessons'])),
                on_click=on_select_current_lesson
            ),
            width=2
        ),
        state=ShowStates.SELECT_CURRENT_LESSON
    ),
    on_start=on_start
)
