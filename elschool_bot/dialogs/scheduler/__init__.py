from enum import Enum

from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Column, Select, Row, Checkbox, SwitchTo, Multiselect, Group, Radio
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.dialogs.grades import start_get_grades, process_result
from elschool_bot.dialogs.scheduler import scheduler
from elschool_bot.repository import Repo


class SchedulerStates(StatesGroup):
    SCHEDULES_LIST = State()
    SCHEDULE_GRADES_SELECT = State()
    SELECT_LESSONS = State()
    SELECT_DATE = State()
    SELECT_WHEN = State()
    STATUS = State()


class ShowModes(Enum):
    DEFAULT = 0
    SUMMARY = 1
    DETAIL = 2


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
    marks_selector = manager.find('marks_selector')
    for i in range(2, 6):
        await marks_selector.set_checked(str(i), True)
    await manager.switch_to(SchedulerStates.STATUS)
    grades = await start_get_grades(manager)
    if grades is not None:
        await start_select(grades, manager)


async def start_select(grades, manager: DialogManager):
    lessons = [{'id': i, 'text': name} for i, name in enumerate(grades)]
    manager.dialog_data['lessons'] = lessons
    manager.dialog_data['checked_date'] = ''
    await manager.switch_to(SchedulerStates.SCHEDULE_GRADES_SELECT)


async def select_schedule(query, manager: DialogManager, item, grades):
    item = int(item)
    repo: Repo = manager.middleware_data['repo']
    scheduler = manager.middleware_data['scheduler']
    scheduler.remove_grades_task(query.from_user.id, item)
    _, _, _, next_time, interval, show_mode, lessons, _, marks = await repo.get_schedule(query.from_user.id, item)
    manager.dialog_data['schedule_next_time'] = next_time
    show_mode = ShowModes(show_mode)

    if show_mode == ShowModes.DETAIL:
        await manager.find('detail').set_checked(True)
    elif show_mode == ShowModes.SUMMARY:
        await manager.find('summary').set_checked(True)

    if lessons != 'all':
        select_lessons = manager.find('select_lessons')
        for lesson in lessons.split(','):
            await select_lessons.set_checked(lesson, True)

    in_time = manager.find('in_time')
    await in_time.set_checked(next_time)

    if interval != -1:
        await manager.find('loop').set_checked(True)
        await manager.find('interval').set_checked(str(interval), True)

    marks_selector = manager.find('marks_selector')
    for mark in marks.split(','):
        await marks_selector.set_checked(mark, True)

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
        scheduler = manager.middleware_data['scheduler']
        next_time = manager.dialog_data['schedule_next_time']
        scheduler.add_grades_task(manager, next_time, id)


async def on_save_schedule(query, button, manager: DialogManager):
    user_id = manager.event.from_user.id
    next_time = manager.find('in_time').get_checked()

    if manager.find('loop').is_checked():
        interval = int(manager.find('interval').get_checked())
    else:
        interval = -1

    if manager.find('detail').is_checked():
        show_mode = ShowModes.DETAIL
    elif manager.find('summary').is_checked():
        show_mode = ShowModes.SUMMARY
    else:
        show_mode = ShowModes.DEFAULT

    if manager.find('select_all').is_checked():
        lessons = 'all'
    else:
        lessons = ','.join(manager.find('select_lessons').get_checked())

    marks = ','.join(manager.find('marks_selector').get_checked())

    repo: Repo = manager.middleware_data['repo']
    name = 'отправка'
    if manager.dialog_data.get('new'):
        id = await repo.save_schedule(user_id, name, next_time, interval,
                                      show_mode.value, lessons, None, marks)
        manager.start_data[:] = await repo.schedule_names(user_id)
        del manager.dialog_data['new']
    else:
        id = int(manager.dialog_data['schedule_id'])
        await repo.update_schedule(user_id, id, name + str(id), next_time, interval,
                                   show_mode.value, lessons, None, marks)
    scheduler = manager.middleware_data['scheduler']
    scheduler.add_grades_task(manager, next_time, id)
    manager.dialog_data['status'] = 'отправка сохранена'
    await manager.switch_to(SchedulerStates.STATUS)


async def on_delete(query, button, manager: DialogManager):
    repo: Repo = manager.middleware_data['repo']
    await repo.remove_schedule(query.from_user.id, manager.dialog_data['schedule_id'])
    scheduler = manager.middleware_data['scheduler']
    scheduler.remove_grades_task(query.from_user.id, manager.dialog_data['schedule_id'])
    manager.start_data[:] = await repo.schedule_names(query.from_user.id)
    await manager.switch_to(SchedulerStates.SCHEDULES_LIST)


async def on_select_all(event, checkbox, manager: DialogManager):
    if checkbox.is_checked():
        select_lessons = manager.find('select_lessons')
        await select_lessons.reset_checked()


async def on_selected_lessons_changed(event, select, manager: DialogManager, item_id):
    if select.is_checked(item_id):
        await manager.find('select_all').set_checked(False)


async def on_back(query, button, manager: DialogManager):
    await manager.switch_to(SchedulerStates.SCHEDULES_LIST)


dialog = Dialog(
    Window(
        Const('Выбери, какую отправку хочешь изменить, удалить или добавить новую'),
        Button(Const('новая отправка'), 'new', on_new),
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
        Const('настройка отправки'),
        SwitchTo(Const('показывать'), 'when_show', SchedulerStates.SELECT_WHEN),
        Row(
            Checkbox(Const('✓ кратко'), Const('кратко'), 'summary'),
            Checkbox(Const('✓ подробно'), Const('подробно'), 'detail')
        ),
        Row(
            SwitchTo(
                Format('выбрать из списка'),
                'lessons_picked',
                SchedulerStates.SELECT_LESSONS,
                when=lambda data, widget, manager: not manager.find('summary').is_checked()
            ),
            SwitchTo(
                Format('{dialog_data[checked_date]} дата проставления'),
                'date',
                SchedulerStates.SELECT_DATE,
                when=lambda data, widget, manager: not manager.find('summary').is_checked()
            ),
        ),
        Multiselect(
            Format('✓ {item}'),
            Format('{item}'),
            'marks_selector',
            lambda item: item,
            (5, 4, 3, 2)
        ),
        Row(
            SwitchTo(Const('отмена'), 'cancel', SchedulerStates.SCHEDULES_LIST, on_cancel_schedule),
            Button(Const('удалить'), 'delete', when=~F['dialog_data'].get('new'), on_click=on_delete),
            Button(Const('сохранить'), 'save', on_click=on_save_schedule)
        ),
        state=SchedulerStates.SCHEDULE_GRADES_SELECT
    ),
    Window(
        Const('выбери уроки'),
        Checkbox(
            Format('✓ все'),
            Format('все'),
            'select_all',
            on_state_changed=on_select_all,
            default=True
        ),
        Group(
            Multiselect(
                Format('✓ {item[text]}'),
                Format('{item[text]}'),
                'select_lessons',
                lambda item: item['id'],
                F['dialog_data']['lessons'],
                on_state_changed=on_selected_lessons_changed
            ),
            width=2
        ),
        SwitchTo(Const('назад'), '', SchedulerStates.SCHEDULE_GRADES_SELECT),
        state=SchedulerStates.SELECT_LESSONS
    ),
    Window(
        Const('выбери, за какое время показывать оценки относительно дня отправки'),
        Radio(Format('{item}'), Format('{item}'), 'mark_date_select', lambda item: item[0],
              [(0, 'день'), (1, 'неделя'), (3, 'месяц')]),
        Button(Const('сбросить'), 'cancel_date', ),
        SwitchTo(Const('назад'), '', SchedulerStates.SCHEDULE_GRADES_SELECT),
        state=SchedulerStates.SELECT_DATE
    ),
    Window(
        Const('выбери, когда показывать'),
        Radio(
            Format('✓ {item}'),
            Format('{item}'),
            'in_time',
            lambda item: item.replace(':', '_').replace('другое', 'other'),
            ['12:00', '15:00', '18:00', 'другое'],
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
        state=SchedulerStates.SELECT_WHEN
    ),
    Window(
        Format('{dialog_data[status]}'),
        Button(Const('назад'), 'back', on_back),
        state=SchedulerStates.STATUS
    ),
    on_process_result=on_process_result
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(scheduler.dialog)
