import logging

import aiohttp
from bs4 import BeautifulSoup

from elschool_bot.repository.base import DataProcessError, RegisterError

logger = logging.getLogger(__name__)


def _check_response(response, url, error_message, login=None, password=None):
    logger.debug(f"проверка ответа от сервера: {response}")
    if not response.ok:
        raise RegisterError(
            f"{error_message}, проблемы с сервером, код ошибки http {response.status}"
        )

    if str(response.url).startswith(url):
        logger.debug("ответ нормальный")
        return

    raise RegisterError(
        f"{error_message}, так как сервер отправил не на ту страницу "
        f"({response.url} вместо {url}). "
        f"Обычно такое происходит если не правильно указан логин или пароль.",
        login,
        password,
    )


async def register(login, password):
    logger.debug(f"пользователь с логином {login} получает токен регистрации")
    async with aiohttp.ClientSession() as session:
        response = await session.post(
            "https://elschool.ru/Logon/Index",
            params={"login": login, "password": password},
            ssl=False,
        )
        _check_response(
            response,
            "https://elschool.ru/users/privateoffice",
            "не удалось выполнить регистрацию",
            login,
            password,
        )
        jwtoken = (
            session.cookie_jar.filter_cookies("https://elschool.ru")
            .get("JWToken")
            .value
        )
        logger.debug(f"токен получен {jwtoken}")
        return jwtoken


async def get_grades(jwtoken, url, quarter):
    async with aiohttp.ClientSession(cookies={"JWToken": jwtoken}) as session:
        return await _get_grades(quarter, session, url)


async def _get_grades(quarter, session, url):
    logger.info(f"получаем оценки с {url}")
    response = await session.get(url, ssl=False)
    _check_response(response, url, "не удалось получить оценки с сервера")
    text = await response.text()

    try:
        bs = BeautifulSoup(text, "html.parser")
        table = bs.find("table", class_="GradesTable")
        if not table:
            raise DataProcessError("на странице не найдена таблица с оценками")
        thead = table.find("thead")
        if not thead:
            raise DataProcessError("на странице не найден блок для заголовков")
        ths = thead.find_all("th")
        if not ths:
            raise DataProcessError(
                "на странице не найдены заголовки с названиями частей года"
            )
        quarters = [th.text.strip() for th in ths if not th.attrs]
        grades = {}

        for i in range(len(quarters)):
            quarter_grades = {}
            tbody = table.find("tbody")
            if not tbody:
                raise DataProcessError("на странице не найдено тело таблицы")
            trs = tbody.find_all("tr")
            if not trs:
                raise DataProcessError("в таблице нет строк с уроками")
            for tr in trs:
                td = tr.find("td", class_="grades-lesson")
                if not td:
                    raise DataProcessError("в строке таблицы нет названия урока")
                lesson_name = td.text.strip()
                lesson_marks = []
                tds = tr.find_all("td", class_="grades-marks")
                if not tds:
                    raise DataProcessError("в строке таблицы нет частей года")
                if i >= len(tds):
                    raise DataProcessError("выбранной части года нет в строке таблицы")
                marks = tds[i]

                for mark in marks.find_all("span", class_="mark-span"):
                    lesson_date, date = mark["data-popover-content"].split("<p>")
                    lesson_marks.append(
                        {
                            "lesson_date": lesson_date.split(":")[1].strip(),
                            "date": date.split(":")[1].strip(),
                            "mark": int(mark.text),
                        }
                    )

                quarter_grades[lesson_name] = lesson_marks
            grades[quarters[i]] = quarter_grades

        if quarter:
            return grades[quarter]
    except Exception as e:
        raise DataProcessError(f"при обработке данных возникла ошибка: {e}") from e
    return grades


async def _get_results_grades(session, url: str):
    url = url.replace("grades", "results")
    logger.info(f"получаем итоговые оценки с {url}")
    response = await session.get(url, ssl=False)
    _check_response(response, url, "не удалось получить оценки с сервера")
    text = await response.text()

    try:
        bs = BeautifulSoup(text, "html.parser")
        table = bs.find("table", class_="ResultsTable")
        if not table:
            raise DataProcessError("на странице не найдена таблица с оценками")
        thead = table.find("thead")
        if not thead:
            raise DataProcessError("на странице не найден блок для заголовков")
        ths = thead.find_all("th")
        if not ths:
            raise DataProcessError(
                "на странице не найдены заголовки с названиями частей года"
            )
        quarters = [th.text.strip() for th in ths if not th.attrs][1:]
        results = {}
        tbody = table.find("tbody")
        if not tbody:
            raise DataProcessError("на странице не найдено тело таблицы")
        trs = tbody.find_all("tr")
        if not trs:
            raise DataProcessError("в таблице нет строк с уроками")
        for tr in trs:
            lesson = tr.find("td").text.strip()
            lesson_results = {}
            for quarter, td in zip(quarters, tr.find_all("td", class_="results-mark")):
                text = td.text.strip()
                if not text:
                    lesson_results[quarter] = None
                else:
                    lesson_results[quarter] = int(text)
            results[lesson] = lesson_results
        return results
    except Exception as e:
        raise DataProcessError(f"при обработке данных возникла ошибка: {e}") from e


async def get_results_and_url(jwtoken):
    async with aiohttp.ClientSession(cookies={"JWToken": jwtoken}) as session:
        url = await _get_url(session)
        grades = await _get_results_grades(session, url)
    return grades, url


async def get_results(jwtoken, url):
    async with aiohttp.ClientSession(cookies={"JWToken": jwtoken}) as session:
        grades = await _get_results_grades(session, url)
    return grades


async def get_grades_and_url(jwtoken, quarter=None):
    async with aiohttp.ClientSession(cookies={"JWToken": jwtoken}) as session:
        url = await _get_url(session)
        grades = await _get_grades(quarter, session, url)
    return grades, url


async def _get_url(session):
    response = await session.get("https://elschool.ru/users/diaries", ssl=False)
    _check_response(
        response,
        "https://elschool.ru/users/diaries",
        "при получении ссылки на страницу с оценками произошла ошибка",
    )
    html = await response.text()
    bs = BeautifulSoup(html, "html.parser")
    a = bs.find("a", text="Табель")
    if not a:
        raise DataProcessError(
            "на странице дневника не найдена ссылка на страницу с оценками"
        )
    return "https://elschool.ru/users/diaries/" + a["href"]


async def _get_diaries(session: aiohttp.ClientSession, url, date):
    url = (
        url.replace("grades", "details")
        + f"&year={date.year}&week={date.isocalendar()[1]}"
    )
    response = await session.get(url, ssl=False)
    _check_response(response, url, "не удалось получить расписание с сервера")
    text = await response.content.read()
    try:
        bs = BeautifulSoup(text, "html.parser")
        days = {}
        for div in bs.find("div", class_="diaries").find_all("div"):
            table = div.find("table", class_="table")
            if table is None:
                continue
            for tbody in table.find_all("tbody"):
                trs = tbody.find_all("tr", class_="diary__lesson")
                if not trs:
                    continue
                day = trs[0].find("td", class_="diary__dayweek").text.strip()
                if "\xa0" in day:
                    day = day.split("\xa0", 1)[1].strip()
                else:
                    day = day.split(" ", 1)[1]
                day = f"{day}.{date.year}"
                if (
                    len(trs) == 1
                    and trs[0].find("td", class_="diary__nolesson") is not None
                ):
                    days[day] = None
                    continue
                lessons = {}
                for tr in trs:
                    td_discipline = tr.find("td", class_="diary__discipline")
                    number, name = td_discipline.find(
                        "div", class_="flex-grow-1"
                    ).text.split(". ", 1)
                    number = int(number)
                    start_time, end_time = td_discipline.find(
                        "div", class_="diary__discipline__time"
                    ).text.split("-")
                    homework = (
                        tr.find("td", class_="diary__homework")
                        .find("div", class_="diary__homework-text")
                        .text.strip()
                    )
                    lessons[number] = {
                        "number": number,
                        "name": name,
                        "start_time": start_time.strip(),
                        "end_time": end_time.strip(),
                        "homework": homework,
                    }
                days[day] = lessons
        return days
    except Exception as e:
        raise DataProcessError(f"при обработке данных возникла ошибка: {e}") from e


async def get_diaries(jwtoken, url, date):
    async with aiohttp.ClientSession(cookies={"JWToken": jwtoken}) as session:
        diaries = await _get_diaries(session, url, date)
    return diaries


async def get_diaries_and_url(jwtoken, date):
    async with aiohttp.ClientSession(cookies={"JWToken": jwtoken}) as session:
        url = await _get_url(session)
        diaries = await _get_diaries(session, url, date)
    return diaries, url
