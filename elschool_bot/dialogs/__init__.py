from aiogram import Dispatcher, Router, F
from aiogram.filters.command import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram_dialog import DialogManager, StartMode, setup_dialogs

from elschool_bot.repository import RepoMiddleware, Repo
from . import settings, grades

router = Router()
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='оценки'), KeyboardButton(text='настройки')]
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
    await dialog_manager.start(grades.GradesStates.STATUS, mode=StartMode.RESET_STACK)


@router.message(Command('showmenu'))
@router.message(F.text == 'меню')
async def show_menu(message: Message):
    await message.answer('основное меню', reply_markup=main_menu)


def register_handlers(dp: Dispatcher, config):
    dp.include_router(router)
    middleware = RepoMiddleware(config.dbfile)
    dp.message.middleware(middleware)
    dp.callback_query.middleware(middleware)
    settings.register_handlers(dp)
    grades.register_handlers(dp)
    setup_dialogs(dp)
