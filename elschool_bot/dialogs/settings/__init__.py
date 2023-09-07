from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import User, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Row, Select
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import Repo
from . import register, remove_data
from .change_data import ChangeDataStates
from ..input_data import start_register


class States(StatesGroup):
    MAIN = State()
    GET_QUARTER_DATA = State()


async def on_result(data, result_data, manager: DialogManager):
    if result_data is None:
        return
    if manager.dialog_data.get('register'):
        del manager.dialog_data['register']
        await register.register(result_data, manager)
        return
    if manager.dialog_data.get('change_data'):
        del manager.dialog_data['change_data']
        await change_data.update_no_data(result_data, manager)
        return
    manager.dialog_data['status'] = result_data.get('status', 'настройки')


async def on_start(start_data, manager: DialogManager):
    manager.dialog_data['status'] = 'настройки'


async def get_data(repo: Repo, event_from_user: User, **kwargs):
    return {
        'registered': await repo.has_user(event_from_user.id)
    }


async def on_edit_data(query: CallbackQuery, button, manager: DialogManager):
    repo = manager.middleware_data['repo']
    login, password = await repo.get_user_data(query.from_user.id)
    if login is not None and password is not None:
        await manager.start(ChangeDataStates.HAS_ALL_DATA)
    elif login is not None:
        await manager.start(ChangeDataStates.HAS_DATA, {'has_type': 'логин', 'no_type': 'пароль'})
    elif password is not None:
        await manager.start(ChangeDataStates.HAS_DATA, {'has_type': 'пароль', 'no_type': 'логин'})
    else:
        manager.dialog_data['change_data'] = True
        await start_register(('логин', 'пароль'),
                             ('у меня нет твоих данных, чтобы изменить нужно ввести все.', ''),
                             manager, ('', ''))


async def on_delete_data(query: CallbackQuery, button, manager: DialogManager):
    await remove_data.start(manager)


async def on_privacy_policy(query, button, manager: DialogManager):
    await manager.update({'status': "Для получения оценок бот использует логин и пароль от журнала elschool. "
                                    "Эти данные используются только для получения токена. "
                                    "Этот токен используется для получения оценок. "
                                    "Есть возможность сохранить данные от аккаунта elschool. "
                                    "Разработчик гарантирует, что данные никто смотреть не будет."})


async def on_version(query, button, manager: DialogManager):
    await manager.update({
        'status': '''моя версия: 3.0.0.dev5

Список изменений:
Это большое обновление. Бот был написан практически с нуля.

Совершенно новый интерфейс. Многие кнопки перемещены в новое меню настройки. На главном экране только самые нужные действия.
Появилась возможность сохранять данные от elschool для автоматического обновления токена регистрации. При этом можно сохранять только часть данных, остальные бот будет спрашивать при обновлении.
Подсказки по исправлению теперь можно посмотреть только после просмотра оценок.
Вместо четверти теперь везде написано часть года. Раньше "четверть" означала четверть или полугодие.

Обновления меню оценки:
Теперь можно выбирать какие именно оценки показывать и как показывать (кратко, обычно, подробно).
Можно выбрать конкретные уроки, дату урока, дату проставления оценки, саму оценку (например только 4).
При этом просто посмотреть все оценки в этой части года (четверти или полугодия) можно всего за 2 нажатия. Раньше для этого требовалось 3 нажатия.

Исправленные ошибки:
Исправлено множество ошибок из старых версий. Улучшена обработка ошибок elschool.
Возможны новые ошибки (эта версия ещё в разработке).'''
    })


async def on_change_quarter(query, button, manager: DialogManager):
    manager.dialog_data.update({'status': 'получение данных', 'quarters': []})
    await manager.switch_to(States.GET_QUARTER_DATA)
    await manager.show()
    repo = manager.middleware_data['repo']
    quarters = await repo.get_quarters(query.from_user.id)
    await manager.update({'status': 'выбери 1 из вариантов', 'quarters': quarters})


async def on_quarter_select(query, select, manager: DialogManager, quarter):
    repo = manager.middleware_data['repo']
    await repo.update_quarter(query.from_user.id, quarter)
    manager.dialog_data['status'] = f'часть года изменена на {quarter}'
    await manager.switch_to(States.MAIN)


async def on_register(query, button, manager: DialogManager):
    manager.dialog_data['register'] = True
    await start_register(('логин', 'пароль'), ('Начнём регистрацию.', ''), manager,
                         ('', ''), check_get_grades=True)


dialog = Dialog(
    Window(
        Format('{dialog_data[status]}'),
        Button(Const('политика конфиденциальности'), 'privacy_policy', on_privacy_policy),
        Button(Const('регистрация'), 'register', on_register, when=~F['registered']),
        Row(
            Button(Const('изменить данные'), 'edit_data', on_edit_data),
            Button(Const('удалить данные', ), 'delete_data', on_click=on_delete_data),
            when='registered'
        ),
        Row(
            Button(Const('версия'), 'version', on_click=on_version),
            Button(Const('изменить часть года'), 'change_quarter', on_click=on_change_quarter)
        ),
        state=States.MAIN
    ),
    Window(
        Format('{dialog_data[status]}'),
        Select(
            Format('{item}'),
            'select_quarter',
            lambda item: item,
            F['dialog_data']['quarters'],
            on_click=on_quarter_select
        ),
        state=States.GET_QUARTER_DATA
    ),
    on_process_result=on_result,
    getter=get_data,
    on_start=on_start
)


def register_handlers(router):
    router.include_router(dialog)
    router.include_router(register.dialog)
    router.include_router(change_data.dialog)
    router.include_router(remove_data.dialog)
