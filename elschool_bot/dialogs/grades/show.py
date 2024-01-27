import itertools
import datetime

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


def mean_mark(marks):
    values = [mark['mark'] for mark in marks if mark['mark'] != 0]
    if not values:
        return 0
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
    return f'до <b>{mark}</b>:\n{text}'


def fix_text(marks, mean):
    marks = [mark['mark'] for mark in marks]
    title = '\nподсказки по исправлению:'
    if mean < 2.5:
        added_marks3 = fix_to3(marks)
        added_marks4 = fix_to4(marks)
        added_marks5 = fix_to5(marks)
        return (f'{title}\n{format_fix_marks(added_marks3, 3)}\n\n'
                f'{format_fix_marks(added_marks4, 4)}\n\n{format_fix_marks(added_marks5, 5)}')
    if mean < 3.5:
        added_marks4 = fix_to4(marks)
        added_marks5 = fix_to5(marks)
        return f'{title}\n{format_fix_marks(added_marks4, 4)}\n\n{format_fix_marks(added_marks5, 5)}'
    elif mean < 4.5:
        added_marks = fix_to5(marks)
        return f'{title}\n{format_fix_marks(added_marks, 5)}'
    else:
        return ''


async def show_default(grades, manager, filters, value_filters, show_back=True):
    text = []
    fix_lessons = {}
    for lesson, marks in grades.items():
        mean = mean_mark(marks)
        fix_lessons[lesson] = {
            'fix': fix_text(marks, mean),
            'mean': mean
        }
    grades = filter_grades(grades, filters, value_filters)
    for lesson, marks in grades.items():
        mean = fix_lessons[lesson]['mean']
        if not marks:
            text.append({'marks': f'<b>{lesson} нет оценок</b>', 'fix': ''})
            continue
        values = ', '.join([str(mark['mark']) for mark in marks])
        text.append({'marks': f'<b>{lesson}</b> {values}, <b>средняя части года</b> {mean: .2f}',
                     'fix': fix_lessons[lesson]['fix']})
    await manager.start(ShowStates.SHOW, {'text': text, 'show_back': show_back})


async def show_detail(grades, manager: DialogManager, filters, value_filters, show_back=True):
    lessons = {}
    mean_value = mean_mark(list(itertools.chain(*grades.values())))

    for lesson, marks in grades.items():
        mean = mean_mark(marks)
        if not mean:
            lessons[lesson] = f'<b>{lesson} нет оценок</b>', mean
            continue

        text = [f'<i>статистика</i> оценок по <b>{lesson}</b>, <u>средняя</u> {mean: .2f}']
        if mean_value != 0:
            if mean >= mean_value:
                text.append(f'<b>эта</b> <i>средняя оценка</i> <b>больше</b> <i>средней оценки</i> по всем предметам ({mean_value:.2f})')
            else:
                text.append(f'<b>эта</b> <i>средняя оценка</i> <b>меньше</b> <i>средней оценки</i> по всем предметам ({mean_value:.2f})')

        if mean >= 4.5:
            text.append('в <b>этой части года</b> <u>должна</u> выйти 5')
        elif mean >= 3.5:
            text.append('в <b>этой части года</b> <u>должна</u> выйти 4')
        elif mean >= 2.5:
            text.append('в <b>этой части года</b> <u>должна</u> выйти 3')
        elif mean > 0:
            text.append('в <b>этой части года</b> <u>должна</u> выйти 2')
        else:
            text.append('<u>нет оценок</u>. Нужно получить. А то ничего не выйдет.')
        lessons[lesson] = text, mean

    grades = filter_grades(grades, filters, value_filters)
    lessons_text = {}

    for lesson, marks in grades.items():
        text, mean = lessons[lesson]
        if not mean:
            lessons_text[lesson] = text
            continue
        marks_count = {5: 0, 4: 0, 3: 0, 2: 0}
        marks_text = ['<u>список выбранных оценок</u>:']
        for mark in marks:
            value = mark['mark']
            lesson_date = mark['lesson_date']
            date = mark['date']
            marks_count[value] += 1
            marks_text.append(
                f'<b>{value}</b>, <u>дата урока</u> <i>{lesson_date}</i>, <u>дата проставления</u> <i>{date}</i>')

        marks_count_text = [f'<b>всего оценок</b>: {sum(marks_count.values())}, из них:']
        for mark, count in marks_count.items():
            marks_count_text.append(f'<b>{mark}</b> - <u>{count}</u>')

        text += '\n'.join(marks_count_text), '\n'.join(marks_text)
        lessons_text[lesson] = '\n'.join(('\n\n'.join(text), fix_text(marks, mean)))
    await manager.start(ShowStates.SHOW_BIG, {'lessons': lessons_text, 'show_back': show_back})


async def show_summary(grades, manager, marks_selected, show_back=True):
    text = ['<b>статистика</b> <i>оценок</i> за <u>текущую часть года</u>:']
    lessons = {5: [], 4: [], 3: [], 2: [], 0: []}
    max_mean = ['', 0]
    min_mean = ['', 6]

    less_mean = []
    greater_mean = []
    print(list(itertools.chain(*grades.values())))
    mean_value = mean_mark(list(itertools.chain(*grades.values())))
    if mean_value != 0:
        text.append(f'{mean_value:.2f} - <b>средняя</b> <i>оценка</i> по <b>всем</b> предметам')

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

        if mean != 0:
            if mean > max_mean[1]:
                max_mean = lesson, mean
            elif mean < min_mean[1]:
                min_mean = lesson, mean

            if mean >= mean_value:
                greater_mean.append(lesson)
            elif mean < mean_value:
                less_mean.append(lesson)

    if max_mean[1] != 0:
        text.append(f'{max_mean[1]:.2f} — <b>наибольшая</b> <i>средняя</i> оценка по <u>{max_mean[0]}</u>')
    if min_mean[1] != 6:
        text.append(f'{min_mean[1]:.2f} — <b>наименьшая</b> <i>средняя</i> оценка по <u>{min_mean[0]}</u>')

    if greater_mean:
        greater_mean_lessons = ', '.join(greater_mean)
        text.append(f'<b>средняя оценка</b> по предметам {greater_mean_lessons} '
                    f'<b>больше</b> <u>средней оценки</u> по <i>всем</i> предметам')

    if less_mean:
        less_mean_lessons = ', '.join(less_mean)
        text.append(f'<b>средняя оценка</b> по предметам {less_mean_lessons} '
                    f'<b>меньше</b> <u>средней оценки</u> по <i>всем</i> предметам')

    for mark, lessons in lessons.items():
        if mark not in marks_selected:
            continue
        lessons = ', '.join(lessons)
        if mark == 0:
            text.append(f'<b>нет оценок</b> по предметам {lessons}')
        elif lessons:
            text.append(f'<b>{mark}</b> выходит по {lessons}')
    await manager.start(ShowStates.SHOW_SMALL, {'grades': '\n\n'.join(text), 'show_back': show_back})


class TextFromGetter(Text):
    def __init__(self, text_getter, when=None):
        super().__init__(when)
        self.text_getter = text_getter

    async def _render_text(self, data, manager: DialogManager) -> str:
        return self.text_getter(data, self, manager)


async def on_start(start_data, manager: DialogManager):
    if isinstance(start_data, dict) and 'lessons' in start_data:
        lessons = list(start_data['lessons'])
        if not lessons:
            manager.dialog_data['current_lesson'] = 'нет уроков'
            manager.dialog_data['current_lesson_index'] = -1
            return
        manager.dialog_data['current_lesson'] = lessons[0]
        manager.dialog_data['current_lesson_index'] = 0


async def on_back(query, button, manager: DialogManager):
    current_lesson_index = manager.dialog_data['current_lesson_index']
    if current_lesson_index == -1:
        return
    current_lesson_index -= 1
    lessons = manager.start_data['lessons']
    if current_lesson_index < 0:
        current_lesson_index = len(lessons) - 1
    manager.dialog_data['current_lesson'] = list(lessons)[current_lesson_index]
    manager.dialog_data['current_lesson_index'] = current_lesson_index


async def on_next(query, button, manager: DialogManager):
    current_lesson_index = manager.dialog_data['current_lesson_index']
    if current_lesson_index == -1:
        return
    current_lesson_index += 1
    lessons = manager.start_data['lessons']
    if current_lesson_index >= len(lessons):
        current_lesson_index = 0
    manager.dialog_data['current_lesson'] = list(lessons)[current_lesson_index]
    manager.dialog_data['current_lesson_index'] = current_lesson_index


async def on_select_current_lesson(event, select, manager: DialogManager, item):
    if manager.dialog_data['current_lesson_index'] == -1:
        await manager.switch_to(ShowStates.SHOW_BIG)
        return
    item = int(item)
    manager.dialog_data['current_lesson'] = list(manager.start_data['lessons'])[item]
    manager.dialog_data['current_lesson_index'] = item
    await manager.switch_to(ShowStates.SHOW_BIG)


async def on_show_fix(event, checkbox, manager: DialogManager):
    await manager.update({'show_fix': checkbox.is_checked()})


def text_getter(data, text, manager: DialogManager):
    if data['dialog_data']['current_lesson_index'] == -1:
        return 'нет данных'
    lessons = data['start_data']['lessons']
    return lessons[data['dialog_data']['current_lesson']]


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
                lambda data: list((i, lesson) for i, lesson in enumerate(data['start_data']['lessons'] or ['нет уроков'])),
                on_click=on_select_current_lesson
            ),
            width=2
        ),
        state=ShowStates.SELECT_CURRENT_LESSON
    ),
    on_start=on_start
)
