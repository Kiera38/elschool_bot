from typing import Dict

from aiogram_dialog.widgets.kbd import CalendarScope
from aiogram_dialog.widgets.kbd.calendar_kbd import (
    CalendarScopeView,
    CalendarMonthView,
    CalendarYearsView,
)
from aiogram_dialog.widgets.text import Format

from elschool_bot.widgets.range_calendar import RangeCalendar, RangeCalendarDaysView
from elschool_bot.widgets.ru_calendar import WeekDay, Month


class RuRangeCalendar(RangeCalendar):
    def _init_views(self) -> Dict[CalendarScope, CalendarScopeView]:
        return {
            CalendarScope.DAYS: RangeCalendarDaysView(
                self._item_callback_data,
                self.config,
                weekday_text=WeekDay(),
                header_text=Month() + Format("{date: %Y}"),
                prev_month_text="<< " + Month(),
                next_month_text=Month() + " >>",
            ),
            CalendarScope.MONTHS: CalendarMonthView(
                self._item_callback_data,
                self.config,
                month_text=Month(),
                this_month_text="[" + Month() + "]",
            ),
            CalendarScope.YEARS: CalendarYearsView(
                self._item_callback_data, self.config
            ),
        }
