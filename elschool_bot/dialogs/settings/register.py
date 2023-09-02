from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Window, Dialog, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Select, Button, Group, Row, SwitchTo, Cancel
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import Repo, RegisterError, DataProcessError


class RegisterStates(StatesGroup):
    REGISTER = State()
    REGISTER_PASSWORD = State()
    CHECK_DATA = State()
    SELECT_QUARTER = State()
    CHECK_SAVE_DATA = State()
    END_REGISTER = State()
    ERROR = State()


async def on_input_login(message: Message, text_input, dialog_manager: DialogManager, text):
    await message.delete()
    if dialog_manager.dialog_data.get('status'):
        dialog_manager.dialog_data['status'] = 'новый логин получил, теперь можешь попробовать ещё раз'
        await dialog_manager.switch_to(RegisterStates.ERROR)
        return
    await dialog_manager.next()


async def on_input_password(message, text_input, dialog_manager: DialogManager, password):
    if message:
        await message.delete()
    if dialog_manager.dialog_data.get('status'):
        dialog_manager.dialog_data['status'] = 'новый пароль получил, теперь можешь попробовать ещё раз'
        await dialog_manager.switch_to(RegisterStates.ERROR)
        return
    login = dialog_manager.find('input_login').get_value()
    dialog_manager.dialog_data['status'] = 'проверка введённых данных: регистрация'
    await dialog_manager.switch_to(RegisterStates.CHECK_DATA)
    repo: Repo = dialog_manager.middleware_data['repo']
    try:
        jwtoken = await repo.check_register_user(login, password)
        await dialog_manager.update({'status': 'проверка введённых данных: получение оценок'})
        grades, url = await repo.check_get_grades(jwtoken)
    except RegisterError as e:
        status = dialog_manager.dialog_data['status']
        message = e.args[0]
        if e.login is not None and e.password is not None:
            message = f'{e.args[0]}. Твой логин {e.login} и пароль {e.password}?'
        dialog_manager.dialog_data.update({'status': f'{status}\n{message}'})
        await dialog_manager.switch_to(RegisterStates.ERROR)
    except DataProcessError as e:
        status = dialog_manager.dialog_data['status']
        message = e.args[0]
        dialog_manager.dialog_data.update({'status': f'{status}\n{message}'})
        await dialog_manager.switch_to(RegisterStates.ERROR)
    else:
        dialog_manager.dialog_data.update({
            'quarters': list(grades.keys()),
            'url': url,
            'jwtoken': jwtoken
        })
        await dialog_manager.next()


async def on_quarter_selected(query: CallbackQuery, select, dialog_manager: DialogManager, selected_item):
    dialog_manager.dialog_data.update({'quarter': selected_item})
    await dialog_manager.next()


async def on_select_save_data(query: CallbackQuery, select, dialog_manager: DialogManager, selected_item):
    user_id = query.from_user.id
    repo: Repo = dialog_manager.middleware_data['repo']
    jwtoken = dialog_manager.dialog_data['jwtoken']
    url = dialog_manager.dialog_data['url']
    login = dialog_manager.find('input_login').get_value()
    password = dialog_manager.find('input_password').get_value()
    quarter = dialog_manager.dialog_data['quarter']
    if selected_item == 'не сохранить':
        await repo.register_user(user_id, jwtoken, url, quarter)
    elif selected_item == 'только логин':
        await repo.register_user(user_id, jwtoken, url, quarter, login)
    elif selected_item == 'только пароль':
        await repo.register_user(user_id, jwtoken, url, quarter, password=password)
    else:
        await repo.register_user(user_id, jwtoken, url, quarter, login, password)
    await dialog_manager.next()


async def to_settings(query, button, manager: DialogManager):
    await manager.done({'status': 'регистрация завершена'})


async def on_try(query, button, manager: DialogManager):
    password = manager.find('input_password').get_value()
    manager.dialog_data['status'] = None
    await on_input_password(None, None, manager, password)


dialog = Dialog(
    Window(
        Const('Начнём регистрацию. Сначала введи свой логин от elschool'),
        TextInput('input_login', on_success=on_input_login),
        state=RegisterStates.REGISTER
    ),
    Window(
        Const('Хорошо, теперь введи свой пароль.'),
        TextInput('input_password', on_success=on_input_password),
        state=RegisterStates.REGISTER_PASSWORD
    ),
    Window(
        Format('{dialog_data[status]}'),
        state=RegisterStates.CHECK_DATA
    ),
    Window(
        Const('данные введены правильно, теперь выбери какие оценки мне сейчас показывать'),
        Select(
            Format('{item}'),
            'select_quarter',
            lambda i: i,
            items=F['dialog_data']['quarters'],
            on_click=on_quarter_selected
        ),
        state=RegisterStates.SELECT_QUARTER
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
        state=RegisterStates.CHECK_SAVE_DATA
    ),
    Window(
        Const('регистрация завершена, теперь можешь использовать все мои возможности'),
        Button(Const('в настройки'), 'to_settings', on_click=to_settings),
        state=RegisterStates.END_REGISTER
    ),
    Window(
        Format('{dialog_data[status]}'),
        Group(
            SwitchTo(Const('изменить логин'), 'change_login', RegisterStates.REGISTER),
            SwitchTo(Const('изменить пароль'), 'change_password', RegisterStates.REGISTER_PASSWORD),
            Button(Const('попробовать ещё раз'), 'try', on_try),
            Cancel(Const('попробовать позже')),
            width=2
        ),
        state=RegisterStates.ERROR
    )
)
