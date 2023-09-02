from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Back, Cancel, Button
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import RegisterError


class ChangeAllStates(StatesGroup):
    INPUT_LOGIN = State()
    INPUT_PASSWORD = State()
    STATUS = State()
    ERROR = State()


async def on_input_login(message, text_input, manager: DialogManager, text):
    await manager.next()


async def on_input_password(message: Message, text_input, manager: DialogManager, password):
    repo = manager.middleware_data['repo']
    login = manager.find('input_login').get_value()
    manager.dialog_data.update(status='проверка данных: попытка регистрации', cancel_text='отмена')
    await manager.switch_to(ChangeAllStates.STATUS)
    await manager.show()
    try:
        jwtoken = await repo.check_register_user(login, password)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        if e.login is not None and e.password is not None:
            message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
        manager.dialog_data['status'] = f'{status}\n{message}'
        await manager.switch_to(ChangeAllStates.ERROR)
    await repo.update_data(message.from_user.id, jwtoken, login, password)
    await manager.update({'status': 'обновление данных завершено', 'cancel_text': 'в настройки'})


async def on_clear(query: CallbackQuery, button, manager: DialogManager):
    repo = manager.middleware_data['repo']
    login, password, jwtoken = await repo.get_user_data_jwtoken(query.from_user.id)
    await repo.update_data(query.from_user.id, jwtoken)
    manager.dialog_data.update(status='я удалил твои данные, но ты всё ещё можешь получать оценки',
                               cancel_text='в настройки')
    await manager.switch_to(ChangeAllStates.STATUS)


dialog = Dialog(
    Window(
        Const('введи новый логин'),
        Cancel(Const('отмена')),
        Button(Const('больше не храни'), 'clear', on_click=on_clear),
        TextInput('input_login', on_success=on_input_login),
        state=ChangeAllStates.INPUT_LOGIN
    ),
    Window(
        Const('теперь введи новый пароль'),
        Back(Const('назад')),
        TextInput('input_password', on_success=on_input_password),
        state=ChangeAllStates.INPUT_PASSWORD
    ),
    Window(
        Format('{dialog_data[status]}'),
        Cancel(Format('{dialog_data[cancel_text]}')),
        state=ChangeAllStates.STATUS
    )
)
