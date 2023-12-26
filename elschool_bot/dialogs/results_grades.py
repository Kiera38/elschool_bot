from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import DialogManager, Dialog, Window, ShowMode
from aiogram_dialog.widgets.text import Format

from elschool_bot.dialogs import grades
from elschool_bot.repository import Repo, RegisterError
from elschool_bot.windows import status


class ResultsGradesStates(StatesGroup):
    STATUS = State()


async def start(manager: DialogManager):
    repo: Repo = manager.middleware_data['repo']
    await manager.start(ResultsGradesStates.STATUS)
    results = await get_results(manager, repo)
    if results is None:
        return
    await show_results(manager, results)


async def show_results(manager, results):
    text = ['итоговые оценки:']
    marks_count = {}
    for lesson, marks in results.items():
        text.append(f'<b>{lesson}</b>:')
        need_new_line = False
        for name, mark in marks.items():
            if mark:
                text.append(f'{name}: <b>{mark}</b>')
                need_new_line = True
            if name not in marks_count:
                marks_count[name] = {2: 0, 3: 0, 4: 0, 5: 0, None: 0}
            marks_count[name][mark] += 1
        if need_new_line:
            text[-1] = text[-1] + '\n'

    count_text = []
    for name, marks in marks_count.items():
        if marks[2] == 0 and marks[3] == 0 and marks[4] == 0 and marks[5] == 0:
            continue
        name_text = [f'за <u>{name}</u> у вас:']
        for mark, count in marks.items():
            if mark is None:
                name_text.append(f'ещё <b>нет</b> итоговых оценок по <b>{count}</b> предметам')
                continue
            if count:
                name_text.append(f'<b>{count}</b> - "{mark}"')
            else:
                name_text.append(f'<b>нет</b> "{mark}"')
        count_text.append('\n'.join(name_text))
    text = '\n'.join(text)
    await status.update(manager, '\n\n'.join(count_text)+'\n\n'+text, ShowMode.EDIT)


async def get_results(manager, repo):
    try:
        results = await repo.get_results(manager.event.from_user.id)
    except RegisterError as e:
        if await grades.handle_register_error(manager, repo, e):
            return await get_results_after_error(manager, repo)
    else:
        return results


async def get_results_after_error(manager, repo):
    await status.update(manager, 'данные введены правильно, теперь попробую получить оценки')
    try:
        results = await repo.get_results(manager.event.from_user.id)
    except RegisterError as e:
        status_text = manager.dialog_data['status']
        message = e.args[0]
        await status.update(manager, f'{status_text}\n{message}')
    else:
        return results


async def on_process_result(start_data, result, manager):
    if await grades.process_results_without_grades(start_data, result, manager):
        results = await get_results_after_error(manager, manager.middleware_data['repo'])
        await show_results(manager, results)


async def getter(dialog_manager, **kwargs):
    status = dialog_manager.dialog_data.get('status')
    if status:
        return {'status': status}
    return {'status': 'получение информации'}


dialog = Dialog(
    Window(Format('{status}'), state=ResultsGradesStates.STATUS, getter=getter),
    on_process_result=on_process_result
)
