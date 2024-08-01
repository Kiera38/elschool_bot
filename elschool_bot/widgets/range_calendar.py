from datetime import date
from time import mktime
from typing import Union, Optional, List, Dict

from aiogram.types import InlineKeyboardButton
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common import WhenCondition, ManagedWidget
from aiogram_dialog.widgets.kbd.calendar_kbd import (
    OnDateSelected,
    CalendarConfig,
    CalendarDaysView,
    DATE_TEXT,
    TODAY_TEXT,
    WEEK_DAY_TEXT,
    DAYS_HEADER_TEXT,
    ZOOM_OUT_TEXT,
    NEXT_MONTH_TEXT,
    PREV_MONTH_TEXT,
    Calendar,
)
from aiogram_dialog.widgets.widget_event import (
    WidgetEventProcessor,
    ensure_event_processor,
)


def _is_date_selected(cur_date, data):
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    if start_date is None and end_date is None:
        return False
    if start_date is None:
        return cur_date == end_date
    if end_date is None:
        return cur_date == start_date
    return start_date <= cur_date <= end_date


class RangeCalendarDaysView(CalendarDaysView):
    def __init__(
        self,
        callback_generator,
        config,
        date_text=DATE_TEXT,
        today_text=TODAY_TEXT,
        selected_date_text=None,
        selected_today_text=None,
        weekday_text=WEEK_DAY_TEXT,
        header_text=DAYS_HEADER_TEXT,
        zoom_out_text=ZOOM_OUT_TEXT,
        next_month_text=NEXT_MONTH_TEXT,
        prev_month_text=PREV_MONTH_TEXT,
    ):
        super().__init__(
            callback_generator,
            config,
            date_text,
            today_text,
            weekday_text,
            header_text,
            zoom_out_text,
            next_month_text,
            prev_month_text,
        )
        if selected_date_text is None:
            selected_date_text = "✓" + date_text
        if selected_today_text is None:
            selected_today_text = "✓" + today_text
        self.selected_date_text = selected_date_text
        self.selected_today_text = selected_today_text

    async def _render_date_button(
        self,
        selected_date: date,
        today: date,
        data: Dict,
        manager: DialogManager,
    ) -> InlineKeyboardButton:
        current_data = {
            "date": selected_date,
            "data": data,
        }
        if selected_date == today:
            if _is_date_selected(selected_date, data):
                text = self.selected_today_text
            else:
                text = self.today_text
        else:
            if _is_date_selected(selected_date, data):
                text = self.selected_date_text
            else:
                text = self.date_text
        raw_date = int(mktime(selected_date.timetuple()))
        return InlineKeyboardButton(
            text=await text.render_text(
                current_data,
                manager,
            ),
            callback_data=self.callback_generator(str(raw_date)),
        )


class RangeCalendar(Calendar):
    def __init__(
        self,
        id: str,
        on_click: Union[OnDateSelected, WidgetEventProcessor, None] = None,
        on_range_selected=None,
        config: Optional[CalendarConfig] = None,
        when: WhenCondition = None,
    ) -> None:
        super().__init__(id, on_click, config, when)
        self.on_range_selected = ensure_event_processor(on_range_selected)

    def cancel_selected(self, manager):
        data = self.get_widget_data(manager, {})
        data["start_date"] = None
        data["end_date"] = None

    def get_start_date(self, manager):
        data = self.get_widget_data(manager, {})
        return data.get("start_date")

    def get_end_date(self, manager):
        data = self.get_widget_data(manager, {})
        return data.get("end_date")

    def get_date_range(self, manager):
        data = self.get_widget_data(manager, {})
        return data.get("start_date"), data.get("end_date")

    async def set_date_range(self, manager, start_date, end_date):
        if start_date is not None and end_date is not None:
            assert start_date <= end_date
            await self.on_range_selected.process_event(
                manager.event, self, manager, start_date, end_date
            )
        data = self.get_widget_data(manager, {})
        data["start_date"] = start_date
        data["end_date"] = end_date

    async def _render_keyboard(
        self,
        data,
        manager: DialogManager,
    ) -> List[List[InlineKeyboardButton]]:
        start_date, end_date = self.get_date_range(manager)
        data = {"start_date": start_date, "end_date": end_date, "data": data}
        return await super()._render_keyboard(data, manager)

    async def _handle_click_date(
        self,
        data: str,
        manager: DialogManager,
    ) -> None:
        await super()._handle_click_date(data, manager)
        raw_date = int(data)
        selected_date = date.fromtimestamp(raw_date)
        start_date, end_date = self.get_date_range(manager)
        if start_date is None:
            start_date = selected_date
        elif end_date is None:
            end_date = max(start_date, selected_date)
            start_date = min(start_date, selected_date)
        elif selected_date < start_date:
            start_date = selected_date
        elif selected_date - start_date < end_date - selected_date:
            start_date = selected_date
        else:
            end_date = selected_date

        await self.set_date_range(manager, start_date, end_date)

    def managed(self, manager: DialogManager) -> "ManagedRangeCalendar":
        return ManagedRangeCalendar(self, manager)


class ManagedRangeCalendar(ManagedWidget[RangeCalendar]):
    def cancel_selected(self):
        self.widget.cancel_selected(self.manager)

    def get_start_date(self):
        return self.widget.get_start_date(self.manager)

    def get_end_date(self):
        return self.widget.get_end_date(self.manager)

    def get_date_range(self):
        return self.widget.get_date_range(self.manager)

    async def set_date_range(self, start_date, end_date):
        await self.widget.set_date_range(self.manager, start_date, end_date)
