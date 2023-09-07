import random
import time
import typing
from random import randint

import aiohttp
import aiosqlite
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bs4 import BeautifulSoup


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
        elschool = RandomRepo()
        return await elschool.register(login, password)

    async def register_user(self, user_id, jwtoken, url, quarter, login=None, password=None):
        await self.db.execute('INSERT INTO users (id, jwtoken, url, quarter, login, password) VALUES (?, ?, ?, ?, ?, ?)',
                              (user_id, jwtoken, url, quarter, login, password))
        await self.db.commit()

    async def update_data(self, user_id, jwtoken, login=None, password=None):
        await self.db.execute('UPDATE users SET jwtoken=?, login=?, password=?, last_cache=0 WHERE id=?',
                              (jwtoken, login, password, user_id))
        await self.db.commit()

    async def get_user_data_jwtoken(self, user_id):
        cursor = await self.db.execute('SELECT login, password, jwtoken FROM users WHERE id=?',
                                       (user_id,))
        return await cursor.fetchone()

    async def get_grades(self, user_id):
        async with self.db.cursor() as cursor:
            cursor = typing.cast(aiosqlite.Cursor, cursor)
            await cursor.execute('SELECT last_cache, cache_time, quarter, jwtoken, url FROM users WHERE id=?',
                                 (user_id,))
            last_cache, cache_time, quarter, jwtoken, url = await cursor.fetchone()
            if time.time() - last_cache > cache_time:
                return await self._update_cache(cursor, user_id, quarter, jwtoken, url)

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

    async def _update_cache(self, cursor: aiosqlite.Cursor, user_id, quarter, jwtoken, url):
        elschool = RandomRepo()
        if url:
            grades = await elschool.get_grades(jwtoken, quarter, url)
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
        elschool = RandomRepo()
        return await elschool.get_grades_and_url(jwtoken)

    async def delete_data(self, user_id):
        await self.db.execute('DELETE FROM users WHERE id=?', (user_id,))
        await self.db.commit()

    async def get_quarters(self, user_id):
        elschool = RandomRepo()
        cursor = await self.db.execute('SELECT jwtoken, url FROM users WHERE id=?', (user_id,))
        jwtoken, url = await cursor.fetchone()
        grades = await elschool.get_grades(jwtoken, url)
        return list(grades.keys())

    async def update_quarter(self, user_id, quarter):
        await self.db.execute('UPDATE users SET quarter=? WHERE id=?', (quarter, user_id))
        await self.clear_cache(user_id)


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
    if not response.ok:
        raise RegisterError(f'{error_message}, проблемы с сервером, код ошибки http {response.status}')

    if not url:
        return

    if str(response.url).startswith(url):
        return

    raise RegisterError(f'{error_message}, так как сервер отправил не на ту страницу '
                        f'({response.url} вместо {url}). '
                        f'Обычно такое происходит если не правильно указан логин или пароль.',
                        login, password)


class ElschoolRepo:
    async def register(self, login, password):
        async with aiohttp.ClientSession() as session:
            response = await session.post('https://elschool.ru/Logon/Index',
                                          params={'login': login, 'password': password}, ssl=False)
            _check_response(response, 'https://elschool.ru/users/privateoffice',
                            'не удалось выполнить регистрацию', login, password)
            jwtoken = session.cookie_jar.filter_cookies('https://elschool.ru').get('JWToken').value
            return jwtoken

    async def get_grades(self, jwtoken, url, quarter):
        async with aiohttp.ClientSession(cookies={'JWToken': jwtoken}) as session:
            return await self._get_grades(quarter, session, url)

    async def _get_grades(self, quarter, session, url):
        response = await session.get(url, ssl=False)
        _check_response(response, url, 'не удалось получить оценки с сервера')
        text = await response.text()

        try:
            bs = BeautifulSoup(text, 'html.parser')
            table = bs.find('table', class_='GradesTable')
            quarters = [th.text.strip() for th in table.find('thead').find_all('th') if not th.attrs]
            grades = {}

            for i in range(len(quarters)):
                quarter_grades = {}
                for tr in table.find('tbody').find_all('tr'):
                    lesson_name = tr.find('td', class_='grades-lesson').text.strip()
                    lesson_marks = []
                    marks = tr.find_all('td', class_='grades-marks')[i]

                    for mark in marks.find_all('span', class_='mark-span'):
                        lesson_date, date = mark['data-popover-content'].split('<p>')
                        lesson_date.split(':')[1].strip()
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
        return 'https://elschool.ru/users/diaries/' + bs.find('a', text='Табель')['href']


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
        url = f'https:/random.org'
        return await self.get_grades(jwtoken, url, quarter), url


class RegisterError(Exception):
    def __init__(self, message, login=None, password=None):
        super().__init__(message)
        self.login = login
        self.password = password


class DataProcessError(Exception):
    pass
