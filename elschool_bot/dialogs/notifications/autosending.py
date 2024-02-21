from enum import Enum

from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Column, Select, Row, Checkbox, SwitchTo, Group, Radio, Cancel
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.dialogs.grades import start_get_grades, process_result
from elschool_bot.repository import Repo
from elschool_bot.widgets import grades_select
from elschool_bot.windows import select_lessons, status


class SchedulerStates(StatesGroup):
    SCHEDULES_LIST = State()
    SCHEDULE_GRADES_SELECT = State()
    SELECT_LESSONS = State()
    SELECT_DATE = State()
    SELECT_WHEN = State()
    STATUS = State()
    INPUT_CUSTOM_TIME = State()
    INPUT_NAME = State()


class ShowModes(Enum):
    DEFAULT = 0
    STATISTICS = 1


class Intervals(Enum):
    DAY = 0
    WEEK = 1
    MONTH = 2
    QUARTER = 3


async def show(manager: DialogManager):
    repo: Repo = manager.middleware_data['repo']
    schedules = await repo.schedule_names(manager.event.from_user.id)
    await manager.start(SchedulerStates.SCHEDULES_LIST, schedules)


async def on_new(query, button, manager: DialogManager):
    manager.dialog_data.update(new=True, checked_date='')
    await grades_select.on_start(manager)
    await manager.switch_to(SchedulerStates.STATUS)
    grades = await start_get_grades(manager)
    if grades is not None:
        await start_select(grades, manager)


async def start_select(grades, manager: DialogManager):
    lessons = [{'id': i, 'text': name} for i, name in enumerate(grades)]
    manager.dialog_data['lessons'] = lessons
    manager.dialog_data['checked_date'] = ''
    if 'status' in manager.dialog_data:
        del manager.dialog_data['status']
    await manager.switch_to(SchedulerStates.SCHEDULE_GRADES_SELECT)


async def select_schedule(query, manager: DialogManager, item, grades):
    item = int(item)
    repo: Repo = manager.middleware_data['repo']
    scheduler = manager.middleware_data['notifications']
    scheduler.remove_id_task(query.from_user.id, item)
    _, _, name, next_time, interval, show_mode, lessons, dates, marks, show_without_marks = await repo.get_schedule(
        query.from_user.id, item)
    manager.dialog_data['schedule_next_time'] = next_time
    show_mode = ShowModes(show_mode)

    if show_mode == ShowModes.DEFAULT:
        await manager.find('show_format').set_checked('список')
    else:
        await manager.find('show_format').set_checked('статистика')

    if lessons != 'all':
        select_lessons = manager.find('select_lessons')
        for lesson in lessons.split(','):
            await select_lessons.set_checked(lesson, True)

    in_time = manager.find('in_time')
    if in_time in ('12_00', '15_00', '18_00'):
        await in_time.set_checked(next_time)
    else:
        await in_time.set_checked('other')
        manager.dialog_data['custom_time'] = next_time.replace('_', ':')

    if interval != -1:
        await manager.find('loop').set_checked(True)
        await manager.find('interval').set_checked(str(interval))

    marks_selector = manager.find('marks_selector')
    for mark in marks.split(','):
        await marks_selector.set_checked(mark, True)

    if dates is not None:
        await manager.find('mark_date_select').set_checked(dates)

    manager.find('input_name').set_widget_data(manager, name)
    await grades_select.set_show_without_marks(manager)

    await start_select(grades, manager)


async def on_select_schedule(query, select, manager: DialogManager, item):
    await manager.switch_to(SchedulerStates.STATUS)
    manager.dialog_data['schedule_id'] = item
    grades = await start_get_grades(manager)
    if grades:
        await select_schedule(query, manager, item, grades)


async def on_process_result(start_data, result, manager: DialogManager):
    if manager.dialog_data.get('new'):
        grades = await process_result(start_data, result, manager)
        if grades:
            await manager.switch_to(SchedulerStates.SCHEDULE_GRADES_SELECT)
    if manager.dialog_data.get('schedule_id'):
        grades = await process_result(start_data, result, manager)
        if grades:
            await select_schedule(manager.event, manager, manager.dialog_data['schedule_id'], grades)


async def on_cancel_schedule(query, button, manager: DialogManager):
    manager.dialog_data.clear()
    if id := manager.dialog_data.get('schedule_id'):
        scheduler = manager.middleware_data['notifications']
        next_time = manager.dialog_data['schedule_next_time']
        scheduler.add_grades_task(manager, next_time, id)


async def on_save_schedule(query, button, manager: DialogManager):
    user_id = manager.event.from_user.id
    next_time = manager.find('in_time').get_checked()
    if next_time is None:
        await status.update(manager, 'не выбрано время отправки')
        return
    if next_time == 'other':
        next_time = manager.dialog_data['custom_time'].replace(':', '_')

    if manager.find('loop').is_checked():
        interval = int(manager.find('interval').get_checked())
    else:
        interval = -1

    if grades_select.is_statistics_checked(manager):
        show_mode = ShowModes.STATISTICS
    else:
        show_mode = ShowModes.DEFAULT

    if manager.find('select_all').is_checked():
        lessons = 'all'
    else:
        lessons = ','.join(manager.find('select_lessons').get_checked())

    marks = ','.join(manager.find('marks_selector').get_checked())
    dates = manager.find('mark_date_select').get_checked()
    if dates is not None:
        dates = int(dates)
    name = manager.find('input_name').get_value()

    show_without_marks = grades_select.is_show_without_marks_checked(manager)

    repo: Repo = manager.middleware_data['repo']
    if manager.dialog_data.get('new'):
        id = await repo.save_schedule(user_id, name, next_time, interval,
                                      show_mode.value, lessons, dates, marks, show_without_marks)
        manager.start_data[:] = await repo.schedule_names(user_id)
        del manager.dialog_data['new']
    else:
        id = int(manager.dialog_data['schedule_id'])
        await repo.update_schedule(user_id, id, name, next_time, interval,
                                   show_mode.value, lessons, dates, marks, show_without_marks)
    scheduler = manager.middleware_data['notifications']
    scheduler.add_id_task(manager, next_time, id)
    status.set(manager, 'отправка сохранена')
    await manager.switch_to(SchedulerStates.STATUS)


async def on_delete(query, button, manager: DialogManager):
    repo: Repo = manager.middleware_data['repo']
    await repo.remove_schedule(query.from_user.id, manager.dialog_data['schedule_id'])
    scheduler = manager.middleware_data['notifications']
    scheduler.remove_id_task(query.from_user.id, manager.dialog_data['schedule_id'])
    manager.start_data[:] = await repo.schedule_names(query.from_user.id)
    await manager.switch_to(SchedulerStates.SCHEDULES_LIST)


async def on_back(query, button, manager: DialogManager):
    await manager.switch_to(SchedulerStates.SCHEDULES_LIST)


async def on_input_name(message, text_input, manager: DialogManager, input_message):
    await manager.switch_to(SchedulerStates.SCHEDULE_GRADES_SELECT)


async def on_input_custom_time(message, text_input, manager: DialogManager, input_message):
    await manager.switch_to(SchedulerStates.SELECT_WHEN)
    manager.dialog_data['custom_time'] = input_message


async def on_in_time_state_changed(event, select, manager: DialogManager, item):
    if item == 'other':
        await manager.switch_to(SchedulerStates.INPUT_CUSTOM_TIME)
    elif 'custom_time' in manager.dialog_data:
        del manager.dialog_data['custom_time']

    if 'status' in manager.dialog_data:
        del manager.dialog_data['status']


async def on_cancel_date(query, button, manager: DialogManager):
    manager.find('mark_date_select').set_widget_data(manager, None)


async def getter(dialog_manager: DialogManager, **kwargs):
    dialog_data = dialog_manager.dialog_data
    if custom_time := dialog_data.get('custom_time'):
        return {'custom_time': f'сейчас выбрано{custom_time}'}
    return {'custom_time': ''}


async def select_getter(dialog_manager: DialogManager, **kwargs):
    dialog_data = dialog_manager.dialog_data
    if status := dialog_data.get('status'):
        return {'status': status}
    return {'status': 'настройка отправки'}


dialog = Dialog(
    Window(
        Const('Выбери, какую отправку хочешь изменить, удалить или добавить новую'),
        Row(
            Button(Const('новая отправка'), 'new', on_new),
            Cancel(Const('назад'))
        ),
        Column(Select(
            Format('{item[1]}'),
            'select',
            lambda item: item[0],
            F['start_data'],
            on_click=on_select_schedule
        )),
        state=SchedulerStates.SCHEDULES_LIST
    ),
    Window(
        Format('{status}'),
        Row(
            SwitchTo(Const('название'), 'name', SchedulerStates.INPUT_NAME),
            SwitchTo(Const('показывать'), 'when_show', SchedulerStates.SELECT_WHEN),
        ),
        *grades_select.create(SchedulerStates.SELECT_LESSONS, False),
        Row(
            SwitchTo(Const('отмена'), 'cancel', SchedulerStates.SCHEDULES_LIST, on_cancel_schedule),
            Button(Const('удалить'), 'delete', when=~F['dialog_data'].get('new'), on_click=on_delete),
            Button(Const('сохранить'), 'save', on_click=on_save_schedule)
        ),
        state=SchedulerStates.SCHEDULE_GRADES_SELECT,
        getter=select_getter
    ),
    select_lessons.create(SchedulerStates.SELECT_LESSONS, SchedulerStates.SCHEDULE_GRADES_SELECT),
    Window(
        Const('выбери, за какое время показывать оценки относительно дня отправки'),
        Radio(Format('✓ {item[1]}'), Format('{item[1]}'), 'mark_date_select', lambda item: item[0],
              [(0, 'день'), (1, 'неделя'), (2, 'месяц')]),
        Button(Const('сбросить'), 'cancel_date', on_cancel_date),
        SwitchTo(Const('назад'), '', SchedulerStates.SCHEDULE_GRADES_SELECT),
        state=SchedulerStates.SELECT_DATE
    ),
    Window(
        Format('выбери, когда показывать {custom_time}'),
        Radio(
            Format('✓ {item}'),
            Format('{item}'),
            'in_time',
            lambda item: item.replace(':', '_').replace('другое', 'other'),
            ['12:00', '15:00', '18:00', 'другое'],
            on_state_changed=on_in_time_state_changed
        ),
        Checkbox(Const('✓ повторять'), Const('повторять'), 'loop'),
        Group(
            Radio(
                Format('✓ {item[1]}'),
                Format('{item[1]}'),
                'interval',
                lambda item: item[0],
                [(0, 'каждый день'), (1, 'раз в неделю'), (2, 'раз в месяц')],
                when=lambda data, radio, manager: manager.find('loop').is_checked()
            ),
            width=2
        ),
        SwitchTo(Const('назад'), 'back_from', SchedulerStates.SCHEDULE_GRADES_SELECT),
        state=SchedulerStates.SELECT_WHEN,
        getter=getter
    ),
    status.create(
        SchedulerStates.STATUS,
        SwitchTo(
            Const('к списку отправок'),
            'to_schedules_list',
            SchedulerStates.SCHEDULES_LIST
        )
    ),
    Window(
        Const('введи время в формате часы:минуты, когда нужно мне отправить'),
        TextInput('input_custom_time', on_success=on_input_custom_time),
        state=SchedulerStates.INPUT_CUSTOM_TIME
    ),
    Window(
        Const('веди новое название для отправки'),
        TextInput('input_name', on_success=on_input_name),
        state=SchedulerStates.INPUT_NAME
    ),
    on_process_result=on_process_result
)
