from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Checkbox, Radio, Group
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.dialogs.notifications import scheduler, autosending


class NotificationStates(StatesGroup):
    MAIN = State()


async def show(manager: DialogManager):
    await manager.start(NotificationStates.MAIN)


async def on_autosend_grades(event, button, manager: DialogManager):
    await autosending.show(manager)


dialog = Dialog(
    Window(
        Const('настройка уведомлений'),
        Button(Const('автоматическая отправка оценок'), 'autosend_grades', on_autosend_grades),
        Checkbox(
            Const('✓ отправлять расписание'),
            Const('отправлять расписание'),
            'autosend_schedule'
        ),
        Radio(
            Format('✓ {item}'),
            Format('{item}'),
            'in_time',
            lambda item: item.replace(':', '_').replace('другое', 'other'),
            ['12:00', '15:00', '18:00', 'другое'],
            when=lambda data, radio, manager: manager.find('autosend_schedule').is_checked()
        ),
        Checkbox(Const('✓ повторять'), Const('повторять'), 'loop',
                 when=lambda data, radio, manager: manager.find('autosend_schedule').is_checked()),
        Group(
            Radio(
                Format('✓ {item[1]}'),
                Format('{item[1]}'),
                'interval',
                lambda item: item[0],
                [(0, 'каждый день'), (1, 'раз в неделю'), (2, 'раз в месяц')],
                when=lambda data, radio, manager: (manager.find('loop').is_checked() and
                                                   manager.find('autosend_schedule').is_checked())
            ),
            width=2
        ),
        Checkbox(
            Const('✓ отправлять расписание при изменениях'),
            Const('отправлять расписание при изменениях'),
            'send_when_change'
        ),
        Checkbox(
            Const('✓ отправлять перед уроком'),
            Const('отправлять перед уроком'),
            'send_before_lesson'
        ),
        Checkbox(
            Const('✓ отправлять после урока'),
            Const('отправлять после урока'),
            'send_before_lesson'
        ),
        Checkbox(
            Const('✓ отправлять перед уроками'),
            Const('отправлять перед уроками'),
            'send_before_lesson'
        ),
        Checkbox(
            Const('✓ отправлять после уроков'),
            Const('отправлять после уроков'),
            'send_before_lesson'
        ),
        state=NotificationStates.MAIN
    ),
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(scheduler.dialog)
    router.include_router(autosending.dialog)
