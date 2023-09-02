from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import RegisterError, Repo


class ChangeStates(StatesGroup):
    START = State()
    NO_SAVED_DATA_INPUT = State()
    STATUS = State()


async def on_input(message: Message, text_input, manager: DialogManager, text):
    input_type = manager.start_data['input_type']
    no_type = manager.start_data['no_type']
    if input_type == no_type or no_type is None:
        manager.dialog_data.update(status='проверка данных: попытка регистрации', cancel_text='отмена')
        await manager.switch_to(ChangeStates.STATUS)
        await manager.show()
        repo: Repo = manager.middleware_data['repo']
        if no_type == 'логин':
            login, _ = await repo.get_user_data(message.from_user.id)
            password = text
        else:
            _, password = await repo.get_user_data(message.from_user.id)
            login = text
        try:
            jwtoken = await repo.check_register_user(login, password)
        except RegisterError as e:
            status = manager.dialog_data['status']
            message = e.args[0]
            if e.login is not None and e.password is not None:
                message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
            await manager.update({'status': f'{status}\n{message}'})
            return
        if no_type is None:
            await repo.update_data(message.from_user.id, jwtoken, login, password)
        elif input_type == 'логин':
            await repo.update_data(message.from_user.id, jwtoken, login)
        else:
            await repo.update_data(message.from_user.id, jwtoken, password=password)
        await manager.update({'status': f'изменение {input_type} завершено', 'cancel_text': 'в настройки'})
    else:
        await manager.switch_to(ChangeStates.NO_SAVED_DATA_INPUT)


async def on_input_no_data(message, text_input, manager: DialogManager, text2):
    text1 = manager.find('input').get_value()
    input_type = manager.start_data['input_type']
    if input_type == 'логин':
        login = text1
        password = text2
    else:
        password = text1
        login = text2
    repo = manager.middleware_data['repo']
    manager.dialog_data.update(status='проверка данных: попытка регистрации', cancel_text='отмена')
    await manager.switch_to(ChangeStates.STATUS)
    await manager.show()
    try:
        jwtoken = await repo.check_register_user(login, password)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        if e.login is not None and e.password is not None:
            message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
        await manager.update({'status': f'{status}\n{message}'})
        return
    if input_type == 'логин':
        await repo.update_data(message.from_user.id, jwtoken, login)
    else:
        await repo.update_data(message.from_user.id, jwtoken, password=password)
    await manager.update({'status': f'изменение {input_type} завершено', 'cancel_text': 'в настройки'})


async def on_clear(query: CallbackQuery, button, manager: DialogManager):
    repo = manager.middleware_data['repo']
    login, password, jwtoken = await repo.get_user_data_jwtoken(query.from_user.id)
    if manager.start_data['input_type'] == 'логин':
        await repo.update_data(query.from_user.id, jwtoken, password=password)
        manager.dialog_data.update(status='я удалил твой логин, но ты всё ещё можешь получать оценки',
                                   cancel_text='в настройки')
    else:
        await repo.update_data(query.from_user.id, jwtoken, login)
        manager.dialog_data.update(status='я удалил твой пароль, но ты всё ещё можешь получать оценки',
                                   cancel_text='в настройки')
    await manager.switch_to(ChangeStates.STATUS)


dialog = Dialog(
    Window(
        Format('хорошо, введи новый {start_data[input_type]}'),
        Cancel(Const('отмена')),
        Button(Const('больше не храни'), 'clear',
               when=lambda data, button, manager: manager.start_data['input_type'] != manager.start_data['no_type'],
               on_click=on_clear),
        TextInput('input', on_success=on_input),
        state=ChangeStates.START
    ),
    Window(
        Format('хорошо, но у меня не сохранён твой {start_data[no_type]}. '
               'Для того, чтобы проверить твой новый {start_data[input_type]} мне нужно, '
               'чтобы ты ввёл {start_data[no_type]}. Я не буду сохранять то, что ты введёшь.'),
        TextInput('no_saved_data_input', on_success=on_input_no_data),
        state=ChangeStates.NO_SAVED_DATA_INPUT
    ),
    Window(
        Format('{dialog_data[status]}'),
        Cancel(Format('{dialog_data[cancel_text]}')),
        state=ChangeStates.STATUS
    )
)
