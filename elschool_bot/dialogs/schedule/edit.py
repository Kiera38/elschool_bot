from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Select, Button, Column, SwitchTo, Cancel
from aiogram_dialog.widgets.text import Const, Format, List, Multi

from elschool_bot.repository import Repo


class EditScheduleStates(StatesGroup):
    SELECT_LESSON = State()
    EDIT = State()
    INPUT_TEXT = State()


async def start(lessons, date, manager: DialogManager):
    await manager.start(EditScheduleStates.SELECT_LESSON, (lessons, date))


async def on_select(event, select, manager: DialogManager, item: int):
    manager.dialog_data['lesson'] = manager.start_data[0][item]
    await manager.switch_to(EditScheduleStates.EDIT)


async def start_input(manager: DialogManager, input_text):
    manager.dialog_data['input_text'] = input_text
    await manager.switch_to(EditScheduleStates.INPUT_TEXT)


async def on_input_name(event, button, manager: DialogManager):
    await start_input(manager, 'название')


async def on_input_time(event, button, manager: DialogManager):
    await start_input(manager, 'время')


async def on_input_homework(event, button, manager: DialogManager):
    await start_input(manager, 'домашнее задание')


async def on_no_lesson(event, button, manager: DialogManager):
    input_type, lesson_number = save_edits(manager)
    manager.dialog_data['edits'][lesson_number]['remove'] = True
    await manager.switch_to(EditScheduleStates.SELECT_LESSON)


async def on_add_new(event, button, manager: DialogManager):
    await start_input(manager, 'номер урока с названием')


async def on_input(event, text_input, manager: DialogManager, text):
    input_type = {
        'название': 'name',
        'время': 'time',
        'домашнее задание': 'homework',
        'номер урока с названием': 'number_and_name'
    }[manager.dialog_data['input_text']]
    lesson_number = save_edits(manager)
    if input_type == 'time':
        start_time, end_time = text.split('-')
        start_time = start_time.strip()
        end_time = end_time.strip()
        manager.start_data[0][lesson_number]['start_time'] = start_time
        manager.start_data[0][lesson_number]['end_time'] = end_time
        manager.dialog_data['edits'][lesson_number]['start_time'] = start_time
        manager.dialog_data['edits'][lesson_number]['end_time'] = end_time
    elif input_type == 'number_and_name':
        number, name = text.split(' ')
        number = number.replace('.', '').strip()
        name = name.strip()
        manager.start_data[0][number] = {'name': name}
        manager.dialog_data['edits'][number] = {'name': name}
    else:
        manager.start_data[0][lesson_number][input_type] = text
        manager.dialog_data['edits'][lesson_number][input_type] = text
    await manager.switch_to(EditScheduleStates.EDIT)


def save_edits(manager):
    if 'edits' not in manager.dialog_data:
        manager.dialog_data['edits'] = {}
    lesson = manager.dialog_data.get('lesson')
    if lesson is None:
        return 0
    lesson_number = lesson['number']
    if lesson_number not in manager.dialog_data['edits']:
        manager.dialog_data['edits'][lesson_number] = {}
    return lesson_number


async def on_save(event, button, manager: DialogManager):
    edits = manager.dialog_data['edits']
    repo: Repo = manager.middleware_data['repo']
    await repo.add_changes(event.from_user.id, manager.start_data[1], edits)
    await event.message.answer('изменения сохранены')


dialog = Dialog(
    Window(
        Const("выбери, что хочешь изменить"),
        Const('сейчас это будет выглядеть так:'),
        List(
            Multi(
                Format('{item[number]}. {item[name]}'),
                Format('{item[start_time]} - {item[end_time]}'),
            ),
            items=F['start_data'][0].values().cast(list),
            sep='\n\n'
        ),
        Column(
            Select(
                Format("{item[number]}. {item[name]}"),
                'lesson',
                lambda item: item['number'],
                lambda data: list(data['start_data'][0].values()),
                int,
                on_click=on_select
            ),
        ),
        Button(Const('добавить'), 'add_new', on_click=on_add_new),
        Button(Const('сохранить'), 'save', on_click=on_save),
        Cancel(Const('отмена')),
        state=EditScheduleStates.SELECT_LESSON
    ),
    Window(
        Format('{dialog_data[lesson][number]}. {dialog_data[lesson][name]}'),
        Format('{dialog_data[lesson][start_time]} - {dialog_data[lesson][end_time]}'),
        Const('домашнее задание:', when=F['dialog_data']['lesson']['homework']),
        Format('{dialog_data[lesson][homework]}', when=F['dialog_data']['lesson']['homework']),
        Column(
            Button(Const('название'), 'name', on_input_name),
            Button(Const('время'), 'time', on_input_time),
            Button(Const('домашнее задание'), 'homework', on_input_homework),
            Button(Const('нет урока'), 'no_lesson', on_no_lesson),
            SwitchTo(Const('назад'), 'back', EditScheduleStates.SELECT_LESSON)
        ),
        state=EditScheduleStates.EDIT
    ),
    Window(
        Format('Введи новое {dialog_data[input_text]}'),
        TextInput('input_text', on_success=on_input),
        state=EditScheduleStates.INPUT_TEXT
    )
)
