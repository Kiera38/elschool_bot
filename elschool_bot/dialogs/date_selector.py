import datetime

from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import SwitchTo, Button, Group, Multiselect, Cancel
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.widgets.ru_range_calendar import RuRangeCalendar


class DateSelectorStates(StatesGroup):
    SELECT_VARIANT = State()
    SELECT_MONTHS = State()
    SELECT_DATE_RANGE = State()


async def on_select_current_week(event, button, manager: DialogManager):
    today = datetime.date.today()
    week_day = today.weekday()
    start_week_day = today - datetime.timedelta(days=week_day)
    end_week_day = start_week_day + datetime.timedelta(days=7)
    await manager.done({'start': start_week_day, 'end': end_week_day})


async def on_select_months(event, button, manager: DialogManager):
    months = manager.find('select_months').get_checked()
    await manager.done({'months': months})


async def on_cancel_date_range(event, button, manager: DialogManager):
    manager.find('select_date_range').cancel_selected()


async def on_select_date_range(event, button, manager: DialogManager):
    start_date, end_date = manager.find('select_date_range').get_date_range()
    await manager.done({'start': start_date, 'end': end_date})


async def on_start(data, manager: DialogManager):
    if data is not None:
        if 'months' in data:
            select_months = manager.find('select_months')
            for month in data['months']:
                await select_months.set_checked(month, True)
        else:
            start = data['start']
            end = data['end']
            await manager.find('select_date_range').set_date_range(start, end)


async def on_cancel_months(event, button, manager: DialogManager):
    await manager.find('select_months').reset_checked()


dialog = Dialog(
    Window(
        Const('выбери даты'),
        SwitchTo(Const('выбрать месяцы'), 'switch_to_months', DateSelectorStates.SELECT_MONTHS),
        Button(Const('текущая неделя'), 'select_week', on_select_current_week),
        SwitchTo(Const('диапазон дат'), 'switch_to_date_range', DateSelectorStates.SELECT_DATE_RANGE),
        Cancel(Const('отмена'), result='clear_dates'),
        state=DateSelectorStates.SELECT_VARIANT
    ),
    Window(
        Const('выбери месяцы'),
        Group(
            Multiselect(
                Format('✓ {item}'),
                Format('{item}'),
                'select_months',
                lambda item: item,
                ['январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
                 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']
            ),
            width=3
        ),
        Button(Const('сбросить'), 'cancel_months', on_cancel_months),
        Button(Const('готово'), 'complete_select_months', on_select_months),
        Cancel(Const('отмена'), result='clear_dates'),
        state=DateSelectorStates.SELECT_MONTHS
    ),
    Window(
        Const('выбери диапазон дат'),
        RuRangeCalendar('select_date_range'),
        Button(Const('сбросить'), 'cancel_date_range', on_cancel_date_range),
        Button(Const('готово'), 'complete_select_date_range'),
        Cancel(Const('отмена'), result='clear_dates'),
        state=DateSelectorStates.SELECT_DATE_RANGE
    ),
    on_start=on_start
)
