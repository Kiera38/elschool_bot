from aiogram import Dispatcher, Router, F
from aiogram.filters.command import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram_dialog import DialogManager, StartMode, setup_dialogs

from elschool_bot.repository import RepoMiddleware, Repo
from . import settings, grades, input_data, scheduler
from .grades import start_select_grades
from .scheduler.scheduler import Scheduler, SchedulerMiddleware

router = Router()
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='оценки'), KeyboardButton(text='отправка по времени')],
    [KeyboardButton(text='настройки')]
], resize_keyboard=True)


@router.message(CommandStart())
async def start_command(message: Message):
    await message.answer('Привет, я Elschool Bot. Буду помогать тебе с учёбой. '
                         'Для начала рекомендую зарегистрироваться или почитать помощь, '
                         'чтобы разобраться с моими возможностями.',
                         reply_markup=main_menu)


@router.message(F.text == 'настройки')
async def show_settings(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(settings.States.MAIN, mode=StartMode.RESET_STACK)


@router.message(F.text == 'оценки')
async def show_grades(message: Message, dialog_manager: DialogManager, repo: Repo):
    if not await repo.has_user(message.from_user.id):
        await message.answer('ты не зарегистрирован, попробуй сначала зарегистрироваться. '
                             'Это можно сделать на вкладке настройки.')
        return
    await start_select_grades(dialog_manager)


@router.message(Command('showmenu'))
@router.message(F.text == 'меню')
async def show_menu(message: Message):
    await message.answer('основное меню', reply_markup=main_menu)


@router.message(F.text == 'отправка по времени')
async def schedules(message: Message, dialog_manager):
    await scheduler.show(dialog_manager)


@router.message(Command('restoreschedules'))
async def restore_schedules(message: Message, dialog_manager: DialogManager, scheduler):
    await scheduler.restore_grades_task(dialog_manager)
    await message.answer('все отправки восстановлены')


def register_handlers(dp: Dispatcher, config):
    dp.include_router(router)

    middleware = RepoMiddleware(config.dbfile)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)

    scheduler_ = Scheduler()
    scheduler_middleware = SchedulerMiddleware(scheduler_)
    dp.message.middleware(scheduler_middleware)
    dp.callback_query.middleware(scheduler_middleware)

    settings.register_handlers(dp)
    grades.register_handlers(dp)
    scheduler.register_handlers(dp)

    dp.include_router(input_data.dialog)

    setup_dialogs(dp)
