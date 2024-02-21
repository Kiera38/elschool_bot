import asyncio
import logging
import os
import pickle

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

from elschool_bot import Config, BotConfig, LoggingConfig
from elschool_bot.dialogs import register_handlers, set_commands


class PickleStorage(MemoryStorage):
    def __init__(self, file):
        super().__init__()

        if os.path.exists(file):
            with open(file, 'rb') as f:
                self.storage = pickle.load(f)

        self.file = file

    async def close(self) -> None:
        with open(self.file, 'wb') as f:
            pickle.dump(f, self.storage)


def load_config():
    # TODO: загружать конфиг из файла
    return Config(
        bot=BotConfig(token=os.environ['BOT_TOKEN'], parse_mode='html'),
        logging=LoggingConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        dbfile='bot.db', storage_file='storage.pkl'
    )


async def main():
    config = load_config()
    logging.basicConfig(level=config.logging.level, format=config.logging.format)
    bot = Bot(config.bot.token, parse_mode=config.bot.parse_mode)
    storage = PickleStorage(config.storage_file) if config.storage_file is not None else MemoryStorage()
    dispatcher = Dispatcher(storage=storage, events_isolation=SimpleEventIsolation())
    register_handlers(dispatcher, config)
    await set_commands(bot)
    await dispatcher.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
