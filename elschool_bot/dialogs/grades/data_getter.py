from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Window, Dialog
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Format


class DataGetterStates(StatesGroup):
    INPUT_FIRST = State()
    INPUT_SECOND = State()


dialog = Dialog(
    Window(
        Format('{start_data[text]}, введи {start_data[input_data][0]}'),
        TextInput('input_first'),
        state=DataGetterStates.INPUT_FIRST
    ),
    Window(
        Format('теперь введи {start_data[input_data][1]}'),
        state=DataGetterStates.INPUT_SECOND
    )
)
