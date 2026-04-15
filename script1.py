import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import sys
from dotenv import load_dotenv
import time
import openai
from functools import partial
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QPoint
from PySide6.QtCore import QDir
import csv
load_dotenv()
import io
from openai import OpenAI
import sqlite3
import shiboken6 as shiboken # Вот так он обычно импортируется в PySide6


#треш. я быдло ахахах

class AIWorker(QtCore.QObject):
    # Сигналы для передачи данных обратно в основной поток
    finished = QtCore.Signal(str) #работа закончилась
    error = QtCore.Signal(str) #работа завершилась с ошибкой

    #инициализация
    def __init__(self, test_summary, api_key):
        super().__init__()
        self.test_summary = test_summary #итоги теста (промпт)
        self.api_key = api_key #API ключ из env файла, в идеале подгружается из облака

    def run(self):
        try:
            #говорим, к кому обращаемся (open router)
            client = OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers = {
                "HTTP-Referer": "http://localhost",  # Требование OpenRouter
                "X-Title": "My Quiz App",
            }

            #генерируем промпт
            )
            response = client.chat.completions.create(
                model="z-ai/glm-4.5-air:free",
                messages=[
                    {"role": "system",
                     "content": "Ты — ассистент-преподаватель. Проанализируй ошибки ученика и дай краткие рекомендации по темам. Не форматируй текст"},
                    {"role": "user", "content": self.test_summary},
                ],
                stream=False
            )
            result = response.choices[0].message.content
            self.finished.emit(result) # Отправляем результат
        except Exception as e:
            self.error.emit(str(e)) # Отправляем ошибку


class MyWidget(QtWidgets.QWidget): #окно
    def __init__(self):
        super().__init__()
        self.resize(1000, 800)
        self.setFixedSize(1000, 800)

        # 1. Создаем StackedWidget
        self.stacked_widget = QtWidgets.QStackedWidget(self)

        # Основной Layout для всего окна
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.stacked_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

            # 2. Создаем страницы
        self.page_main = QtWidgets.QWidget()
        self.page_dirs = QtWidgets.QWidget()
        self.page_test = QtWidgets.QWidget()
        self.page_results = QtWidgets.QWidget()

            # Добавляем их в стек
        self.stacked_widget.addWidget(self.page_main)  # Индекс 0
        self.stacked_widget.addWidget(self.page_dirs)
        self.stacked_widget.addWidget(self.page_test)  # Индекс 2
        self.stacked_widget.addWidget(self.page_results)  # Индекс 3

            # Инициализируем интерфейс каждой страницы
        self.setup_main_page()
        #self.setup_test_page()

        self.all_questions = {} #вопросы, взятые из csv файла
        self.question_ids = [] #их айди
        self.current_index = 0 #индекс текущего вопроса (не айди!)
        self.user_progress_right = []
        self.user_progress_wrong = []
        self.last_id = 0 #чтобы избегать совпадающих айди ???

        self.recs_box = QtWidgets.QTextEdit()
        self.recs_box.hide()

            # Показываем главную
        self.stacked_widget.setCurrentIndex(0)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())



    def setup_main_page(self):
        #layout = QtWidgets.QVBoxLayout(self.page_main)

        self.stacked_widget.setCurrentIndex(0)

        self.page_main.setStyleSheet("background-color: #7393b3;")

        main_layout = QtWidgets.QVBoxLayout(self.page_main)
        main_layout.setContentsMargins(50, 100, 50, 50)  # Отступы от краев окна
        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)

        title = QtWidgets.QTextEdit("Добро пожаловать!",self)
        title.move(200,100)
        title.resize(700, 150)  # размеры
        title.setFont(QtGui.QFont("Sylfaen", 52, italic = True))
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        title.setTextColor("#F0F8FF")
        title.setStyleSheet("background-color: rgba(255, 0, 0, 0); border:  none"); #последний параметр rgba - прозрачность
        title.setReadOnly(True)  # Запрет на изменение текста
        main_layout.addWidget(title)

        main_layout.addStretch(1)

        button_layout = QtWidgets.QHBoxLayout()

        button1 = QtWidgets.QPushButton("Скачать дополнительные материалы", self)
        button2 = QtWidgets.QPushButton("Начать тест", self)

        font = QtGui.QFont()
        font.setFamily("Bookman Old Style")  # Название шрифта
        font.setPointSize(14)  # Размер шрифта
        button1.setFont(font)
        button2.setFont(font)
        button1.setStyleSheet("background-color: #5c6671; color: white; border: 2px solid black;")
        button2.setStyleSheet("background-color: #5c6671; color: white; border: 2px solid black;")
        button1.move(50, 700)
        button2.move(550, 700)
        button1.setFixedSize(400, 50)
        button2.setFixedSize(400, 50)

        button1.clicked.connect(self.check_action)
        button2.clicked.connect(self.tests_menu)

        button_layout.addWidget(button1)
        button_layout.addSpacing(50)  # Расстояние между кнопками
        button_layout.addWidget(button2)

        # Добавляем слой с кнопками в основной слой
        main_layout.addLayout(button_layout)

        self.all_questions = {} #вопросы, взятые из csv файла
        self.question_ids = [] #их айди
        self.current_index = 0 #индекс текущего вопроса (не айди!)
        self.user_progress_right = []
        self.user_progress_wrong = []
        self.last_id = 0 #чтобы избегать совпадающих айди ???



    #выводит скачанные модули вопросов
    def tests_menu(self):

        self.stacked_widget.setCurrentIndex(1)
        self.page_dirs.setStyleSheet("background-color: #7393b3;")

        main_layout = QtWidgets.QVBoxLayout(self.page_dirs)
        title = QtWidgets.QTextEdit("Выберите тему:", self)
        title.move(200, 100)
        title.resize(700, 150)  # размеры
        title.setFont(QtGui.QFont("Sylfaen", 52, italic=True))
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        title.setTextColor("#F0F8FF")
        title.setStyleSheet( "background-color: rgba(255, 0, 0, 0); border:  none");  # последний параметр rgba - прозрачность
        title.setReadOnly(True)  # Запрет на изменение текста
        main_layout.addWidget(title)


        #кнопка set directory
        path = "./"
        directory = QDir(path)

        # Filter for only directories and exclude "." and ".."
        filters = QDir.Dirs | QDir.NoDotAndDotDot
        dir_list = directory.entryList(filters)
        #получили список папок
        #создаём из них кнопки
        width = 1000;
        height = 800;
        height -= 350;

        button_layout = QtWidgets.QVBoxLayout()

        for i in range(len(dir_list)):
            # 1. Создаем кнопку и сразу передаем текст из списка
            button = QtWidgets.QPushButton(dir_list[i], self)
            # 3. Устанавливаем размер и положение кнопки
            button.setFixedWidth(400)
            button.setFixedHeight(80)
            button_layout.addWidget(button)
            button.clicked.connect(partial(self.start_test, dir_list[i]))

        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        button_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        main_layout.addLayout(button_layout)



#функция начала теста
    def start_test(self, dir_path):
        print(dir_path)
        dir = QDir(dir_path)

        conn = sqlite3.connect('project.db')
        cursor = conn.cursor()

        try:
            # SQL-запрос, который выбирает все нужные поля из таблицы вопросов
            # Если вам нужны вопросы только по конкретной теме, добавьте: WHERE topic_id = ?
            query = "SELECT id, topic_id, question_text, answers_json, true_answer FROM questions"
            cursor.execute(query)

            rows = cursor.fetchall()
            questions_dict = {}

            for row in rows:
                # row[0] - это id, который теперь берется прямо из базы (PRIMARY KEY)
                questions_dict[str(row[0])] = {
                    "id": row[0],  # Сохраняем собственный ID
                    "topic_id": row[1], "question_text": row[2],
                    "text": row[2],  # question_text
                    "answers": row[3],  # варианты ответов
                    "true_answer": row[4]
                }

            self.all_questions = questions_dict
            self.question_ids = list(questions_dict.keys())
            self.current_index = 0

            if self.question_ids:
                self.displayQA()

        finally:
            conn.close()  # Всегда закрываем соединение
        #os.chdir("../")
        return

    def displayQA(self):

        self.stacked_widget.setCurrentIndex(2)
        # --- ПОЛНАЯ ОЧИСТКА ---
        # --- ОЧИСТКА ДЛЯ PYSIDE6 ---

        # --- ОЧИСТКА БЕЗ SHIBOKEN (Универсальный способ) ---
        if self.page_test.layout() is not None:
            old_layout = self.page_test.layout()

            # Удаляем все виджеты
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())  # Вызываем ваш вспомогательный метод

            # Вместо shiboken.delete мы "переносим" лайаут на временный объект,
            # который тут же уничтожится, забирая лайаут с собой.
            QtWidgets.QWidget().setLayout(old_layout)

        self.page_test.setStyleSheet("background-color: #7393b3;")
        main_layout = QtWidgets.QVBoxLayout(self.page_test)

        # Проверка: остались ли еще вопросы?
        if self.current_index >= len(self.question_ids):
            self.end_of_the_test()
            return

        # 2. Получаем текущий вопрос
        current_id = self.question_ids[self.current_index]
        q_data = self.all_questions[str(current_id)]

        # 3. Отрисовка вопроса
        question = QtWidgets.QTextEdit(q_data["text"].strip('"'))
        question.setFont(QtGui.QFont("Sylfaen", 32, italic=True))
        question.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        question.setTextColor("#F0F8FF")
        question.setStyleSheet( "background-color: rgba(255, 0, 0, 0); border:  none");  # последний параметр rgba - прозрачность
        question.setReadOnly(True)  # Запрет на изменение текста
        question.setFixedHeight(250)  # размеры
        main_layout.addWidget(question)
        main_layout.setContentsMargins(0, 50, 0, 0)

        # 4. Отрисовка кнопок ответов
        answers_list = q_data["answers"].split("|")
        width, height = 1000, 800
        work_height = height - 350

        button_layout = QtWidgets.QVBoxLayout()

        for i in range(len(answers_list)):
            button = QtWidgets.QPushButton(answers_list[i], self)
            button.setFixedWidth(500)
            button.setFixedHeight(70)
            button.setFont(QtGui.QFont("Sylfaen", 14))
            button_layout.addWidget(button)
            # Важно: передаем индекс i, чтобы потом проверить правильность
            button.clicked.connect(partial(self.check_answer, q_data, i))

        main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        button_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        button_layout.setContentsMargins(0, 0, 0, 150)
        main_layout.addLayout(button_layout)
        # 3. Устанавливаем размер и положение кнопки



        # 5. Прогресс-бар (PRbox)
        pr_text = f"Вопрос {self.current_index + 1} из {len(self.all_questions)}"
        prog_box = QtWidgets.QTextEdit(pr_text)
        prog_box.setText(pr_text)
        main_layout.addWidget(prog_box)

    def check_answer(self, que, n):
        tr_an = str(que["true_answer"])
        if ( que["answers"].split("|") )[n] == tr_an:
            self.user_progress_right.append(self.question_ids[self.current_index])
        else:
            self.user_progress_wrong.append(self.question_ids[self.current_index])

        self.current_index += 1
        self.displayQA()
        #(self.user_progress_right)
        return

    def end_of_the_test(self):

        # Проверяем, что thread существует, это именно объект QThread, и он запущен
        if hasattr(self, 'thread') and isinstance(self.thread, QtCore.QThread):
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()

        # --- ОЧИСТКА БЕЗ SHIBOKEN (Универсальный способ) ---
            # 2. Правильная очистка страницы результатов
        # --- ОЧИСТКА БЕЗ SHIBOKEN (Универсальный способ) ---
        if self.page_test.layout() is not None:
            old_layout = self.page_test.layout()

            # Удаляем все виджеты
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())  # Вызываем ваш вспомогательный метод

            # Вместо shiboken.delete мы "переносим" лайаут на временный объект,
            # который тут же уничтожится, забирая лайаут с собой.
            QtWidgets.QWidget().setLayout(old_layout)

        self.stacked_widget.setCurrentIndex(3)
        self.page_results.setStyleSheet("background-color: #7393b3;")

        main_layout = QtWidgets.QVBoxLayout(self.page_results)
        pr_text = f"Результат: {(len(self.user_progress_right) / len(self.question_ids)) * 100}% правильных ответов"
        res_box = QtWidgets.QTextEdit(pr_text)
        res_box.setFixedHeight(150)
        res_box.setFont(QtGui.QFont("Sylfaen", 34))
        res_box.move(50, 100)
        main_layout.addWidget(res_box)

        self.recs_box = QtWidgets.QTextEdit("Обработка результатов, подождите...")
        self.recs_box.setFixedHeight(500)  # Это ограничит его рост вверх
        self.recs_box.setFont(QtGui.QFont("Sylfaen", 22))
        self.recs_box.setReadOnly(True)
        self.recs_box.setStyleSheet(
                "background: rgba(255, 255, 255, 30); border-radius: 10px; color: white; padding: 10px;")
        main_layout.addWidget(self.recs_box)

        # кнопка возвращения на главный экран
        ret_button = QtWidgets.QPushButton("Вернуться в главное меню")
        ret_button.setFixedHeight(50)
        ret_button.setFont(QtGui.QFont("Sylfaen", 14))
        ret_button.clicked.connect(self.setup_main_page)
        main_layout.addWidget(ret_button)

        main_layout.setContentsMargins(30, 30, 30, 30)

        self.page_results.update()  # Перерисовать виджет
        self.page_results.repaint()  # Немедленно обновить (форсированно)
        QtWidgets.QApplication.processEvents()  # Обработать все скопившиеся события отрисовки


        test_summary = self.prepare_ai_prompt()  # Собираем текст для API

            # запускаем, чтобы во время ожидания API ответа программа не замораживалась
        self.thread = QtCore.QThread()

        self.worker = AIWorker(test_summary, os.getenv('OPENROUTER_API_KEY'))
        self.worker.moveToThread(self.thread)

            # Соединяем сигналы
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_ai_finished)
        self.worker.error.connect(self.on_ai_error)

            # Очистка памяти после завершения
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()



    def prepare_ai_prompt(self):
        report = "Проанализируй результаты теста и дай краткие рекомендации:\n"

        for q_id in self.question_ids:
            q_data = self.all_questions[q_id]
            status = "Правильно" if q_id in self.user_progress_right else "Неправильно"

            report += f"- Вопрос: {q_data['text']}\n"
            report += f"  Результат: {status}\n"

        return report


    def on_ai_finished(self, text):
        self.recs_box.setText(text)
        self.recs_box.setStyleSheet("background: transparent; border: none; color: white;")

    # Слот для ошибки
    def on_ai_error(self, error_message):
        print(f"Ошибка AI: {error_message}")


### ДАЛЬШЕ ТОКА МУСОР !!!

























    @QtCore.Slot()
    #действие "проверить", пока тут просто стоит заглушка
    def check_action(self):
        self.clear_window()
        self.background_label.setPixmap(QtGui.QPixmap("white_canvas.png"))

    #действие "не проверять", но не конечное




    #функция, не несущая большого смысла, просто для удобства чтения кода
    #прячет текст
    def hide_my_message(self):
        if self.k >= 1:
            self.question.hide()
        else: return

    #функция для изменения размера кнопки
    def change_size(self):
        self.button2.setFixedSize( 400+50*(12-self.k), 50)
        self.button2.setFont(QtGui.QFont("Bookman Old Style", 14 + (12-self.k)))
        self.button2.move(550 - 25*(12-self.k), 700)

    #если игрок ОЧЕНЬ настойчиво выбирал "не проверять"
    #почти новая страница, 1.1
    def jump_to_dont(self):
        #пряяем кнопки
        self.button2.hide()
        self.button1.hide()

        #меняем фон на белый
        self.background_label.setPixmap(QtGui.QPixmap("white_canvas.png"))

        #таймер для первой задержки (2 секунды)
        QtCore.QTimer.singleShot(2000, lambda: self.change_to_black())

    def change_to_black(self):
        #меняем фон на чёрный
        self.background_label.setPixmap(QtGui.QPixmap('black_canvas.png'))

        #таймер для второй задержки (2 секунды)
        QtCore.QTimer.singleShot(2000, lambda: self.change_back())

    def change_back(self):
        #меняем фон опять (снова) - страница 1.1
        self.background_label.setPixmap(QtGui.QPixmap('pygame_holding_door.png'))
        #вот тут как бэ ошибочка потому что наверно стоило старую кнопку использовать
        #но пока оставим так
        #расписываем как выглядит кнопка
        push_button_font = QtGui.QFont("Courier", 20)
        self.button_push.setFont(push_button_font)
        self.button_push.hide()
        self.button_push.move(50,500)
        self.button_push.setFixedSize(200,50)
        self.button_push.setStyleSheet("background-color: #5c6671;border: 2px solid black;")
        self.button_push.show()
        self.k = 0
        #коннектим с пушинг дор
        self.button_push.clicked.connect(self.pushing_door)


    #функция для открытия двери
    #в основном просто показывает и меняет текст
    #потом переходит в мини-игру открыть дверь
    def pushing_door(self):
        #текст для высвечивания на экране
        push_mono = ["I should leave, then...", "I just... have to open the door.", "Am I sure?",
                     "Isn't it better if I check..."]
        #настройка внешнего вида сообщения
        self.question = QtWidgets.QTextEdit("",self)
        self.question.setFont(QtGui.QFont("Sylfaen", 18, italic=True))
        self.question.setFixedSize(400, 50)
        self.question.setStyleSheet("background-color: #2c3742")
        self.question.move(450, 50)
        self.question.show()

        #настройка прогресс бара
        self.prog_bar.setRange(0,500)
        self.prog_bar.move(425, 200)
        self.prog_bar.setFixedWidth(450)
        self.prog_bar.setStyleSheet("""
            QProgressBar {
                height: 15px;
                border-style: solid;
                border-width: 2px;
                border-color: black;
                background-color: #FFFFFF;  /* Background color of the progress bar */
            }
            QProgressBar::chunk {
                background-color: #FFD580;  /* Color of the progress chunks */
                width: 7px;                 /* Width of each chunk */
            }
        """)
        self.prog_bar.setTextVisible(False)

        if self.k < 4:
            #от 0 до 3 меняем текст
            #я уверена что это можно оптимизировать но мне лень думать как
            #погнали перегрузку компа
            self.question.setPlainText(push_mono[self.k])
            self.k += 1
        else:
            self.question.hide()#прячем сообщение
            self.background_label.setPixmap(QtGui.QPixmap('pygame_holding_theDOOR.png')) #меняем бэкграунд
            self.button_push.clicked.connect(self.opening_door)#коннектим button_push с новой функцией
            #старая (вроде) не выполняется, k = 0

            self.button_push.setText("PUSH.")
            self.prog_bar.show() #показываем прогресс бар

            #таймер, который срабатывает каждые 150 мс. Каждый раз уменьшает значение progress_bar
            #подробнее про значения прогресс бар в следующей функции
            #таймер запускается только после нажатия на кнопку 5 раз
            self.decrease_timer.timeout.connect(self.decrease)
            self.decrease_timer.start(150)  # Вызывается каждые 150 мс

    #та самая мини-игра "открыть дверь"
    def opening_door(self):
        cur_val = self.prog_bar.value()
        #запоминаем текущее значение прогресс бара
        self.prog_bar.setValue(cur_val + 4)
        #увеличиваем значение ПБ на 4, так как кнопка была нажата
        #при значении больше 490 переходим наконец в не-проверять концовку
        #и останавливаем таймер
        if self.prog_bar.value() >= 490: #то есть если ПБ (почти) заполнена
            self.decrease_timer.stop()
            self.dont_check_ending()


    #концовка не-проверять. пока что стоит заглушка
    def dont_check_ending(self):
        self.clear_window()
        self.background_label.setPixmap(QtGui.QPixmap('black_canvas.png'))

    #уменьшение значения ПБ
    def decrease(self):
        cur_val = self.prog_bar.value()
        if cur_val > 0:
            self.prog_bar.setValue(cur_val - 1)
        #если значение ПБ опустилось до нуля
        if self.prog_bar.value() == 0:
            self.decrease_timer.stop() #становка таймера
            self.check_action() #проверить-концовка

    #ХААААХ я реально только так придумала
    def clear_window(self):
        for widget in self.findChildren(QtWidgets.QWidget):
            widget.hide()




#это треш. я ничего не вынесла из курса ооп.
#я продолжу походу переодически создавать новые окна АААА



        #self.layout.setContentsMargins(0, 200, 0, 0) #отступ для лэйаута
        #self.layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)  #ыравнивание по центру

        #таймер (нужен для строки прогресса)
        #self.decrease_timer = QtCore.QTimer(self)

        #строка прогресса
        #self.prog_bar = QtWidgets.QProgressBar(self)
        #self.prog_bar.hide()
        #может реализую позже

        #текст (заголовок)





        #модуль с рекомендациями
        #инициализируется здесь для передачи в другю функцию


        #прогресс вопросов
        '''
        ДОБАВИТЬ НА 2 СТРАНИЦУ
        self.recs_box = QtWidgets.QTextEdit("Анализирую результаты, подождите...", self)
        self.recs_box.hide()
        pr_box = QtWidgets.QTextEdit("", self)
        pr_box.move(0, 750)
        pr_box.resize(500, 50)
        pr_box.setStyleSheet("background: transparent; border: none; color: white;")
        pr_box.setFont(QtGui.QFont("Sylfaen", 14))
        pr_box.setReadOnly(True)
        self.prog_box = pr_box
        self.prog_box.hide()
        #результаты одного (!) теста
        '''





if __name__ == "__main__":
            app = QtWidgets.QApplication([])

            widget = MyWidget()
            widget.resize(1000, 800)
            widget.show()

            sys.exit(app.exec())