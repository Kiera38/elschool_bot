from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import SwitchTo, Row, Multiselect, Checkbox
from aiogram_dialog.widgets.text import Format, Const


def not_summary_checked(data, widget, manager):
    return not manager.find('summary').is_checked()


async def on_summary_set(event, checkbox, manager: DialogManager):
    if checkbox.is_checked():
        await manager.find('detail').set_checked(False)


async def on_detail_set(event, checkbox, manager: DialogManager):
    if checkbox.is_checked():
        await manager.find('summary').set_checked(False)


def create(lessons_state, lesson_date_state, date_state):
    select_lessons = SwitchTo(
        Format('выбрать из списка'),
        'lessons_picked',
        lessons_state,
        when=not_summary_checked
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
        Row(
            Checkbox(Const('✓ кратко'), Const('кратко'), 'summary', on_state_changed=on_summary_set),
            Checkbox(Const('✓ подробно'), Const('подробно'), 'detail', on_state_changed=on_detail_set)
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
