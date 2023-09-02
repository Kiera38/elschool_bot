from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Select, Cancel
from aiogram_dialog.widgets.text import Format, Const

from elschool_bot.repository import Repo, RegisterError, DataProcessError


class InputDataStates(StatesGroup):
    INPUT_FIRST = State()
    INPUT_SECOND = State()
    CHECK_DATA = State()
    ERROR = State()


async def on_first(message: Message, text_input, manager: DialogManager, first):
    await message.delete()
    if 'status' in manager.dialog_data:
        input_first = manager.start_data['inputs'][0]
        manager.dialog_data['status'] = f'новый {input_first} получил, теперь можешь попробовать ещё раз'
        await manager.switch_to(InputDataStates.ERROR)
        return

    if len(manager.start_data['inputs']) == 1:
        if manager.start_data['inputs'][0] == 'логин':
            await check_register(first, manager.start_data['value'], manager)
        else:
            await check_register(manager.start_data['value'], first, manager)
        return

    await manager.next()


async def on_second(message: Message, text_input, manager: DialogManager, second):
    if message:
        await message.delete()

    if 'status' in manager.dialog_data:
        input_first = manager.start_data['inputs'][1]
        manager.dialog_data['status'] = f'новый {input_first} получил, теперь можешь попробовать ещё раз'
        await manager.switch_to(InputDataStates.ERROR)
        return

    if manager.start_data['inputs'][0] == 'логин':
        await check_register(manager.find('input_first').get_value(), second, manager)
    else:
        await check_register(second, manager.find('input_first').get_value(), manager)


async def check_register(login, password, manager: DialogManager):
    repo: Repo = manager.middleware_data['repo']
    manager.dialog_data['status'] = 'проверка данных: попытка регистрации'
    await manager.switch_to(InputDataStates.CHECK_DATA)
    try:
        jwtoken = await repo.check_register_user(login, password)
        result = {'login': login, 'password': password, 'jwtoken': jwtoken}
        if manager.start_data.get('check_get_grades', False):
            await manager.update({'status': 'проверка данных: получение оценок'})
            grades, url = await repo.check_get_grades(jwtoken)
            result.update(grades=grades, url=url)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        if e.login is not None and e.password is not None:
            message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
        manager.dialog_data['status'] = f'{status}\n{message}'
        await manager.switch_to(InputDataStates.ERROR)
    except DataProcessError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        manager.dialog_data['status'] = f'{status}\n{message}'
        await manager.switch_to(InputDataStates.ERROR)
    else:
        await manager.done(result)


async def on_select_change(query, select, manager: DialogManager, item):
    del manager.dialog_data['status']
    manager.dialog_data['change'] = True
    if item == manager.start_data['inputs'][0]:
        await manager.switch_to(InputDataStates.INPUT_FIRST)
    else:
        await manager.switch_to(InputDataStates.INPUT_SECOND)


async def getter(dialog_manager: DialogManager, **kwargs):
    start_data = dialog_manager.start_data
    dialog_data = dialog_manager.dialog_data
    if dialog_data.get('change'):
        return {'texts': start_data['change_texts']}
    return {'texts': start_data['input_texts']}


async def start_register(inputs, input_texts, manager: DialogManager,
                         change_texts=None, value=None, check_get_grades=True):
    if change_texts is None:
        change_texts = input_texts
    await manager.start(InputDataStates.INPUT_FIRST,
                        {'inputs': inputs, 'input_texts': input_texts,
                         'change_texts': change_texts, 'value': value, 'check_get_grades': check_get_grades})


async def on_try(query, button, manager: DialogManager):
    inputs = manager.start_data['inputs']
    if len(inputs) == 1:
        first = manager.find('input_first').get_value()
        second = manager.start_data['value']
    else:
        first = manager.find('input_first').get_value()
        second = manager.find('input_second').get_value()

    if inputs[0] == 'логин':
        await check_register(first, second, manager)
    else:
        await check_register(second, first, manager)


dialog = Dialog(
    Window(
        Format('{texts[0]} Сначала введи {start_data[inputs][0]}.'),
        TextInput('input_first', on_success=on_first),
        state=InputDataStates.INPUT_FIRST,
        getter=getter
    ),
    Window(
        Format('{texts[1]} Теперь введи {start_data[inputs][1]}.'),
        TextInput('input_second', on_success=on_second),
        state=InputDataStates.INPUT_SECOND,
        getter=getter
    ),
    Window(
        Format('{dialog_data[status]}'),
        state=InputDataStates.CHECK_DATA
    ),
    Window(
        Format('{dialog_data[status]}'),
        Select(
            Format('изменить {item}'),
            'select_change',
            lambda item: item, F['start_data']['inputs'],
            on_click=on_select_change
        ),
        Button(Const('попробовать ещё раз'), 'try', on_try),
        Cancel(Const('попробовать потом')),
        state=InputDataStates.ERROR
    ),
)
