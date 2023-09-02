import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from elschool_bot import Config
from elschool_bot.dialogs import register_handlers


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(os.environ['BOT_TOKEN'])
    dispatcher = Dispatcher(storage=MemoryStorage())
    register_handlers(dispatcher, Config('bot.db'))
    await dispatcher.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
