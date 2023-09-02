from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Row, Select, Button, Cancel, Group
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import Repo
from elschool_bot.dialogs.input_data import start_register


class ChangeDataStates(StatesGroup):
    HAS_ALL_DATA = State()
    HAS_DATA = State()
    CHECK_SAVE_DATA = State()
    STATUS = State()


async def start_one_change(input_type, no_type, manager: DialogManager):
    if no_type is None or no_type == input_type:
        manager.dialog_data['need_save'] = 'логин', 'пароль'
        repo = manager.middleware_data['repo']
        if input_type == 'логин':
            _, value = await repo.get_user_data(manager.event.from_user.id)
        else:
            value, _ = await repo.get_user_data(manager.event.from_user.id)
        await start_register((input_type,), ('',), manager, value=value)
    else:
        manager.dialog_data['need_save'] = input_type,
        await start_register((input_type, no_type),
                             ('', f'хорошо, но у меня не сохранён твой {no_type}. '
                                  f'Для того, чтобы проверить твой новый {input_type} мне нужен, твой {no_type}'
                                  f'Я не буду его сохранять'), manager)


async def on_change_login_all_data(query, button, manager: DialogManager):
    await start_one_change('логин', None, manager)


async def on_change_password_all_data(query, button, manager: DialogManager):
    await start_one_change('пароль', None, manager)


async def on_change_login(query, button, manager: DialogManager):
    await start_one_change('логин', manager.start_data['no_type'], manager)


async def on_change_password(query, button, manager: DialogManager):
    await start_one_change('пароль', manager.start_data['no_type'], manager)


async def on_select_save_data(query: CallbackQuery, select, dialog_manager: DialogManager, selected_item):
    user_id = query.from_user.id
    repo: Repo = dialog_manager.middleware_data['repo']
    jwtoken = dialog_manager.start_data['jwtoken']
    login = dialog_manager.start_data['login']
    password = dialog_manager.start_data['password']
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


async def on_process_result(start_data, data, manager: DialogManager):
    need_save = manager.dialog_data['need_save']
    repo: Repo = manager.middleware_data['repo']
    jwtoken = data['jwtoken']
    login = data['login']
    password = data['password']
    if len(need_save) == 2:
        await repo.update_data(manager.event.from_user.id, jwtoken, login, password)
    elif need_save[0] == 'логин':
        await repo.update_data(manager.event.from_user.id, jwtoken, login)
    else:
        await repo.update_data(manager.event.from_user.id, jwtoken, password=password)
    await manager.done()


async def on_change_all(query, button, manager: DialogManager):
    manager.dialog_data['need_save'] = 'логин', 'пароль'
    await start_register(('логин', 'пароль'), ('', ''), manager)


async def update_no_data(data, manager: DialogManager):
    await manager.start(ChangeDataStates.CHECK_SAVE_DATA, data)


dialog = Dialog(
    Window(
        Const('у меня есть все твои данные, выбери какие хочешь изменить'),
        Row(
            Button(Const('логин'), 'change_login', on_change_login_all_data),
            Button(Const('пароль'), 'change_password', on_change_password_all_data),
            Button(Const('всё'), 'change_all', on_change_all)
        ),
        Cancel(Const('отмена')),
        state=ChangeDataStates.HAS_ALL_DATA
    ),
    Window(
        Format('у меня есть только {start_data[has_type]}, выбери что хочешь изменить'),
        Row(
            Button(Const('логин'), 'change_login', on_change_login),
            Button(Const('пароль'), 'change_password', on_change_password),
            Button(Const('всё'), 'change_all', on_change_all)
        ),
        Cancel(Const('отмена')),
        state=ChangeDataStates.HAS_DATA
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
    on_process_result=on_process_result
)
