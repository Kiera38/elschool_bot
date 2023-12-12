from dataclasses import dataclass


@dataclass
class Config:
    dbfile: str


def main():
    import elschool_bot.__main__
    import asyncio
    asyncio.run(elschool_bot.__main__.main())
