from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import SwitchTo, Row, Multiselect, Radio, Checkbox
from aiogram_dialog.widgets.text import Format, Const


def not_statistics_checked(data, widget, manager):
    return not statistics_checked(data, widget, manager)


def not_summary_checked(data, widget, manager: DialogManager):
    return not_statistics_checked(data, widget, manager) or not manager.find('statistics_variant').is_checked('общая')


def statistics_checked(data, widget, manager: DialogManager):
    return manager.find('show_format').is_checked('статистика')


def detail_checked(data, widget, manager: DialogManager):
    return statistics_checked(data, widget, manager) and manager.find('statistics_variant').is_checked('подробная')


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
    await manager.find('statistics_variant').set_checked('общая')


def is_show_without_marks_checked(manager: DialogManager):
    if detail_checked(None, None, manager):
        return manager.find('show_without_marks_detail').is_checked()
    return manager.find('show_without_marks').is_checked()


def is_summary_checked(manager):
    return statistics_checked(None, None, manager) and manager.find('statistics_variant').is_checked('общая')


def is_detail_checked(manager):
    return detail_checked(None, None, manager)


def create(lessons_state, lesson_date_state, date_state):
    select_lessons = SwitchTo(
        Format('выбрать из списка'),
        'lessons_picked',
        lessons_state,
        when=not_statistics_checked
    )
    select_date = SwitchTo(
        Format('{dialog_data[checked_date]} дата проставления'),
        'date',
        date_state
    )

    if lesson_date_state is not None:
        center = (
            select_lessons,
            Row(
                SwitchTo(
                    Format('{dialog_data[checked_date_lesson]} дата урока'),
                    'date_lesson',
                    lesson_date_state
                ),
                select_date,
                when=not_summary_checked
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
        Radio(
            Format('✓ {item}'),
            Format('{item}'),
            'statistics_variant',
            lambda item: item,
            ['общая', 'подробная'],
            when=statistics_checked
        ),
        Checkbox(
            Const('✓ показывать без оценок'),
            Const('показывать без оценок'),
            'show_without_marks_detail',
            when=detail_checked,
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
