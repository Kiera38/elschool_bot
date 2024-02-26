from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Checkbox, Radio, Group, SwitchTo, ManagedCheckbox
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.dialogs.notifications import scheduler, autosending
from elschool_bot.repository import Repo


class NotificationStates(StatesGroup):
    MAIN = State()
    SELECT_TIME_SCHEDULE = State()
    INPUT_CUSTOM_TIME = State()
    STATUS = State()


async def show(manager: DialogManager):
    await manager.start(NotificationStates.MAIN)


async def on_autosend_grades(event, button, manager: DialogManager):
    await autosending.show(manager)


async def on_autosend_schedule(event, button, manager: DialogManager):
    repo: Repo = manager.middleware_data['repo']
    time, interval = await repo.get_user_autosend_schedule(event.from_user.id)
    autosend_schedule = manager.find('autosend_schedule')
    in_time = manager.find('in_time')
    loop = manager.find('loop')
    if time:
        await autosend_schedule.set_checked(True)
        if time in ('12:00', '15:00', '18:00'):
            await in_time.set_checked(time.replace(':', '_'))
        else:
            await in_time.set_checked('other')
            manager.dialog_data['autosend_schedule_time'] = time

        if interval is not None and interval != -1:
            await loop.set_checked(True)
            await manager.find('interval').set_checked(interval)
        else:
            await loop.set_checked(False)
    else:
        await autosend_schedule.set_checked(False)
        await loop.set_checked(False)

    await manager.switch_to(NotificationStates.SELECT_TIME_SCHEDULE)


async def on_save_autosend_schedule(event, button, manager: DialogManager):
    autosend_schedule = manager.find('autosend_schedule')
    in_time = manager.find('in_time')
    loop = manager.find('loop')
    time = None
    interval = -1

    if autosend_schedule.is_checked():
        time = in_time.get_checked()
        if time == 'other':
            time = manager.dialog_data['autosend_schedule_time']
        else:
            time = time.replace('_', ':')

        if loop.is_checked():
            interval = manager.find('interval').get_checked()

    repo = manager.middleware_data['repo']
    await repo.set_user_autosend_schedule(event.from_user.id, time, interval)
    await manager.switch_to(NotificationStates.STATUS)


async def on_input_custom_time(event, text_input, manager: DialogManager, text):
    manager.dialog_data['autosend_schedule_time'] = text
    await manager.switch_to(NotificationStates.SELECT_TIME_SCHEDULE)


async def on_start(data, manager: DialogManager):
    repo = manager.middleware_data['repo']
    notify_change_schedule = await repo.get_user_notify_change_schedule(manager.event.from_user.id)
    if notify_change_schedule is None:
        notify_change_schedule = False
    manager.dialog_data['notify_change_schedule'] = notify_change_schedule
    await manager.find('send_when_change').set_checked(notify_change_schedule)


async def on_send_when_change(event, checkbox: ManagedCheckbox, manager: DialogManager):
    is_checked = checkbox.is_checked()
    if is_checked != manager.dialog_data['notify_change_schedule']:
        repo = manager.middleware_data['repo']
        await repo.set_user_notify_change_schedule(event.from_user.id, is_checked)
        manager.dialog_data['notify_change_schedule'] = is_checked


dialog = Dialog(
    Window(
        Const('настройка уведомлений'),
        Button(Const('автоматическая отправка оценок'), 'autosend_grades', on_autosend_grades),
        Button(Const('автоматическая отправка расписания'), 'autosend_schedule_btn', on_autosend_schedule),
        Checkbox(
            Const('✓ отправлять расписание при изменениях'),
            Const('отправлять расписание при изменениях'),
            'send_when_change',
            on_state_changed=on_send_when_change
        ),
        # Checkbox(
        #     Const('✓ отправлять перед уроком'),
        #     Const('отправлять перед уроком'),
        #     'send_before_lesson'
        # ),
        # Checkbox(
        #     Const('✓ отправлять после урока'),
        #     Const('отправлять после урока'),
        #     'send_before_lesson'
        # ),
        # Checkbox(
        #     Const('✓ отправлять перед уроками'),
        #     Const('отправлять перед уроками'),
        #     'send_before_lesson'
        # ),
        # Checkbox(
        #     Const('✓ отправлять после уроков'),
        #     Const('отправлять после уроков'),
        #     'send_before_lesson'
        # ),
        state=NotificationStates.MAIN
    ),
    Window(
        Const('выбери, когда показывать расписание'),
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
        Button(Const('сохранить'), 'save_time_schedule', on_save_autosend_schedule),
        state=NotificationStates.SELECT_TIME_SCHEDULE
    ),
    Window(
        Const('введи время в формате часы:минуты, когда нужно мне отправить'),
        TextInput('input_custom_time', on_success=on_input_custom_time),
        state=NotificationStates.INPUT_CUSTOM_TIME
    ),
    Window(
        Const('отправка расписания сохранена'),
        SwitchTo(Const('назад'), 'back', NotificationStates.MAIN),
        state=NotificationStates.STATUS
    ),
    on_start=on_start
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(scheduler.dialog)
    router.include_router(autosending.dialog)
