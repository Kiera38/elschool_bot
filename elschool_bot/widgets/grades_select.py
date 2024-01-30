from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import SwitchTo, Row, Multiselect, Radio, Checkbox, Start, Button
from aiogram_dialog.widgets.text import Format, Const

from elschool_bot.dialogs.date_selector import DateSelectorStates


def not_statistics_checked(data, widget, manager):
    return not statistics_checked(data, widget, manager)


def statistics_checked(data, widget, manager: DialogManager):
    return manager.find('show_format').is_checked('статистика')


def is_statistics_checked(manager: DialogManager):
    return statistics_checked(None, None, manager)


async def on_show_without_marks(event, checkbox, manager: DialogManager):
    show_without_marks = manager.find('show_without_marks')
    is_checked = checkbox.is_checked()
    if is_checked != show_without_marks.is_checked():
        await show_without_marks.set_checked(is_checked)


async def on_start(manager: DialogManager):
    marks = manager.find('marks_selector')
    for i in range(2, 6):
        await marks.set_checked(str(i), True)

    await manager.find('show_format').set_checked('статистика')


def is_show_without_marks_checked(manager: DialogManager):
    if is_statistics_checked(manager):
        return manager.find('show_without_marks_statistics').is_checked()
    return manager.find('show_without_marks').is_checked()


async def set_show_without_marks(manager: DialogManager):
    if is_statistics_checked(manager):
        await manager.find('show_without_marks_statistics').set_checked(True)
    else:
        await manager.find('show_without_marks').set_checked(True)


async def on_start_lesson_date(event, button, manager: DialogManager):
    manager.dialog_data['start_lesson_date'] = True
    await manager.start(DateSelectorStates.SELECT_VARIANT, manager.dialog_data.get('lesson_dates'))


async def on_start_date(event, button, manager: DialogManager):
    manager.dialog_data['start_date'] = True
    await manager.start(DateSelectorStates.SELECT_VARIANT, manager.dialog_data.get('dates'))


def process_result(result, manager: DialogManager):
    if 'start_lesson_date' in manager.dialog_data:
        del manager.dialog_data['start_lesson_date']
        manager.dialog_data['lesson_dates'] = result
        return True
    if 'start_date' in manager.dialog_data:
        del manager.dialog_data['start_date']
        manager.dialog_data['dates'] = result
        return True
    return False


def create(lessons_state, lesson_date_state):
    select_lessons = SwitchTo(
        Format('выбрать предметы из списка'),
        'lessons_picked',
        lessons_state,
        when=not_statistics_checked
    )
    select_date = Button(
        Format('дата проставления'),
        'date',
        on_start_date
    )

    if lesson_date_state:
        center = (
            select_lessons,
            Row(
                Button(
                    Format('дата урока'),
                    'date_lesson',
                    on_start_lesson_date
                ),
                select_date,
            ),
        )
    else:
        center = (Row(select_lessons, select_date),)

    return (
        Radio(
            Format('✓ {item}'),
            Format('{item}'),
            'show_format',
            lambda item: item,
            ['статистика', 'список']
        ),
        Checkbox(
            Const('✓ показывать без оценок'),
            Const('показывать без оценок'),
            'show_without_marks_statistics',
            when=statistics_checked,
            on_state_changed=on_show_without_marks
        ),
        *center,
        Multiselect(
            Format('✓ {item}'),
            Format('{item}'),
            'marks_selector',
            lambda item: item,
            (5, 4, 3, 2)
        ),
    )
