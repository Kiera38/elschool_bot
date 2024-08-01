from datetime import datetime
from typing import Dict

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import CalendarScope
from aiogram_dialog.widgets.kbd.calendar_kbd import (
    CalendarScopeView,
    CalendarDaysView,
    CalendarMonthView,
    CalendarYearsView,
    Calendar,
)
from aiogram_dialog.widgets.text import Text, Format


class WeekDay(Text):
    async def _render_text(self, data, manager: DialogManager) -> str:
        selected_date: datetime.date = data["date"]
        return ("пн", "вт", "ср", "чт", "пт", "сб", "вс")[selected_date.weekday()]


class Month(Text):
    async def _render_text(self, data, manager: DialogManager) -> str:
        selected_date: datetime.date = data["date"]
        return (
            "январь",
            "февраль",
            "март",
            "апрель",
            "май",
            "июнь",
            "июль",
            "август",
            "сентябрь",
            "октябрь",
            "ноябрь",
            "декабрь",
        )[selected_date.month - 1]


class RuCalendar(Calendar):
    def _init_views(self) -> Dict[CalendarScope, CalendarScopeView]:
        return {
            CalendarScope.DAYS: CalendarDaysView(
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
