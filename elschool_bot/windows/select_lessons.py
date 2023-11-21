from aiogram import F
from aiogram_dialog import Window, DialogManager
from aiogram_dialog.widgets.kbd import Checkbox, Group, Multiselect, SwitchTo
from aiogram_dialog.widgets.text import Const, Format


async def on_select_all(event, checkbox, manager: DialogManager):
    if checkbox.is_checked():
        select_lessons = manager.find('select_lessons')
        await select_lessons.reset_checked()


async def on_selected_lessons_changed(event, select, manager: DialogManager, item_id):
    if select.is_checked(item_id):
        await manager.find('select_all').set_checked(False)


def create(state, select_state):
    return Window(
        Const('выбери уроки'),
        Checkbox(
            Const('✓ все'),
            Const('все'),
            'select_all',
            default=True,
            on_state_changed=on_select_all
        ),
        Checkbox(
            Const('✓ показывать без оценок'),
            Const('показывать без оценок'),
            'show_without_marks',
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
        SwitchTo(Const('назад'), '', select_state),
        state=state
    )