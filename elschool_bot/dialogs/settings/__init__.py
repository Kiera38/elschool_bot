from aiogram import F
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import User, CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Row, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from elschool_bot.repository import Repo
from . import register, remove_data
from .change_data import ChangeDataStates
from elschool_bot.dialogs import input_data
from elschool_bot.windows import status


class States(StatesGroup):
    MAIN = State()
    GET_QUARTER_DATA = State()
    EDIT_CACHE_TIME = State()


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
    status.set(manager, result_data.get('status', 'настройки'))


async def on_start(start_data, manager: DialogManager):
    status.set(manager, 'настройки')


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
        await input_data.start(('логин', 'пароль'),
                               ('у меня нет твоих данных, чтобы изменить нужно ввести все.', ''),
                               manager, ('', ''))


async def on_delete_data(query: CallbackQuery, button, manager: DialogManager):
    await remove_data.start(manager)


async def on_privacy_policy(query, button, manager: DialogManager):
    await status.update(manager, "Для получения оценок бот использует логин и пароль от журнала elschool. "
                                 "Эти данные используются только для получения токена. "
                                 "Этот токен используется для получения оценок. "
                                 "Есть возможность сохранить данные от аккаунта elschool. "
                                 "Разработчик гарантирует, что данные никто смотреть не будет.")


async def on_version(query, button, manager: DialogManager):
    await status.update(manager, '''моя версия: 3.3.0b1.dev15

Список изменений:
в 3.3.0:
Не забудьте обновить основное меню!
просмотр расписания, просмотр расписания звонков, кривой код. Можно указывать изменения в расписании (считается эксперементальной функцией).
Фильтры при просмотре оценок влияют только на список оценок. Вся статистика, и средние оценки теперь расчитываются до примененния фильтров. 
Больше нет разделения на общую и подробную статистику. При выборе показа статистики можно смотреть и ту и другую.
Меню помощи. Позволяет ознакомится со всеми возможностями бота.
Автоматическая отправка расписания на следующий день в определённое время. 
Автоматическая отправка расписания при сохранении изменений. Расписание отправляется всем пользователям из того же класса что и человек, сохранивший изменения, у которых включена эта функция.
ВНИМАНИЕ! Все новые функции могут работать с ошибками. Если вы нашли ошибку, сообщите разработчику.
Изменения в расписании является эксперементальной возможностью, которая может быть переделана в одном из следующих обновлений. 

в 3.2.0:
Выбор одной даты это конечно хорошо, но ещё лучше выбирать промежуток дат. В этом обновлении теперь можно выбирать промежуток дат, несколько месяцев сразу или просто за всю текущую неделю.
Простой просмотр итоговых оценок. Но для использования нужно не забыть обновить нижнее меню.

в 3.1.1:
Исправления ошибок: 
В подробной статистике писалось в нескольких местах писалось за текущую часть года, но из-за фильтрации это могли быть оценки за более маленький промежуток времени. Теперь там написано из выбранных.
В подробной статистике при пролистывании предметов назад бот мог начать считать, что оценок нет совсем, хотя они были.
Исправлена фильтрация оценок в автоматической отправке, если выбрать промежуток времени, за который нужно показывать оценки.
Изменён текст для показа подсказок по исправлению. Теперь он больше соответствует новому стилю.

в 3.1.0:
Добавлена возможность выбирать конкретный предмет из списка в подробном режиме показа оценок. Просто переключаться на следующий или предыдущий можно как и раньше.
Предметы без оценок теперь скрываются, но это можно настроить.
Статистика оценок. Общая и по каждому предмету.
Меню настройки показа оценок обновлено. Теперь оно более понятно.
Улучшено оформление бота. Теперь в тексте важные части выделены.

в 3.0.1:
Различные исправления ошибок и улучшение кода

в 3.0.0:
Самое большое обновление. Бот был написан практически с нуля.

Совершенно новый интерфейс. Многие кнопки перемещены в новое меню настройки. На главном экране только самые нужные действия.
Появилась возможность сохранять данные от elschool для автоматического обновления токена регистрации. При этом можно сохранять только часть данных, остальные бот будет спрашивать при обновлении.
Подсказки по исправлению теперь можно посмотреть только после просмотра оценок.
Вместо четверти теперь везде написано часть года. Раньше "четверть" означала четверть или полугодие.

Обновления меню оценки:
Теперь можно выбирать какие именно оценки показывать и как показывать (кратко, обычно, подробно).
Можно выбрать конкретные уроки, дату урока, дату проставления оценки, саму оценку (например только 4).
При этом просто посмотреть все оценки в этой части года (четверти или полугодия) можно всего за 2 нажатия. Раньше для этого требовалось 3 нажатия.

Новое меню автоматической отправки:
Появилось новое меню "отправка по времени". В этом меню можно настроить автоматическую отправку оценок в определённое время.
Можно настроить как часто будут отправляться оценки.

Исправленные ошибки:
Исправлено множество ошибок из старых версий. Улучшена обработка ошибок elschool.
''')


async def on_change_quarter(query, button, manager: DialogManager):
    status.set(manager, 'получение данных', quarters=[])
    await manager.switch_to(States.GET_QUARTER_DATA)
    await manager.show()
    repo = manager.middleware_data['repo']
    quarters = await repo.get_quarters(query.from_user.id)
    await status.update(manager, 'выбери 1 из вариантов', quarters=quarters)


async def on_quarter_select(query, select, manager: DialogManager, quarter):
    repo = manager.middleware_data['repo']
    await repo.update_quarter(query.from_user.id, quarter)
    status.set(manager, f'часть года изменена на {quarter}')
    await manager.switch_to(States.MAIN)


async def on_register(query, button, manager: DialogManager):
    manager.dialog_data['register'] = True
    await input_data.start(('логин', 'пароль'), ('Начнём регистрацию.', ''), manager,
                           ('', ''), check_get_grades=True)


async def on_input_cache_time(message, widget, manager: DialogManager, text: str):
    text = text.split()
    try:
        if len(text) == 1:
            text = text[0].split(':')
            if len(text) == 1:
                seconds = int(text[0])
            elif len(text) == 2:
                minutes = int(text[0])
                seconds = int(text[1]) + minutes * 60
            elif len(text) == 3:
                hours = int(text[0])
                minutes = int(text[1]) + hours * 60
                seconds = int(text[2]) + minutes * 60
            else:
                status.set(manager, 'сохранять оценки на несколько дней это слишком много. '
                                    'Я должен показывать все изменения.')
                await manager.switch_to(States.MAIN)
                return
        elif len(text) % 2 == 0:
            seconds = 0
            for text1, text2 in zip(text[::2], text[1::2]):
                if text2 in ('секунда', 'секунд'):
                    seconds += int(text1)
                elif text2 in ('минута', 'минут'):
                    seconds += int(text1) * 60
                elif text2 in ('час', 'часов'):
                    seconds += int(text1) * 3600
                else:
                    status.set(manager, 'я не могу сохранять оценки на такое время.')
                    await manager.switch_to(States.MAIN)
                    return
        else:
            status.set(manager, 'я не могу сохранять оценки на такое время.')
            await manager.switch_to(States.MAIN)
            return
    except ValueError:
        status.set(manager, 'какое-то странное время ты написал. Я не могу понять. '
                            'Где-то вместо числа написано что-то, не похожее на число.')
        await manager.switch_to(States.MAIN)
        return
    repo: Repo = manager.middleware_data['repo']
    await repo.set_cache_time(message.from_user.id, seconds)


dialog = Dialog(
    Window(
        status.create_status_widget(),
        Button(Const('регистрация'), 'register', on_register, when=~F['registered']),
        Row(
            Button(Const('изменить данные'), 'edit_data', on_edit_data),
            Button(Const('удалить данные', ), 'delete_data', on_click=on_delete_data),
            when='registered'
        ),
        Row(
            Button(Const('версия'), 'version', on_click=on_version),
            Button(Const('политика конфиденциальности'), 'privacy_policy', on_privacy_policy),
        ),
        Row(
            Button(Const('часть года'), 'change_quarter', on_click=on_change_quarter),
            SwitchTo(Const('время кеширования'), 'change_cache_time', States.EDIT_CACHE_TIME)
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
    Window(
        Const('Чтобы не мучать постоянными запросами сервер elschool, я на некоторое время сохраняю оценки. '
              'Сейчас ты можешь написать мне время, которое я не буду обновлять твои оценки '
              'после предыдущего получения. Стандартное время 1 час. '
              'Можно писать по разному. Например 20 минут 10 секунд или 20:10 или 21 минута или 1200 секунд.'),
        TextInput('cache_time', on_success=on_input_cache_time),
        SwitchTo(Const('отмена'), 'cancel_cache_time', States.MAIN),
        state=States.EDIT_CACHE_TIME
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
