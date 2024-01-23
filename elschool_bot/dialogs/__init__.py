import logging

from aiogram import Dispatcher, Router, F, Bot
from aiogram.filters import ExceptionTypeFilter
from aiogram.filters.command import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ErrorEvent, BotCommand, CallbackQuery
from aiogram_dialog import DialogManager, StartMode, setup_dialogs
from aiogram_dialog.api.entities import DIALOG_EVENT_NAME

from elschool_bot.repository import RepoMiddleware, Repo, DataProcessError, RegisterError
from . import settings, grades, input_data, notifications, date_selector, results_grades, schedule
from .grades import start_select_grades
from .notifications.scheduler import Scheduler, SchedulerMiddleware

router = Router()
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='расписание'), KeyboardButton(text='расписание звонков')],
    [KeyboardButton(text='оценки'), KeyboardButton(text='итоговые оценки')],
    [KeyboardButton(text='отправка по времени'), KeyboardButton(text='настройки')]
], resize_keyboard=True)
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_command(message: Message):
    logger.info(f'пользователь с id {message.from_user.id} использовал команду /start')
    await message.answer('Привет, я Elschool Bot. Буду помогать тебе с учёбой. '
                         'Для начала рекомендую зарегистрироваться или почитать помощь, '
                         'чтобы разобраться с моими возможностями.',
                         reply_markup=main_menu)


@router.message(Command('settings'))
@router.message(F.text == 'настройки')
async def show_settings(message: Message, dialog_manager: DialogManager):
    logger.debug(f'пользователь с id {message.from_user.id} решил посмотреть настройки')
    await dialog_manager.start(settings.States.MAIN, mode=StartMode.RESET_STACK)


@router.message(F.text == 'оценки')
async def show_grades(message: Message, dialog_manager: DialogManager, repo: Repo):
    if not await repo.has_user(message.from_user.id):
        logger.debug(f'незарегистрированный пользователь с id {message.from_user.id} решил получить оценки')
        await message.answer('ты не зарегистрирован, попробуй сначала зарегистрироваться. '
                             'Это можно сделать на вкладке настройки.')
        return
    logger.debug(f'пользователь с id {message.from_user.id} решил получить оценки')
    await start_select_grades(dialog_manager)


@router.message(Command('showmenu'))
@router.message(F.text == 'меню')
async def show_menu(message: Message):
    logger.debug(f'у пользователя с id {message.from_user.id} пропало основное меню')
    await message.answer('основное меню', reply_markup=main_menu)


@router.message(Command('schedules'))
@router.message(F.text == 'отправка по времени')
async def schedules(message: Message, dialog_manager, repo):
    if not await repo.has_user(message.from_user.id):
        logger.debug(f'незарегистрированный пользователь с id {message.from_user.id} '
                     f'решил по управлять своими отправками по времени')
        await message.answer('ты не зарегистрирован, попробуй сначала зарегистрироваться. '
                             'Это можно сделать на вкладке настройки.')
        return
    logger.debug(f'пользователь с id {message.from_user.id} решил по управлять своими отправками по времени')
    await notifications.show(dialog_manager)


@router.message(Command('resultsgrades'))
@router.message(F.text == 'итоговые оценки')
async def results(message: Message, dialog_manager, repo):
    if not await repo.has_user(message.from_user.id):
        logger.debug(f'незарегистрированный пользователь с id {message.from_user.id} '
                     f'решил посмотреть свои итоговые оценки.')
        await message.answer('ты не зарегистрирован, попробуй сначала зарегистрироваться. '
                             'Это можно сделать на вкладке настройки.')
        return
    logger.debug(f'пользователь с id {message.from_user.id} решил посмотреть свои итоговые оценки')
    await results_grades.start(dialog_manager)


@router.message(Command('schedule'))
@router.message(F.text == 'расписание')
async def show_schedule(message, dialog_manager):
    await schedule.start(dialog_manager)


@router.message(Command('timeschedule'))
@router.message(F.text == 'расписание звонков')
async def show_time_schedule(message, dialog_manager):
    await schedule.start_time_schedule(dialog_manager)


@router.message(Command('restoreschedules'))
async def restore_schedules(message: Message, dialog_manager: DialogManager, notifications):
    logger.info(f'разработчик с id {message.from_user.id} решил восстановить отправки по времени')
    await notifications.restore_grades_task(dialog_manager)
    await message.answer('все отправки восстановлены')


@router.error(ExceptionTypeFilter(DataProcessError))
async def on_data_process_error(error: ErrorEvent, bot: Bot):
    chat_id, user_id = get_ids(error)

    await bot.send_message(chat_id, f'при обработке данных, полученных с сервера произошла ошибка {error.exception}')
    logger.error(f'у пользователя c id {user_id} произошла ошибка обработки данных', exc_info=error.exception)


def get_ids(error):
    event = error.update.event
    if isinstance(event, CallbackQuery):
        event = event.message
    chat_id = event.chat.id
    user_id = event.from_user.id
    return chat_id, user_id


@router.error(ExceptionTypeFilter(RegisterError))
async def on_register_error(error: ErrorEvent, bot: Bot):
    chat_id, user_id = get_ids(error)
    exception: RegisterError = error.exception

    await bot.send_message(chat_id, f'при регистрации произошла ошибка {exception}')
    if exception.login is not None and exception.password is not None:
        await bot.send_message(chat_id, f'твой логин {exception.login} и пароль {exception.password}')
    logger.error(f'у пользователя c id {user_id} произошла ошибка регистрации', exc_info=exception)


@router.error()
async def on_other_error(error: ErrorEvent, bot: Bot):
    chat_id, user_id = get_ids(error)
    exception = error.exception

    error_text = f'{type(exception).__name__}: {exception}'
    await bot.send_message(chat_id, f'пока я что-то делал, произошла какая-то странная ошибка: {error_text}')
    logger.error(f'у пользователя c id {user_id} возникла необработанная ошибка', exc_info=exception)


def register_handlers(dp: Dispatcher, config):
    setup_dialogs(dp)
    dp.include_router(router)

    middleware = RepoMiddleware(config.dbfile)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)
    dp.observers[DIALOG_EVENT_NAME].middleware(middleware)

    scheduler_ = Scheduler()
    scheduler_middleware = SchedulerMiddleware(scheduler_)
    dp.message.middleware(scheduler_middleware)
    dp.callback_query.middleware(scheduler_middleware)

    settings.register_handlers(dp)
    grades.register_handlers(dp)
    notifications.register_handlers(dp)
    schedule.register_handlers(dp)

    dp.include_router(input_data.dialog)
    dp.include_router(date_selector.dialog)
    dp.include_router(results_grades.dialog)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command='/start', description='запустить бота'),
        BotCommand(command='/showmenu', description='показать меню'),
        BotCommand(command='/settings', description='показать настройки'),
        BotCommand(command='/grades', description='показать оценки'),
        BotCommand(command='/schedules', description='показать отправки'),
        BotCommand(command='/resultsgrades', description='показать итоговые оценки'),
        BotCommand(command='/schedule', description='показать расписание')
    ]
    await bot.set_my_commands(commands)
