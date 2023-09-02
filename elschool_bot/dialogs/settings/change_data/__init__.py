from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Row, Select, Start, Button, Cancel, Group, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import Repo, RegisterError, DataProcessError
from .all import ChangeAllStates
from .one import ChangeStates


class ChangeDataStates(StatesGroup):
    HAS_ALL_DATA = State()
    HAS_DATA = State()
    NO_DATA = State()
    INPUT_PASSWORD = State()
    CHECK_SAVE_DATA = State()
    STATUS = State()
    ERROR = State()


async def on_change_login_all_data(query, button, manager: DialogManager):
    await manager.start(ChangeStates.START, {'input_type': 'логин', 'no_type': None})


async def on_change_password_all_data(query, button, manager: DialogManager):
    await manager.start(ChangeStates.START, {'input_type': 'пароль', 'no_type': None})


async def on_change_login(query, button, manager: DialogManager):
    await manager.start(ChangeStates.START, {'input_type': 'логин', 'no_type': manager.start_data['no_type']})


async def on_change_password(query, button, manager: DialogManager):
    await manager.start(ChangeStates.START, {'input_type': 'пароль', 'no_type': manager.start_data['no_type']})


async def on_input_login(message, text_input, manager: DialogManager, text):
    await message.delete()
    if manager.dialog_data.get('status'):
        manager.dialog_data['status'] = 'новый логин получил, теперь можешь попробовать ещё раз'
        await manager.switch_to(ChangeDataStates.ERROR)
        return
    await manager.next()


async def on_input_password(message, text_input, manager: DialogManager, password):
    if message:
        await message.delete()
    if manager.dialog_data.get('status'):
        manager.dialog_data['status'] = 'новый пароль получил, теперь можешь попробовать ещё раз'
        await manager.switch_to(ChangeDataStates.ERROR)
        return
    login = manager.find('input_login').get_value()
    repo = manager.middleware_data['repo']
    manager.dialog_data.update(status='проверка данных: попытка регистрации', cancel_text='отмена')
    await manager.switch_to(ChangeDataStates.STATUS)
    await manager.show()
    try:
        jwtoken = await repo.check_register_user(login, password)
    except RegisterError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        if e.login is not None and e.password is not None:
            message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
        manager.dialog_data['status'] = f'{status}\n{message}'
        await manager.switch_to(ChangeDataStates.ERROR)
    except DataProcessError as e:
        status = manager.dialog_data['status']
        message = e.args[0]
        manager.dialog_data['status'] = f'{status}\n{message}'
        await manager.switch_to(ChangeDataStates.ERROR)
    else:
        manager.dialog_data['jwtoken'] = jwtoken
        await manager.switch_to(ChangeDataStates.CHECK_SAVE_DATA)


async def on_select_save_data(query: CallbackQuery, select, dialog_manager: DialogManager, selected_item):
    user_id = query.from_user.id
    repo: Repo = dialog_manager.middleware_data['repo']
    jwtoken = dialog_manager.dialog_data['jwtoken']
    login = dialog_manager.find('input_login').get_value()
    password = dialog_manager.find('input_password').get_value()
    if selected_item == 'не сохранить':
        await repo.update_data(user_id, jwtoken)
    elif selected_item == 'только логин':
        await repo.update_data(user_id, jwtoken, login)
    elif selected_item == 'только пароль':
        await repo.update_data(user_id, jwtoken, password=password)
    else:
        await repo.update_data(user_id, jwtoken, login, password)
    dialog_manager.dialog_data.update(status='изменение данных завершено', cancel_text='в настройки')
    await dialog_manager.next()


async def on_process_result(data, start_data, manager: DialogManager):
    await manager.done()


async def on_try(query, button, manager: DialogManager):
    password = manager.find('input_password').get_value()
    manager.dialog_data['status'] = None
    await on_input_password(None, None, manager, password)


dialog = Dialog(
    Window(
        Const('у меня есть все твои данные, выбери какие хочешь изменить или удалить'),
        Row(
            Button(Const('логин'), 'change_login', on_change_login_all_data),
            Button(Const('пароль'), 'change_password', on_change_password_all_data),
            Start(Const('всё'), 'change_all', ChangeAllStates.INPUT_LOGIN)
        ),
        Cancel(Const('отмена')),
        state=ChangeDataStates.HAS_ALL_DATA
    ),
    Window(
        Format('у меня есть только {start_data[has_type]}, выбери что хочешь изменить или удалить'),
        Row(
            Button(Const('логин'), 'change_login', on_change_login),
            Button(Const('пароль'), 'change_password', on_change_password),
            Start(Const('всё'), 'change_all', ChangeAllStates.INPUT_LOGIN)
        ),
        Cancel(Const('отмена')),
        state=ChangeDataStates.HAS_DATA
    ),
    Window(
        Const('у меня нет твоих данных, чтобы изменить нужно ввести все. Начни с логина'),
        Cancel(Const('отмена')),
        TextInput('input_login', on_success=on_input_login),
        state=ChangeDataStates.NO_DATA
    ),
    Window(
        Const('теперь пароль'),
        TextInput('input_password', on_success=on_input_password),
        state=ChangeDataStates.INPUT_PASSWORD
    ),
    Window(
        Const('Обычно я получаю всю информацию по токену, но elschool раз в неделю обновляет его. '
              'Чтобы я мог его обновить автоматически, мне нужно сохранить твои данные у себя. '
              'Ты можешь мне запретить сохранять данные. В этом случае при обновлении токена, я спрошу их снова. '
              'Этот параметр можно в будущем изменить.'),
        Group(
            Select(
                Format('{item}'),
                'select_save_data',
                lambda i: i,
                ['сохранить всё', 'не сохранить', 'только логин', 'только пароль'],
                on_click=on_select_save_data
            ),
            width=2
        ),
        state=ChangeDataStates.CHECK_SAVE_DATA
    ),
    Window(
        Format('{dialog_data[status]}'),
        Cancel(Format('{dialog_data[cancel_text]}')),
        state=ChangeDataStates.STATUS
    ),
    Window(
        Format('{dialog_data[status]}'),
        Group(
            SwitchTo(Const('изменить логин'), 'change_login', ChangeDataStates.NO_DATA),
            SwitchTo(Const('изменить пароль'), 'change_password', ChangeDataStates.INPUT_PASSWORD),
            Button(Const('попробовать ещё раз'), 'try', on_try),
            Cancel(Const('попробовать позже')),
            width=2
        ),
        state=ChangeDataStates.ERROR
    ),
    on_process_result=on_process_result
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(all.dialog)
    router.include_router(one.dialog)
