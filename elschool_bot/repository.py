import logging
import random
import time
import typing
from random import randint

import aiohttp
import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Repo:
    def __init__(self, connection: aiosqlite.Connection):
        self.db = connection

    async def has_user(self, user_id):
        cursor = await self.db.execute('SELECT EXISTS(SELECT id FROM users WHERE id=?)', (user_id,))
        return (await cursor.fetchone())[0]

    async def get_user_data(self, user_id):
        cursor = await self.db.execute('SELECT login, password FROM users WHERE id=?',
                                       (user_id,))
        return await cursor.fetchone()

    async def check_register_user(self, login, password):
        elschool = ElschoolRepo()
        return await elschool.register(login, password)

    async def register_user(self, user_id, jwtoken, url, quarter, login=None, password=None):
        await self.db.execute(
            'INSERT INTO users (id, jwtoken, url, quarter, login, password) VALUES (?, ?, ?, ?, ?, ?)',
            (user_id, jwtoken, url, quarter, login, password))
        await self.db.commit()
        logger.info(f'пользователь с id {user_id} зарегистрировался')

    async def update_data(self, user_id, jwtoken, login=None, password=None):
        await self.db.execute('UPDATE users SET jwtoken=?, login=?, password=?, last_cache=0 WHERE id=?',
                              (jwtoken, login, password, user_id))
        await self.db.commit()
        logger.info(f'пользователь с id {user_id} обновил свои данные')

    async def get_user_data_jwtoken(self, user_id):
        cursor = await self.db.execute('SELECT login, password, jwtoken FROM users WHERE id=?',
                                       (user_id,))
        return await cursor.fetchone()

    async def get_grades(self, user_id):
        logger.debug(f'пользователь с id {user_id} получает оценки')
        async with self.db.cursor() as cursor:
            cursor = typing.cast(aiosqlite.Cursor, cursor)
            await cursor.execute('SELECT last_cache, cache_time, quarter, jwtoken, url FROM users WHERE id=?',
                                 (user_id,))
            last_cache, cache_time, quarter, jwtoken, url = await cursor.fetchone()
            if time.time() - last_cache > cache_time:
                logger.debug('время кеширования прошло, нужно получить новые оценки')
                return await self._update_cache(cursor, user_id, quarter, jwtoken, url)

            logger.debug('время кеширования ещё не прошло, отправляются сохранённые оценки')
            await cursor.execute('SELECT lesson_name, lesson_date, date, mark FROM grades WHERE user_id=?',
                                 (user_id,))
            grades = {}
            async for lesson_name, lesson_date, date, mark in cursor:
                if lesson_name not in grades:
                    grades[lesson_name] = []
                grades[lesson_name].append({
                    'lesson_date': lesson_date,
                    'date': date,
                    'mark': mark
                })
            return grades

    async def update_cache(self, user_id):
        async with self.db.cursor() as cursor:
            await cursor.execute('SELECT quarter, jwtoken, url FROM users WHERE id=?', (user_id,))
            quarter, jwtoken, url = await cursor.fetchone()
            return self._update_cache(cursor, user_id, quarter, jwtoken, url)

    async def set_cache_time(self, user_id, cache_time):
        await self.db.execute('UPDATE users SET cache_time=? WHERE id=?', (cache_time, user_id))
        await self.db.commit()

    async def _update_cache(self, cursor: aiosqlite.Cursor, user_id, quarter, jwtoken, url):
        elschool = ElschoolRepo()
        if url:
            grades = await elschool.get_grades(jwtoken, url, quarter)
            await cursor.execute('UPDATE users SET last_cache=? WHERE id=?', (time.time(), user_id))
        else:
            grades, url = await elschool.get_grades_and_url(jwtoken, quarter)
            await cursor.execute('UPDATE users SET last_cache=?, url=? WHERE id=?',
                                 (time.time(), url, user_id))
        data = []
        for name, marks in grades.items():
            if not marks:
                data.append((user_id, name, '00.00.0000', '00.00.0000', 0))
            for mark in marks:
                data.append((user_id, name, mark['lesson_date'], mark['date'], mark['mark']))

        await cursor.execute('DELETE FROM grades WHERE user_id=?', (user_id,))
        await cursor.executemany('INSERT INTO grades VALUES (?, ?, ?, ?, ?)', data)
        await self.db.commit()
        return grades

    async def clear_cache(self, user_id):
        await self.db.execute('UPDATE users SET last_cache=0 WHERE id=?', (user_id,))
        await self.db.commit()

    async def check_get_grades(self, jwtoken):
        elschool = ElschoolRepo()
        return await elschool.get_grades_and_url(jwtoken)

    async def delete_data(self, user_id):
        await self.db.execute('DELETE FROM users WHERE id=?', (user_id,))
        await self.db.commit()

    async def get_quarters(self, user_id):
        elschool = ElschoolRepo()
        cursor = await self.db.execute('SELECT jwtoken, url FROM users WHERE id=?', (user_id,))
        jwtoken, url = await cursor.fetchone()
        grades = await elschool.get_grades(jwtoken, url, None)
        return list(grades.keys())

    async def update_quarter(self, user_id, quarter):
        await self.db.execute('UPDATE users SET quarter=? WHERE id=?', (quarter, user_id))
        await self.clear_cache(user_id)

    async def save_schedule(self, user_id, name, next_time, interval,
                            show_mode, lessons, dates, marks, show_without_marks):
        async with self.db.cursor() as cursor:
            await cursor.execute('SELECT id FROM schedules WHERE user_id=?', (user_id,))
            ids = {id[0] async for id in cursor}
            max_id = max(ids) if ids else 0
            id = 1
            for id in range(1, max_id+2):
                if id not in ids:
                    break
            if not name or name == 'None':
                name = f'отправка {id}'
            logger.info(f'пользователь с id {user_id} сохранил отправку с id {id} и названием {name}, '
                        f'которая покажет оценки в {next_time} с повторениями {interval}')
            await cursor.execute('INSERT INTO schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                 (user_id, id, name, next_time, interval,
                                  show_mode, lessons, dates, marks, show_without_marks))
        await self.db.commit()
        return id

    async def update_schedule(self, user_id, id, name, next_time, interval, show_mode,
                              lessons, dates, marks, show_without_marks):
        logger.info(f'пользователь с id {user_id} изменил отправку с названием {name}, '
                    f'которая покажет оценки в {next_time} с повторениями {interval}')
        await self.db.execute('UPDATE schedules SET name=?, next_time=?, interval=?, show_mode=?, '
                              'lessons=?, dates=?, marks=?, show_without_marks=? WHERE user_id=? AND id=?',
                              (name, next_time, interval, show_mode,
                               lessons, dates, marks, show_without_marks, user_id, id))
        await self.db.commit()

    async def schedule_names(self, user_id):
        cursor = await self.db.execute('SELECT id, name FROM schedules WHERE user_id=?', (user_id,))
        return await cursor.fetchall()

    async def remove_schedule(self, user_id, id):
        logger.info(f'пользователь с id {user_id} удалил отправку с id {id}')
        await self.db.execute('DELETE FROM schedules WHERE user_id=? AND id=?', (user_id, id))
        await self.db.commit()

    async def get_schedule(self, user_id, id):
        cursor = await self.db.execute('SELECT * FROM schedules WHERE user_id=? AND id=?', (user_id, id))
        return await cursor.fetchone()

    async def get_schedules_for_restore(self):
        cursor = await self.db.execute('SELECT user_id, id, next_time FROM schedules')
        schedules = {}
        async for user_id, id, next_time in cursor:
            if user_id not in schedules:
                schedules[user_id] = []
            schedules[user_id].append({'id': id, 'next_time': next_time})
        return schedules

    async def get_results(self, user_id):
        cursor = await self.db.execute('SELECT jwtoken, url FROM users WHERE id=?', (user_id,))
        jwtoken, url = await cursor.fetchone()
        elschool = ElschoolRepo()
        if url:
            return await elschool.get_results(jwtoken, url)
        else:
            results, url = await elschool.get_results_and_url(jwtoken)
            await self.db.execute('UPDATE users SET url=?', (url,))
            return results


class RepoMiddleware(BaseMiddleware):
    def __init__(self, dbfile):
        self.dbfile = dbfile

    async def __call__(
            self,
            handler: typing.Callable[[TelegramObject, typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]],
            event: TelegramObject,
            data: typing.Dict[str, typing.Any],
    ) -> typing.Any:
        async with aiosqlite.connect(self.dbfile) as connection:
            data['repo'] = Repo(connection)
            return await handler(event, data)


def _check_response(response, url, error_message, login=None, password=None):
    logger.debug(f'проверка ответа от сервера: {response}')
    if not response.ok:
        raise RegisterError(f'{error_message}, проблемы с сервером, код ошибки http {response.status}')

    if str(response.url).startswith(url):
        logger.debug('ответ нормальный')
        return

    raise RegisterError(f'{error_message}, так как сервер отправил не на ту страницу '
                        f'({response.url} вместо {url}). '
                        f'Обычно такое происходит если не правильно указан логин или пароль.',
                        login, password)


class ElschoolRepo:
    async def register(self, login, password):
        logger.debug(f'пользователь с логином {login} получает токен регистрации')
        async with aiohttp.ClientSession() as session:
            response = await session.post('https://elschool.ru/Logon/Index',
                                          params={'login': login, 'password': password}, ssl=False)
            _check_response(response, 'https://elschool.ru/users/privateoffice',
                            'не удалось выполнить регистрацию', login, password)
            jwtoken = session.cookie_jar.filter_cookies('https://elschool.ru').get('JWToken').value
            logger.debug(f'токен получен {jwtoken}')
            return jwtoken

    async def get_grades(self, jwtoken, url, quarter):
        async with aiohttp.ClientSession(cookies={'JWToken': jwtoken}) as session:
            return await self._get_grades(quarter, session, url)

    async def _get_grades(self, quarter, session, url):
        logger.info(f'получаем оценки с {url}')
        response = await session.get(url, ssl=False)
        _check_response(response, url, 'не удалось получить оценки с сервера')
        text = await response.text()

        try:
            bs = BeautifulSoup(text, 'html.parser')
            table = bs.find('table', class_='GradesTable')
            if not table:
                raise DataProcessError('на странице не найдена таблица с оценками')
            thead = table.find('thead')
            if not thead:
                raise DataProcessError('на странице не найден блок для заголовков')
            ths = thead.find_all('th')
            if not ths:
                raise DataProcessError('на странице не найдены заголовки с названиями частей года')
            quarters = [th.text.strip() for th in ths if not th.attrs]
            grades = {}

            for i in range(len(quarters)):
                quarter_grades = {}
                tbody = table.find('tbody')
                if not tbody:
                    raise DataProcessError('на странице не найдено тело таблицы')
                trs = tbody.find_all('tr')
                if not trs:
                    raise DataProcessError('в таблице нет строк с уроками')
                for tr in trs:
                    td = tr.find('td', class_='grades-lesson')
                    if not td:
                        raise DataProcessError('в строке таблицы нет названия урока')
                    lesson_name = td.text.strip()
                    lesson_marks = []
                    tds = tr.find_all('td', class_='grades-marks')
                    if not tds:
                        raise DataProcessError('в строке таблицы нет частей года')
                    if i >= len(tds):
                        raise DataProcessError('выбранной части года нет в строке таблицы')
                    marks = tds[i]

                    for mark in marks.find_all('span', class_='mark-span'):
                        lesson_date, date = mark['data-popover-content'].split('<p>')
                        lesson_marks.append({
                            'lesson_date': lesson_date.split(':')[1].strip(),
                            'date': date.split(':')[1].strip(),
                            'mark': int(mark.text)
                        })

                    quarter_grades[lesson_name] = lesson_marks
                grades[quarters[i]] = quarter_grades

            if quarter:
                return grades[quarter]
        except Exception as e:
            raise DataProcessError(f'при обработке данных возникла ошибка: {e}') from e
        return grades

    async def _get_results_grades(self, session, url: str):
        url = url.replace('grades', 'results')
        logger.info(f'получаем итоговые оценки с {url}')
        response = await session.get(url, ssl=False)
        _check_response(response, url, 'не удалось получить оценки с сервера')
        text = await response.text()

        try:
            bs = BeautifulSoup(text, 'html.parser')
            table = bs.find('table', class_='ResultsTable')
            if not table:
                raise DataProcessError('на странице не найдена таблица с оценками')
            thead = table.find('thead')
            if not thead:
                raise DataProcessError('на странице не найден блок для заголовков')
            ths = thead.find_all('th')
            if not ths:
                raise DataProcessError('на странице не найдены заголовки с названиями частей года')
            quarters = [th.text.strip() for th in ths if not th.attrs][1:]
            results = {}
            tbody = table.find('tbody')
            if not tbody:
                raise DataProcessError('на странице не найдено тело таблицы')
            trs = tbody.find_all('tr')
            if not trs:
                raise DataProcessError('в таблице нет строк с уроками')
            for tr in trs:
                lesson = tr.find('td').text.strip()
                lesson_results = {}
                for quarter, td in zip(quarters, tr.find_all('td', class_='results-mark')):
                    text = td.text.strip()
                    if not text:
                        lesson_results[quarter] = None
                    else:
                        lesson_results[quarter] = int(text)
                results[lesson] = lesson_results
            return results
        except Exception as e:
            raise DataProcessError(f'при обработке данных возникла ошибка: {e}') from e

    async def get_results_and_url(self, jwtoken):
        async with aiohttp.ClientSession(cookies={'JWToken': jwtoken}) as session:
            url = await self._get_url(session)
            grades = await self._get_results_grades(session, url)
        return grades, url

    async def get_results(self, jwtoken, url):
        async with aiohttp.ClientSession(cookies={'JWToken': jwtoken}) as session:
            grades = await self._get_results_grades(session, url)
        return grades

    async def get_grades_and_url(self, jwtoken, quarter=None):
        async with aiohttp.ClientSession(cookies={'JWToken': jwtoken}) as session:
            url = await self._get_url(session)
            grades = await self._get_grades(quarter, session, url)
        return grades, url

    async def _get_url(self, session):
        response = await session.get(f'https://elschool.ru/users/diaries', ssl=False)
        _check_response(response, 'https://elschool.ru/users/diaries',
                        'при получении ссылки на страницу с оценками произошла ошибка')
        html = await response.text()
        bs = BeautifulSoup(html, 'html.parser')
        a = bs.find('a', text='Табель')
        if not a:
            raise DataProcessError('на странице дневника не найдена ссылка на страницу с оценками')
        return 'https://elschool.ru/users/diaries/' + a['href']


class RandomRepo:
    async def register(self, login, password):
        return f'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM{login}{password}'

    async def get_grades(self, jwtoken, url, quarter=None):
        quarters = (
            ('1 четверть', '2 четверть', '3 четверть', '4 четверть'),
            ('1 полугодие', '2 полугодие')
        )
        lessons = [
            'Астрономия',
            'Индивидуальный проект',
            'Иностранный язык',
            'Информатика',
            'Информационная безопасность',
            'История',
            'Литература',
            'Математика',
            'Мировая художественная культура',
            'Обществознание',
            'Основы безопасности жизнедеятельности',
            'Разговоры о важном',
            'Решение задач и упражнений повышенной сложности',
            'Решение задач различных типов и цепочек химических превращений',
            'Родной язык',
            'Русский язык',
            'Физика',
            'Физическая культура',
            'Финансовая грамотность',
            'Химия',
            'Я в современном мире',
            'Немецкий язык',
            'Технология',
            'ИЗО',
            'Биология'
        ]

        grades = {}
        for q in quarters[randint(0, 1)]:
            quarter_grades = {}
            random.shuffle(lessons)
            quarter_lessons = lessons[:15]
            for lesson in quarter_lessons:
                quarter_grades[lesson] = [{
                    'date': f'{randint(1, 28)}.{randint(1, 12)}.{randint(1900, 10000)}',
                    'lesson_date': f'{randint(1, 28)}.{randint(1, 12)}.{randint(1900, 10000)}',
                    'mark': randint(2, 5)
                } for i in range(randint(0, 20))]
            grades[q] = quarter_grades

        if quarter:
            qgrades = grades.get(quarter)
            if qgrades is None:
                quarters = list(grades.keys())
                qgrades = grades[quarters[randint(0, len(quarters) - 1)]]
            return qgrades

        return grades

    async def get_grades_and_url(self, jwtoken, quarter=None):
        url = f'https://random.org'
        return await self.get_grades(jwtoken, url, quarter), url


class RegisterError(Exception):
    def __init__(self, message, login=None, password=None):
        super().__init__(message)
        self.login = login
        self.password = password


class DataProcessError(Exception):
    pass
