from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram_dialog import Window, Dialog, DialogManager
from aiogram_dialog.widgets.kbd import Select, Button, Group
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import Repo


class RegisterStates(StatesGroup):
    SELECT_QUARTER = State()
    CHECK_SAVE_DATA = State()
    END_REGISTER = State()


async def on_quarter_selected(
    query: CallbackQuery, select, dialog_manager: DialogManager, selected_item
):
    dialog_manager.dialog_data.update({"quarter": selected_item})
    await dialog_manager.next()


async def on_select_save_data(
    query: CallbackQuery, select, dialog_manager: DialogManager, selected_item
):
    user_id = query.from_user.id
    repo: Repo = dialog_manager.middleware_data["repo"]
    jwtoken = dialog_manager.start_data["jwtoken"]
    url = dialog_manager.start_data["url"]
    login = dialog_manager.start_data["login"]
    password = dialog_manager.start_data["password"]
    quarter = dialog_manager.dialog_data["quarter"]
    if selected_item == "не сохранить":
        await repo.register_user(user_id, jwtoken, url, quarter)
    elif selected_item == "только логин":
        await repo.register_user(user_id, jwtoken, url, quarter, login)
    elif selected_item == "только пароль":
        await repo.register_user(user_id, jwtoken, url, quarter, password=password)
    else:
        await repo.register_user(user_id, jwtoken, url, quarter, login, password)
    await dialog_manager.next()


async def to_settings(query, button, manager: DialogManager):
    await manager.done({"status": "регистрация завершена"})


async def register(data, manager: DialogManager):
    data["quarters"] = list(data["grades"].keys())
    await manager.start(RegisterStates.SELECT_QUARTER, data)


dialog = Dialog(
    Window(
        Const(
            "данные введены правильно, теперь выбери какие оценки мне сейчас показывать"
        ),
        Select(
            Format("{item}"),
            "select_quarter",
            lambda i: i,
            items=F["start_data"]["quarters"],
            on_click=on_quarter_selected,
        ),
        state=RegisterStates.SELECT_QUARTER,
    ),
    Window(
        Const(
            "Обычно я получаю всю информацию по токену, но elschool раз в неделю обновляет его. "
            "Чтобы я мог его обновить автоматически, мне нужно сохранить твои данные у себя. "
            "Ты можешь мне запретить сохранять данные. В этом случае при обновлении токена, я спрошу их снова. "
            "Этот параметр можно в будущем изменить."
        ),
        Group(
            Select(
                Format("{item}"),
                "select_save_data",
                lambda i: i,
                ["сохранить всё", "не сохранить", "только логин", "только пароль"],
                on_click=on_select_save_data,
            ),
            width=2,
        ),
        state=RegisterStates.CHECK_SAVE_DATA,
    ),
    Window(
        Const("регистрация завершена, теперь можешь использовать все мои возможности"),
        Button(Const("в настройки"), "to_settings", on_click=to_settings),
        state=RegisterStates.END_REGISTER,
    ),
)
