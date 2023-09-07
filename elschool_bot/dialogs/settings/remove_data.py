from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Row, Button, Cancel
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import Repo


class RemoveDataStates(StatesGroup):
    ALL_DATA = State()
    ONE_DATA = State()
    NO_DATA = State()
    CONFIRM = State()
    STATUS = State()


async def start(manager: DialogManager):
    repo: Repo = manager.middleware_data['repo']
    login, password, jwtoken = await repo.get_user_data_jwtoken(manager.event.from_user.id)
    if login is None and password is None:
        await manager.start(RemoveDataStates.NO_DATA, {'login': login, 'password': password, 'jwtoken': jwtoken})
    elif login is None:
        await manager.start(RemoveDataStates.ONE_DATA,
                            {'data_type': 'пароль', 'jwtoken': jwtoken, 'login': login, 'password': password})
    elif password is None:
        await manager.start(RemoveDataStates.ONE_DATA,
                            {'data_type': 'логин', 'jwtoken': jwtoken, 'password': password,'login': login})
    else:
        await manager.start(RemoveDataStates.ALL_DATA,
                            {'login': login, 'password': password, 'jwtoken': jwtoken})


async def remove(remove_type, remove_message, manager: DialogManager):
    manager.dialog_data.update(remove_type=remove_type, remove_message=remove_message)
    await manager.switch_to(RemoveDataStates.CONFIRM)


async def on_remove_login(query, button, manager: DialogManager):
    await remove('логин', 'Ты всё ещё сможешь получать оценки. До обновления токена.', manager)


async def on_remove_password(query, button, manager: DialogManager):
    await remove('пароль', 'Ты всё ещё сможешь получать оценки. До обновления токена.', manager)


async def on_remove_all(query, button, manager: DialogManager):
    await remove('всё', 'Ты всё ещё сможешь получать оценки. До обновления токена.', manager)


async def on_remove_full(query, button, manager: DialogManager):
    await remove('полностью',
                 'Абсолютно все данные о тебе будут удалены. Ты больше не сможешь получать оценки.', manager)


async def on_remove_one(query, button, manager: DialogManager):
    remove_type = manager.start_data['data_type']
    await remove(remove_type, 'Ты всё ещё сможешь получать оценки. До обновления токена.', manager)


async def on_confirm(query, button, manager: DialogManager):
    remove_type = manager.dialog_data['remove_type']
    repo: Repo = manager.middleware_data['repo']
    login = manager.start_data['login']
    password = manager.start_data['password']
    jwtoken = manager.start_data['jwtoken']
    user_id = manager.event.from_user.id
    if remove_type == 'логин':
        await repo.update_data(user_id, jwtoken, password=password)
        status = ('удалил твой логин. Но ты всё ещё можешь получать оценки. Когда elschool обновит токен, я просто '
                  'спрошу у тебя спрошу логин и не буду его сохранять.')
    elif remove_type == 'пароль':
        await repo.update_data(user_id, jwtoken, login)
        status = ('удалил твой пароль. Но ты всё ещё можешь получать оценки. Когда elschool обновит токен, я просто '
                  'спрошу у тебя спрошу пароль и не буду его сохранять.')
    elif remove_type == 'всё':
        await repo.update_data(user_id, jwtoken)
        status = ('удалил твой логин и пароль. Но ты всё ещё можешь получать оценки. Когда elschool обновит токен, '
                  'я просто спрошу у тебя спрошу логин и пароль и не буду его сохранять.')
    else:
        await repo.delete_data(user_id)
        status = 'удалил все твои данные. Ты больше не можешь получать оценки.'
    manager.dialog_data['status'] = status
    await manager.switch_to(RemoveDataStates.STATUS)


dialog = Dialog(
    Window(
        Const('выбери, что хочешь удалить'),
        Row(
            Button(Const('удалить логин'), 'delete_login', on_remove_login),
            Button(Const('удалить пароль'), 'delete_password', on_remove_password),
        ),
        Row(
            Button(Const('удалить всё'), 'delete_all', on_remove_all),
            Button(Const('удалить полностью'), 'delete_full', on_remove_full)
        ),
        Cancel(Const('отмена')),
        state=RemoveDataStates.ALL_DATA
    ),
    Window(
        Const('выбери, что хочешь удалить'),
        Button(Format('удалить {start_data[data_type]}'), 'delete_one', on_remove_one),
        Button(Const('удалить полностью'), 'delete_one_full', on_remove_full),
        Cancel(Const('отмена')),
        state=RemoveDataStates.ONE_DATA
    ),
    Window(
        Const('удалить полностью'),
        Button(Const('удалить полностью'), 'delete_one_full', on_remove_full),
        Cancel(Const('отмена')),
        state=RemoveDataStates.NO_DATA
    ),
    Window(
        Format('Уверен, что хочешь удалить {dialog_data[remove_type]}. {dialog_data[remove_message]}'),
        Row(
            Button(Const('удалить'), 'confirm_delete', on_confirm),
            Cancel(Const('не надо'))
        ),
        state=RemoveDataStates.CONFIRM
    ),
    Window(
        Format('{dialog_data[status]}'),
        Cancel(Const('в настройки')),
        state=RemoveDataStates.STATUS)
)
