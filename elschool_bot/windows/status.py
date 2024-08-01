from aiogram_dialog import Window, DialogManager
from aiogram_dialog.widgets.text import Format


def create(state, *widgets):
    return Window(create_status_widget(), *widgets, state=state)


def create_status_widget():
    return Format("{dialog_data[status]}")


def set(manager: DialogManager, status: str, **data):
    manager.dialog_data["status"] = status
    manager.dialog_data.update(data)


async def update(manager: DialogManager, status: str, show_mode=None, **data):
    await manager.update({"status": status, **data}, show_mode=show_mode)
