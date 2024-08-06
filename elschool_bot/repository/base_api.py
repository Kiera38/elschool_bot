import datetime
from typing import Protocol


class RegisterError(Exception):
    def __init__(self, message, login=None, password=None):
        super().__init__(message)
        self.login = login
        self.password = password


class DataProcessError(Exception):
    pass


class Api(Protocol):
    async def register(self, login: str, password: str) -> str: ...

    async def get_grades(
        self, jwtoken: str, url: str
    ) -> dict[str, dict[str, list[dict[str, str | int]]]]: ...

    async def get_results(
        self, jwtoken: str, url: str
    ) -> dict[str, dict[str, int]]: ...

    async def get_results_and_url(
        self, jwtoken: str
    ) -> tuple[dict[str, dict[str, int]], str]: ...

    async def get_grades_and_url(
        self, jwtoken: str
    ) -> tuple[dict[str, dict[str, list[dict[str, str | int]]]], str]: ...

    async def get_diaries(
        self, jwtoken: str, url: str, date: datetime.date
    ) -> dict[str, dict[int, dict[str, str | int]]]: ...

    async def get_diaries_and_url(
        self, jwtoken: str, date: datetime.date
    ) -> tuple[dict[str, dict[int, dict[str, str | int]]], str]: ...
