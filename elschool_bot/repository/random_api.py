import random


async def register(login, password):
    return f"qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM{login}{password}"


async def get_grades(jwtoken, url, quarter=None):
    quarters = (
        ("1 четверть", "2 четверть", "3 четверть", "4 четверть"),
        ("1 полугодие", "2 полугодие"),
    )
    lessons = [
        "Астрономия",
        "Индивидуальный проект",
        "Иностранный язык",
        "Информатика",
        "Информационная безопасность",
        "История",
        "Литература",
        "Математика",
        "Мировая художественная культура",
        "Обществознание",
        "Основы безопасности жизнедеятельности",
        "Разговоры о важном",
        "Решение задач и упражнений повышенной сложности",
        "Решение задач различных типов и цепочек химических превращений",
        "Родной язык",
        "Русский язык",
        "Физика",
        "Физическая культура",
        "Финансовая грамотность",
        "Химия",
        "Я в современном мире",
        "Немецкий язык",
        "Технология",
        "ИЗО",
        "Биология",
    ]

    grades = {}
    for q in quarters[random.randint(0, 1)]:
        quarter_grades = {}
        random.shuffle(lessons)
        quarter_lessons = lessons[:15]
        for lesson in quarter_lessons:
            quarter_grades[lesson] = [
                {
                    "date": f"{random.randint(1, 28)}.{random.randint(1, 12)}.{random.randint(1900, 10000)}",
                    "lesson_date": f"{random.randint(1, 28)}.{random.randint(1, 12)}.{random.randint(1900, 10000)}",
                    "mark": random.randint(2, 5),
                }
                for i in range(random.randint(0, 20))
            ]
        grades[q] = quarter_grades

    if quarter:
        qgrades = grades.get(quarter)
        if qgrades is None:
            quarters = list(grades.keys())
            qgrades = grades[quarters[random.randint(0, len(quarters) - 1)]]
        return qgrades

    return grades


async def get_grades_and_url(jwtoken, quarter=None):
    url = "https://random.org"
    return await get_grades(jwtoken, url, quarter), url
