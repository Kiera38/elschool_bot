import textwrap

from aiogram.fsm.state import StatesGroup, State
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import SwitchTo
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.media import StaticMedia


class HelpStates(StatesGroup):
    MAIN = State()
    CAPABILITIES = State()
    REGISTRATION = State()
    GRADES = State()
    SCHEDULE = State()
    NOTIFICATIONS = State()
    SETTINGS = State()
    CONTACTS = State()

    VIEW_GRADES = State()
    VIEW_SCHEDULE = State()
    SAVE_EDITS = State()
    VIEW_HOMEWORK = State()
    AUTOSEND = State()

    GRADES_STATISTICS = State()
    GRADES_LIST = State()
    GRADES_FILTERS = State()
    RESULTS_GRADES = State()

    SCHEDULE_CHANGES = State()
    DEFAULT_SCHEDULE_CHANGES = State()
    SCHEDULE_BUTTONS = State()

    AUTOSEND_GRADES = State()
    AUTOSEND_SCHEDULE = State()
    NOTIFY_SCHEDULE_CHANGE = State()
    START_LESSON = State()
    END_LESSON = State()
    START_LESSONS = State()
    END_LESSONS = State()

    REGISTER = State()
    CHANGE_DATA = State()
    REMOVE_DATA = State()
    VERSION = State()
    PRIVACY_POLICY = State()
    CHANGE_QUARTER = State()
    CHANGE_CACHE_TIME = State()


dialog = Dialog(
    Window(
        Const('Зачем ты здесь? С чем тебе помочь?'),
        SwitchTo(Const('возможности бота'), 'capabilities', HelpStates.CAPABILITIES),
        SwitchTo(Const('регистрация'), 'registration', HelpStates.REGISTRATION),
        SwitchTo(Const('оценки'), 'grades', HelpStates.GRADES),
        SwitchTo(Const('расписание'), 'schedule', HelpStates.SCHEDULE),
        SwitchTo(Const('уведомления'), 'notification', HelpStates.NOTIFICATIONS),
        SwitchTo(Const('настройки'), 'settings', HelpStates.SETTINGS),
        SwitchTo(Const('связаться с разработчиком'), 'contacts', HelpStates.CONTACTS),
        state=HelpStates.MAIN
    ),

    Window(
        Const('Этот бот имеет много возможностей.'),
        SwitchTo(Const('просмотр всех оценок'), 'view_grades', HelpStates.VIEW_GRADES),
        SwitchTo(Const('просмотр расписания'), 'view_schedule', HelpStates.VIEW_SCHEDULE),
        SwitchTo(Const('сохранять изменения в расписании'), 'save_edits', HelpStates.SAVE_EDITS),
        SwitchTo(Const('записывать домашку'), 'view_homework', HelpStates.VIEW_HOMEWORK),
        SwitchTo(Const('автоматическая отправка'), 'autosend', HelpStates.AUTOSEND),
        SwitchTo(Const('назад'), 'back', HelpStates.MAIN),
        state=HelpStates.CAPABILITIES
    ),
    Window(
        Const(textwrap.dedent('''
        Ты можешь в любой момент посмотреть свои оценки за определённую часть года. Получение оценок из elschool работает в несколько раз быстрее сайта. 
        Бот может показывать их в различных вариантах.
        1) Общая статистика оценок.
        2) Статистика по каждому из предметов.
        3) Список.
        
        В любом из этих вариантов бот также показывает подсказки по исправлению. Это список оценок, которые нужно получить, чтобы улучшить свою среднюю оценку.
        
        Также можно посмотреть свои итоговые оценки за определённую часть года или за весь год.
        ''')),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        SwitchTo(Const('назад'), 'back', HelpStates.CAPABILITIES),
        state=HelpStates.VIEW_GRADES
    ),
    Window(
        Const(textwrap.dedent('''
        Можно смотреть расписание на любой день. Расписание берётся из elschool и потом добавляются изменения, сохранённые у бота.
        
        Также есть удобная кнопка для просмотра расписания звонков на сегодня. Это также включает подсказку о том, когда закончится урок. Все мы любим смотреть сколько осталось до канца урока.
        ''')),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        SwitchTo(Const('назад'), 'back', HelpStates.CAPABILITIES),
        state=HelpStates.VIEW_SCHEDULE
    ),
    Window(
        Const(textwrap.dedent('''
        Бывает такое, что присылают изменения в расписании, и расписание из elschool уже неправильное. Бот может сохранить эти изменения у себя.
        Изменения сохраняются сразу для всего класса, так что их указывать может только 1 человек.
        
        Изменения в расписании является эксперементальной функцией. Возможны ошибки в работе.
        ''')),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        SwitchTo(Const('назад'), 'back', HelpStates.CAPABILITIES),
        state=HelpStates.SAVE_EDITS
    ),
    Window(
        Const(textwrap.dedent('''
        Забыл домашнее задание? Может вообще не знал? Не беда. Записывай его сюда. Ну а также можешь посмотреть, какую домашку записали другие пользователи из твоего класса.
        Если кто-то спрашивает у тебя что задали - отправляй его ко мне. Сам всё узнает.
        ''')),
        # StaticMedia(path=''),
        SwitchTo(Const('назад'), 'back', HelpStates.CAPABILITIES),
        state=HelpStates.VIEW_HOMEWORK
    ),
    Window(
        Const(textwrap.dedent('''
        Хочется, чтобы бот сам отправлял тебе всякие данные? Такая возможность тоже есть. Отправлять можно как в определённое время, так и привязанное к расписанию звонков.
        Если кто-то из твоего класса сохранил изменения в расписании, то они также могут прийти к тебе.
        Настроить отправку можно на:
        1) определённое время
        2) Прямо перед началом 1 урока (возможно это будет даже 0 у некоторых)
        3) Прямо перед любым уроком
        4) После любого урока
        5) После всех уроков
        
        Отправлять можно оценки или расписание.
        ''')),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        SwitchTo(Const('назад'), 'back', HelpStates.CAPABILITIES),
        state=HelpStates.AUTOSEND
    ),

    Window(
        Const(textwrap.dedent('''
        Для использования большинства функций бота нужна регистрация. 
        Для того, чтобы зарегистрироваться нужно нажать на кнопку "настройки" и выбрать пункт "регистрация".
        Бот попросит сначала ввести логин, а затем пароль от elschool. Их нужно ввести.
        Бот проверит правильность введённых данных, получит всю необходимую информацию. 
        После этого нужно выбрать, какие данные нужно сохранить. Бот сохранит только эти данные. Варианты:
        1) Вообще ничего не сохранять. 
        2) Сохранить только логин/пароль.
        3) Сохранить всё.
        Если какие-то данные не сохранены то бот продолжит работать. Но время от времени, примерно раз в неделю будет спрашивать недостающие данные заново.
        Это связано с тем, что токен регистрации полученный от elschool изменился, и боту нужно получить новый.
        ''')),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        # StaticMedia(path=''),
        SwitchTo(Const('назад'), 'back', HelpStates.MAIN),
        state=HelpStates.REGISTRATION
    ),

    Window(
        Const(textwrap.dedent('''
        Бот может показывать оценки, поставленные учителем в elschool. Для работы этой функции потребуется регистрация.
        Чтобы посмотреть свои оценки, нужно нажать на кнопку "оценки". бот получит информацию об оценкахи предложит выбрать, как показать.
        ''')),
        SwitchTo(Const('статистика'), 'statistics', HelpStates.GRADES_STATISTICS),
        SwitchTo(Const('список'), 'list', HelpStates.GRADES_LIST),
        SwitchTo(Const('фильтрация'), 'filters', HelpStates.GRADES_FILTERS),
        SwitchTo(Const('итоговые оценки'), 'results_grades', HelpStates.RESULTS_GRADES),
        SwitchTo(Const('назад'), 'back', HelpStates.MAIN),
        state=HelpStates.GRADES
    ),
    Window(
        Const(textwrap.dedent('''
        Статистика. 
        в этом варианте бот анализирует оценки и показывает некоторую информацию. Там можно увидеть:
        По какому предмету лучшая и худшая оценка
        Среднюю оценку по всем предметам
        Предметы, у которых средняя оценка больше или меньше средней оценки по всем предметам
        
        Для каждого предмета показывается:
        Средняя оценка, а также лучше или хуже средней оценки по всем предметам
        Какая оценка должна выйти за эту часть года
        Количество оценок
        Список оценок с датами урока и проставления
        Подсказки по исправлению
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.GRADES),
        state=HelpStates.GRADES_STATISTICS
    ),
    Window(
        Const(textwrap.dedent('''
        Список. 
        Показываются все оценки по всем предметам. Также можно включить показ подсказок по исправлению.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.GRADES),
        state=HelpStates.GRADES_LIST
    ),
    Window(
        Const(textwrap.dedent('''
        Также можно фильтровать оценки. Так не будут показываться некоторые оценки, которые не хочется видеть.
        Доступные фильтры:
        Показывать без оценок. 
        Если эта настройка не включена, то предметы без оценок показываться не будут.
        
        выбрать из списка (доступна только в при выборе списка). 
        Показывать только определённые предметы.
        
        Дата урока. 
        Выбрать конкретные даты, когда проходили уроки.
        
        Дата проставления. 
        выбрать конкретные даты, когда учитель поставил эти оценки.
        
        Сами оценки. 
        Можно например показывать только 4 или 4 и 5.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.GRADES),
        state=HelpStates.GRADES_FILTERS
    ),
    Window(
        Const(textwrap.dedent('''
        Итоговые оценки.
        Бот может показать итоговые оценки за часть года и год. Для этого нужно нажать на кнопку "итоговые оценки".
        В этом сообщении также будет количество оценок.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.GRADES),
        state=HelpStates.RESULTS_GRADES
    ),

    Window(
        Const(textwrap.dedent('''
        Бот может показывать расписание на любой день. Для этого нужна регистрация.
        Чтобы посмотреть расписание, нужно нажать на кнопку "расписание".
        Бот предложит выбрать день в календаре. можно выбрать любой день, месяц, год.
        После этого бот получит необходимую информацию и покажет расписание.
        ''')),
        SwitchTo(Const('изменения в расписании'), 'schedule_changes', HelpStates.SCHEDULE_CHANGES),
        SwitchTo(Const('стандартные изменения'), 'default_schedule_changes', HelpStates.DEFAULT_SCHEDULE_CHANGES),
        SwitchTo(Const('Удобные кнопки'), 'schedule_buttons', HelpStates.SCHEDULE_BUTTONS),
        SwitchTo(Const('назад'), 'back', HelpStates.MAIN),
        state=HelpStates.SCHEDULE
    ),
    Window(
        Const(textwrap.dedent('''
        Бывает такое, что присылают изменения в расписании. В таком случае расписание из elschool становится неправильным.
        Бот позволяет указывать изменения. эти изменения сохраняются для всего класса, поэтому их можно сохранять только 1 человеку.
        Для сохранения изменений можно нажать на кнопку изменения в расписании прямо под расписанием на определённый день.
        в отрывшемся окне можно изменять уроки, добавлять новые и удалять которых не будет в этот день.
        Для добавления нового урока нужно нажать на кнопку "новый урок" и ввести номер урока с названием.
        После этого его можно будет также редактировать , как и остальные.
        Для редактирования урока нужно нажать на кнопку с нужным уроком, и выбрать что именно нужно изменить, а затем ввести изменённый вариант.
        Изменять можно название урока, время начала и конца, домашнее задание. Здесь же можно и удалить урок, нажав на кнопку "нет урока".
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SCHEDULE),
        state=HelpStates.SCHEDULE_CHANGES
    ),
    Window(
        Const(textwrap.dedent('''
        Иногда в elschool что-то всегда неправильное. Для таких случаев нужны стандартные изменения. Такие изменения работают для любого дня.
        Чтобы их указать нужно нажать на кнопку "стандартные изменения", которая находится под выбором дня.
        После этого выбираешь любой день недели и изменяешь.
        ВНИМАНИЕ! Сделав неправильные изменения ты подставляешь весь свой класс. Пожалуйста указывайте только правильные изменения. 
        Изменения в расписании является экспериментальной. Возможны ошибки в работе.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SCHEDULE),
        state=HelpStates.DEFAULT_SCHEDULE_CHANGES
    ),
    Window(
        Const(textwrap.dedent('''
        Удобные кнопки:
        Расписание звонков. 
        Позволяет быстро увидеть расписание звонков на сегодня. Также подсказывает когда закончится урок.
        
        Записать домашку. 
        позволяет записать домашку на следующий урок. выбор из тех уроков, которые были сегодня.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SCHEDULE),
        state=HelpStates.SCHEDULE_BUTTONS
    ),

    Window(
        Const(textwrap.dedent('''
        Бот может сам отправлять сообщения с различной информацией. 
        Чтобы это настроить, нужно нажать на кнопку "уведомления".
        ''')),
        SwitchTo(Const('автоматическая отправка оценок'), 'autosend_grades', HelpStates.AUTOSEND_GRADES),
        SwitchTo(Const('отправлять расписание'), 'autosend_schedule', HelpStates.AUTOSEND_SCHEDULE),
        SwitchTo(Const('Отправлять расписание при изменениях'), 'notify_schedule_changes',
                 HelpStates.NOTIFY_SCHEDULE_CHANGE),
        SwitchTo(Const('Отправлять перед уроком'), 'start_lesson', HelpStates.START_LESSON),
        SwitchTo(Const('Отправлять после урока'), 'end_lesson', HelpStates.END_LESSON),
        SwitchTo(Const('Отправлять перед уроками'), 'start_lessons', HelpStates.START_LESSONS),
        SwitchTo(Const('Отправлять после уроков'), 'end_lessons', HelpStates.END_LESSONS),
        SwitchTo(Const('назад'), 'back', HelpStates.MAIN),
        state=HelpStates.NOTIFICATIONS
    ),
    Window(
        Const(textwrap.dedent('''
        Автоматическая отправка оценок. Бот будет сам отправлять оценки в определённое время. Можно настроить неограниченное количество таких отправок.
        Для этого нужно нажать на кнопку "новая отправка" и настроить как и когда показывать оценки. 
        Настройки очень похожи на те, что были при обычном показе оценок. Но есть отличия. Нельзя выбрать дату урока. Дата проставления указывается относительно дня, когда придёт сообщение с оценками.
        
        Есть дополнительные настройки:
        название. 
        позволяет указать название для этой отправки.
        
        показывать.
        Позволяет указать когда стоит показывать сообщение с оценками.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.NOTIFICATIONS),
        state=HelpStates.AUTOSEND_GRADES
    ),
    Window(
        Const(textwrap.dedent('''
        Отправлять расписание. 
        Автоматически отправлять расписание на следующий день в определённое время.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.NOTIFICATIONS),
        state=HelpStates.AUTOSEND_SCHEDULE
    ),
    Window(
        Const(textwrap.dedent('''
        Отправлять расписание при изменениях. 
        Когда кто-то из твоего класса сохранил изменения расписание отправить новое расписание тебе.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.NOTIFICATIONS),
        state=HelpStates.NOTIFY_SCHEDULE_CHANGE
    ),
    Window(
        Const(textwrap.dedent('''
        Отправлять перед уроком. 
        отправить различную информацию об уроке перед его началом.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.NOTIFICATIONS),
        state=HelpStates.START_LESSON
    ),
    Window(
        Const(textwrap.dedent('''
        Отправлять после урока. 
        отправить различную информацию об уроке после его окончания.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.NOTIFICATIONS),
        state=HelpStates.END_LESSON
    ),
    Window(
        Const(textwrap.dedent('''
        Отправлять перед уроками. 
        отправить различную информацию обо всех уроках перед началом.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.NOTIFICATIONS),
        state=HelpStates.START_LESSONS
    ),
    Window(
        Const(textwrap.dedent('''
        Отправлять после уроков. 
        отправить различную информацию обо всех уроках после окончания.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.NOTIFICATIONS),
        state=HelpStates.END_LESSONS
    ),

    Window(
        Const(textwrap.dedent('''
        При нажатии на кнопку "настройки" открываются различные настройки бота.
        Если ты не зарегистрирован, то будет кнопка "регистрация", а если зарегистрирован, то кнопки "изменить данные" и "удалить данные".
        Остальные кнопки показываются всегда.
        ''')),
        SwitchTo(Const('регистрация'), 'register', HelpStates.REGISTER),
        SwitchTo(Const('изменить данные'), 'change_data', HelpStates.CHANGE_DATA),
        SwitchTo(Const('удалить данные'), 'remove_data', HelpStates.REMOVE_DATA),
        SwitchTo(Const('версия'), 'version', HelpStates.VERSION),
        SwitchTo(Const('политика конфиденциальности'), 'privacy_policy', HelpStates.PRIVACY_POLICY),
        SwitchTo(Const('часть года'), 'change_quarter', HelpStates.CHANGE_QUARTER),
        SwitchTo(Const('время кеширования'), 'change_cache_time', HelpStates.CHANGE_CACHE_TIME),
        SwitchTo(Const('назад'), 'back', HelpStates.MAIN),
        state=HelpStates.SETTINGS
    ),
    Window(
        Const(textwrap.dedent('''
        Регистрация. 
        Позволяет зарегистрироваться. Без этого многие возможности не будут работать.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SETTINGS),
        state=HelpStates.REGISTER
    ),
    Window(
        Const(textwrap.dedent('''
        Изменить данные. 
        Позволяет изменять данные регистрации.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SETTINGS),
        state=HelpStates.CHANGE_DATA
    ),
    Window(
        Const(textwrap.dedent('''
        Удалить данные. 
        Удаляет данные регистрации. Можно удалять частично, а можно полностью. "Удалить все" удаляет только логин и пароль. "Удалить полностью" удаляет все данные о тебе.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SETTINGS),
        state=HelpStates.REMOVE_DATA
    ),
    Window(
        Const(textwrap.dedent('''
        Версия. 
        Номер текущей версии бота. Список изменений в обновлениях.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SETTINGS),
        state=HelpStates.VERSION
    ),
    Window(
        Const(textwrap.dedent('''
        Политика конфиденциальности. 
        Рассказывает какие данные хранятся.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SETTINGS),
        state=HelpStates.PRIVACY_POLICY
    ),
    Window(
        Const(textwrap.dedent('''
        часть года. 
        Позволяет выбрать текущую часть года. Это нужно при получении оценок.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SETTINGS),
        state=HelpStates.CHANGE_QUARTER
    ),
    Window(
        Const(textwrap.dedent('''
        Время кеширования. 
        Информация, полученная с сервера кешируется, чтобы не нагружать сервер лишними запросами. эта настройка позволяет указать максимальное время хранения в кеше.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.SETTINGS),
        state=HelpStates.CHANGE_CACHE_TIME
    ),

    Window(
        Const(textwrap.dedent('''
        Нашли ошибку? А может есть предложение по улучшению? Вы всегда можете написать разработчику @izrupy.
        
        Канал с новостями и другой важной информацией @elschoolbotnews.
        
        Исходный код (там сейчас всё плохо) теперь расположен в gitverse https://gitverse.ru/izpy/elschool_bot.
        ''')),
        SwitchTo(Const('назад'), 'back', HelpStates.MAIN),
        state=HelpStates.CONTACTS
    )
)
