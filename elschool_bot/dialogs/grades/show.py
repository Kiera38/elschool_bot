from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Dialog, Window
from aiogram_dialog.widgets.kbd import Button, Row, Checkbox, ManagedCheckboxAdapter, Back, Cancel
from aiogram_dialog.widgets.text import Text, Format, Const, List, Case


class ShowStates(StatesGroup):
    SHOW_SMALL = State()
    SHOW = State()
    SHOW_BIG = State()


class TextFromGetter(Text):
    def __init__(self, text_getter, when=None):
        super().__init__(when)
        self.text_getter = text_getter

    async def _render_text(self, data, manager: DialogManager) -> str:
        return self.text_getter(data, self, manager)


async def on_start(start_data, manager: DialogManager):
    if isinstance(start_data, dict):
        manager.dialog_data['current_lesson'] = list(start_data)[0]
        manager.dialog_data['current_lesson_index'] = 0


async def on_back(query, button, manager: DialogManager):
    current_lesson_index = manager.dialog_data['current_lesson_index']
    current_lesson_index -= 1
    lessons = manager.start_data
    if current_lesson_index == 0:
        current_lesson_index = len(lessons) - 1
    manager.dialog_data['current_lesson'] = list(lessons)[current_lesson_index]
    manager.dialog_data['current_lesson_index'] = current_lesson_index


async def on_next(query, button, manager: DialogManager):
    current_lesson_index = manager.dialog_data['current_lesson_index']
    current_lesson_index += 1
    lessons = manager.start_data
    if current_lesson_index == len(lessons):
        current_lesson_index = 0
    manager.dialog_data['current_lesson'] = list(lessons)[current_lesson_index]
    manager.dialog_data['current_lesson_index'] = current_lesson_index


async def on_show_fix(event, checkbox: ManagedCheckboxAdapter, manager: DialogManager):
    await manager.update({'show_fix': checkbox.is_checked()})


def text_getter(data, text, manager: DialogManager):
    text = data['start_data'][data['dialog_data']['current_lesson']]
    show_fix = data['dialog_data'].get('show_fix')
    if show_fix:
        mark = text['marks']
        fix = text['fix']
        return f'{mark}\n\n{fix}'
    return text['marks']


dialog = Dialog(
    Window(Format('{start_data}'), Cancel(Const('изменить настройки')), state=ShowStates.SHOW_SMALL),
    Window(
        List(
            Case({
                True: Format('{item[marks]}\n{item[fix]}\n'),
                False: Format('{item[marks]}'),
            }, F['data']['dialog_data'].get('show_fix', False)),
            F['start_data']
        ),
        Checkbox(
            Const('✓ подсказки по исправлению'),
            Const('подсказки по исправлению'),
            'show_fix',
            on_state_changed=on_show_fix
        ),
        Cancel(Const('изменить настройки')),
        state=ShowStates.SHOW
    ),
    Window(
        TextFromGetter(text_getter),
        Row(
            Button(Const('<<'), 'back', on_back),
            Button(Const('>>'), 'next', on_next),
        ),
        Checkbox(
            Const('✓ подсказки по исправлению'),
            Const('подсказки по исправлению'),
            'show_fix',
            on_state_changed=on_show_fix
        ),
        Cancel(Const('изменить настройки')),
        state=ShowStates.SHOW_BIG
    ),
    on_start=on_start
)
