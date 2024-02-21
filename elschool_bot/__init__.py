from dataclasses import dataclass


@dataclass
class BotConfig:
    token: str
    parse_mode: str


@dataclass
class LoggingConfig:
    level: int
    format: str


@dataclass
class Config:
    bot: BotConfig
    logging: LoggingConfig
    dbfile: str
    storage_file: str | None = None


def main():
    import elschool_bot.__main__
    import asyncio
    asyncio.run(elschool_bot.__main__.main())
