import os
os.environ["PYTHONIOENCODING"] = "utf-8"
import sys
from dotenv import load_dotenv

from functools import partial
from PySide6 import QtCore, QtWidgets, QtGui

load_dotenv()
import re
from openai import OpenAI
import sqlite3
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTreeWidget,
                             QTreeWidgetItem, QPushButton, QTreeWidgetItemIterator)
import requests


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
        #self.setFixedSize(1000, 800)

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

        self.test_tree = QtWidgets.QTreeWidget()
        self.test_tree.hide()

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
        # Переключаемся на главную страницу
        self.stacked_widget.setCurrentIndex(0)

        # Очищаем предыдущие результаты теста
        self.user_progress_right = []
        self.user_progress_wrong = []

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
        button3 = QtWidgets.QPushButton("Добавить вопрос", self)

        font = QtGui.QFont()
        font.setFamily("Bookman Old Style")  # Название шрифта
        font.setPointSize(14)  # Размер шрифта
        button1.setFont(font)
        button2.setFont(font)
        button3.setFont(font)
        button1.setStyleSheet("background-color: #5c6671; color: white; border: 2px solid black;")
        button2.setStyleSheet("background-color: #5c6671; color: white; border: 2px solid black;")
        button3.setStyleSheet("background-color: #5c6671; color: white; border: 2px solid black;")
        #button1.move(50, 700)
        #button2.move(550, 700)
        #button1.setFixedSize(400, 50)
        #button2.setFixedSize(400, 50)

        button1.setMinimumHeight(50)
        button1.setMinimumWidth(400)
        button2.setMinimumHeight(50)
        button2.setMinimumWidth(200)
        button3.setMinimumHeight(50)
        button3.setMinimumWidth(200)

        button1.clicked.connect(self.downld_action)
        button2.clicked.connect(self.tests_menu)
        button3.clicked.connect(self.open_add_question_dialog)

        button_layout.addWidget(button1)
        button_layout.addStretch()  # Расстояние между кнопками
        button_layout.addWidget(button2)
        button_layout.addStretch()
        button_layout.addWidget(button3)

        # Добавляем слой с кнопками в основной слой
        main_layout.addLayout(button_layout)

        self.all_questions = {} #вопросы, взятые из csv файла
        self.question_ids = [] #их айди
        self.current_index = 0 #индекс текущего вопроса (не айди!)
        self.user_progress_right = []
        self.user_progress_wrong = []
        self.last_id = 0 #чтобы избегать совпадающих айди ???

    def tests_menu(self):
        self.stacked_widget.setCurrentIndex(1)
        self.page_dirs.setStyleSheet("background-color: #7393b3;")

        # Очистка старого лайаута, если он есть
        if self.page_dirs.layout():
            QtWidgets.QWidget().setLayout(self.page_dirs.layout())

        main_layout = QtWidgets.QVBoxLayout(self.page_dirs)

        title = QtWidgets.QLabel("Выберите тему для тестирования:")
        title.setFont(QtGui.QFont("Sylfaen", 28, italic=True))
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("color: #F0F8FF; margin-top: 20px;")
        main_layout.addWidget(title)

        # Используем QTreeWidget для отображения иерархии папок
        self.test_tree = QtWidgets.QTreeWidget()
        self.test_tree.setHeaderLabel("Скачанные материалы")
        self.test_tree.setStyleSheet("""
        QTreeWidget {
            background-color: #121212;
            color: #FFFFFF;
            border: 1px solid #444;
            font-size: 14px;
        }
        QTreeWidget::item {
            padding: 5px;
            border-bottom: 1px solid #222;
        }
        QTreeWidget::item:selected {
            background-color: #333333;
        }
        QHeaderView::section {
            background-color: #1f1f1f;
            color: white;
            padding: 4px;
            border: 1px solid #444;
        }
        QTreeWidget::indicator {
            width: 18px;
            height: 18px;
        }
    """)
        main_layout.addWidget(self.test_tree)

        # Путь к скачанным файлам
        base_path = "./downloads"
        if os.path.exists(base_path):
            self.populate_tree(base_path, self.test_tree.invisibleRootItem())
        else:
            self.test_tree.setHeaderLabel("Папка downloads не найдена")

        # Кнопка запуска теста
        self.btn_start = QtWidgets.QPushButton("Начать тест по выбранной теме")
        self.btn_start.setFixedHeight(50)
        self.btn_start.setFont(QtGui.QFont("Sylfaen", 14, QtGui.QFont.Bold))
        self.btn_start.clicked.connect(self.prepare_test_launch)
        main_layout.addWidget(self.btn_start)

    def populate_tree(self, path, parent_item):
        """Рекурсивно заполняет дерево папками из downloads с авто-состоянием галочек"""
        for name in os.listdir(path):
            full_path = os.path.join(path, name)

            if os.path.isdir(full_path):
                item = QtWidgets.QTreeWidgetItem(parent_item, [name])

                # Добавляем флаги:
                # ItemIsUserCheckable — можно кликать
                # ItemIsAutoTristate — родитель реагирует на детей, а дети на родителя
                item.setFlags(item.flags() |
                              QtCore.Qt.ItemFlag.ItemIsUserCheckable |
                              QtCore.Qt.ItemFlag.ItemIsAutoTristate)

                # По умолчанию галочка не стоит
                item.setCheckState(0, QtCore.Qt.CheckState.Unchecked)
                item.setData(0, QtCore.Qt.UserRole, full_path)

                # Рекурсия для вложенных папок
                self.populate_tree(full_path, item)

    def prepare_test_launch(self):
        selected_paths = []
        # Итератор по всем элементам дерева, у которых стоит галочка
        it = QtWidgets.QTreeWidgetItemIterator(self.test_tree, QtWidgets.QTreeWidgetItemIterator.IteratorFlag.Checked)

        while it.value():
            item = it.value()
            path = item.data(0, QtCore.Qt.UserRole)

            # Проверяем, есть ли внутри .db файл (чтобы не брать пустые папки разделов)
            if path and os.path.exists(path):
                db_files = [f for f in os.listdir(path) if f.endswith('.db')]
                if db_files:
                    selected_paths.append(path)
            it += 1

        if not selected_paths:
            print("Ничего не выбрано!")
            return

        # Теперь вызываем загрузку, передавая список путей
        self.start_combined_test(selected_paths)


#функция начала теста
    def start_combined_test(self, paths):
        # Очищаем предыдущие результаты
        self.user_progress_right = []
        self.user_progress_wrong = []

        self.all_questions = {}
        current_global_id = 0

        self.all_questions = {}
        current_global_id = 0  # Общий счетчик, чтобы ID не дублировались

        for dir_path in paths:
            # Находим .db файл в текущей папке
            files = [f for f in os.listdir(dir_path) if f.endswith('.db')]
            if not files:
                continue

            db_path = os.path.join(dir_path, files[0])

            # Подключаемся к базе конкретной темы
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            try:
                # Выбираем вопросы из локальной таблицы темы
                cursor.execute("SELECT text, options, answer FROM local_questions")
                rows = cursor.fetchall()

                for row in rows:
                    # Записываем в общий словарь под уникальным ключом
                    self.all_questions[str(current_global_id)] = {
                        "id": current_global_id,
                        "text": row[0],
                        "answers": row[1],
                        "true_answer": row[2]
                    }
                    current_global_id += 1
            except Exception as e:
                print(f"Ошибка чтения базы {db_path}: {e}")
            finally:
                conn.close()

        # Если вопросы найдены, запускаем отображение
        if self.all_questions:
            self.question_ids = list(self.all_questions.keys())
            # Перемешиваем вопросы, если нужно, чтобы темы шли вперемешку
            import random
            random.shuffle(self.question_ids)

            self.current_index = 0
            self.displayQA()
        else:
            print("Вопросы не найдены в выбранных материалах.")

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
        tr_an = str(que["true_answer"]).strip()
        user_answer = que["answers"].split("|")[n].strip()

        # Отладка
        print(f"Правильный ответ: '{tr_an}'")
        print(f"Ответ пользователя: '{user_answer}'")
        print(f"Совпадают: {user_answer == tr_an}")

        if user_answer == tr_an:
            self.user_progress_right.append(self.question_ids[self.current_index])
        else:
            self.user_progress_wrong.append(self.question_ids[self.current_index])

        self.current_index += 1
        self.displayQA()

    def end_of_the_test(self):
        # Проверяем, что thread существует, это именно объект QThread, и он запущен
        if hasattr(self, 'thread') and isinstance(self.thread, QtCore.QThread):
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()

        # Очищаем страницу результатов, а не страницу теста!
        if self.page_results.layout() is not None:
            old_layout = self.page_results.layout()
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())
            QtWidgets.QWidget().setLayout(old_layout)

        self.stacked_widget.setCurrentIndex(3)
        self.page_results.setStyleSheet("background-color: #7393b3;")

        main_layout = QtWidgets.QVBoxLayout(self.page_results)

        # Подсчет процента
        if len(self.question_ids) > 0:
            percentage = (len(self.user_progress_right) / len(self.question_ids)) * 100
        else:
            percentage = 0

        pr_text = f"Результат: {percentage:.1f}% правильных ответов.\n"
        pr_text += f"Правильно: {len(self.user_progress_right)} из {len(self.question_ids)}"

        res_box = QtWidgets.QTextEdit(pr_text)
        res_box.setFixedHeight(150)
        res_box.setFont(QtGui.QFont("Sylfaen", 34))
        res_box.setStyleSheet("background-color: rgba(255, 0, 0, 0); border: none; color: #F0F8FF;")
        res_box.setReadOnly(True)
        res_box.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(res_box)

        self.recs_box = QtWidgets.QTextEdit("Обработка результатов, подождите...")
        self.recs_box.setFixedHeight(500)
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

        self.page_results.update()
        self.page_results.repaint()
        QtWidgets.QApplication.processEvents()

        test_summary = self.prepare_ai_prompt()

        # запускаем поток для AI
        self.thread = QtCore.QThread()
        self.worker = AIWorker(test_summary, os.getenv('OPENROUTER_API_KEY'))
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_ai_finished)
        self.worker.error.connect(self.on_ai_error)

        # Правильное завершение потока
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



    @QtCore.Slot()
    def open_add_question_dialog(self):
        dialog = AddQuestionDialog(self)
        dialog.exec()

    @QtCore.Slot()
    #действие "скачать"
    def downld_action(self):
        # Создаем и открываем модальное окно
        self.menu = DownloadMenu("project.db")
        self.menu.exec()


### ДАЛЬШЕ ТОКА МУСОР !!!
























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


class DownloadMenu(QDialog):
    def __init__(self, db_path):
        super().__init__()
        self.setWindowTitle("Выбор материалов для скачивания")
        self.resize(500, 600)
        self.db_path = db_path
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Дерево выбора
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Доступные материалы")
        layout.addWidget(self.tree)

        # Кнопка скачать
        self.btn_download = QPushButton("Скачать выбранное")
        self.btn_download.clicked.connect(self.start_download)
        layout.addWidget(self.btn_download)

    def load_data(self):
        try:
            # Делаем запрос к локальному серверу
            # Сервер должен вернуть структуру в формате JSON
            response = requests.get("http://127.0.0.1:5000/get_structure") #наш локальный сайт
            if response.status_code == 200:
                data = response.json()  # Ожидаем список объектов

                #вывод списков
                for subject in data:
                    s_item = QTreeWidgetItem(self.tree, [subject['name']])
                    s_item.setFlags(s_item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsAutoTristate)
                    s_item.setCheckState(0, QtCore.Qt.Unchecked)
                    s_item.setData(0, QtCore.Qt.UserRole, {"type": "subject", "id": subject['id']})

                    for section in subject.get('sections', []):
                        sec_item = QTreeWidgetItem(s_item, [section['name']])
                        sec_item.setFlags(sec_item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsAutoTristate)
                        sec_item.setCheckState(0, QtCore.Qt.Unchecked)
                        sec_item.setData(0, QtCore.Qt.UserRole, {"type": "section", "id": section['id']})

                        for topic in section.get('topics', []):
                            t_item = QTreeWidgetItem(sec_item, [topic['name']])
                            t_item.setFlags(t_item.flags() | QtCore.Qt.ItemIsUserCheckable)
                            t_item.setCheckState(0, QtCore.Qt.Unchecked)
                            t_item.setData(0, QtCore.Qt.UserRole, {"type": "topic", "id": topic['id']})
            else:
                print("Ошибка сервера:", response.status_code)
        except Exception as e:
            print(f"Не удалось подключиться к серверу: {e}")

    def get_item_path(self, item):
        """Рекурсивно собирает путь из названий элементов дерева"""
        path_parts = []
        current = item
        while current:
            # Убираем символы, которые запрещены в именах папок ОС
            name = re.sub(r'[\\/*?:"<>|]', "", current.text(0))
            path_parts.append(name)
            current = current.parent()

        # Разворачиваем список (от Предмета к Теме) и объединяем в путь
        return os.path.join("downloads", *reversed(path_parts))

    def get_item_path(self, item):
        """Рекурсивно собирает путь из названий элементов дерева"""
        path_parts = []
        current = item
        while current:
            # Убираем символы, которые запрещены в именах папок ОС
            name = re.sub(r'[\\/*?:"<>|]', "", current.text(0))
            path_parts.append(name)
            current = current.parent()

        # Разворачиваем список (от Предмета к Теме) и объединяем в путь
        return os.path.join("downloads", *reversed(path_parts))

    def start_download(self):
        it = QTreeWidgetItemIterator(self.tree, QTreeWidgetItemIterator.Checked)

        while it.value():
            item = it.value()
            data = item.data(0, QtCore.Qt.UserRole)

            # Скачиваем только если это конечная тема (или файл)
            if data["type"] == "topic":
                topic_id = data["id"]

                # 1. Создаем структуру папок на основе дерева в UI
                target_dir = self.get_item_path(item)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                try:
                    # 2. Запрашиваем сервер. Сервер теперь должен использовать таблицу resources
                    # чтобы найти путь к файлу и его оригинальное имя
                    url = f"http://127.0.0.1:5000/download/{topic_id}"
                    response = requests.get(url, stream=True)

                    if response.status_code == 200:
                        # Достаем имя файла из заголовка Content-Disposition (его должен прислать сервер)
                        # Если сервер его не прислал, используем стандартное имя
                        content_disp = response.headers.get('Content-Disposition')
                        if content_disp:
                            filename = re.findall("filename=(.+)", content_disp)[0].strip('"')
                        else:
                            filename = f"topic_{topic_id}.db"

                        full_file_path = os.path.join(target_dir, filename)

                        with open(full_file_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        print(f"Сохранено в: {full_file_path}")
                    else:
                        print(f"Ошибка сервера для ID {topic_id}")

                except Exception as e:
                    print(f"Ошибка при скачивании {topic_id}: {e}")

            it += 1





class AddQuestionDialog(QDialog):
    """
    Диалог добавления нового вопроса в локальную базу данных.

    Структура downloads/:
        downloads/
          <Предмет>/
            <Раздел>/
              <Тема>/
                <тема>.db  (таблица local_questions: text, options, answer)

    Пользователь может:
      • Выбрать существующую тему из дерева папок downloads
      • Или ввести вручную Предмет / Раздел / Тему (создадутся автоматически)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить вопрос")
        self.resize(600, 700)
        self.setStyleSheet("background-color: #2b2b2b; color: #f0f8ff;")
        self.answer_radios = []
        self.answers_group = QtWidgets.QButtonGroup(self)
        self.answers_group.setExclusive(True)
        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(20, 20, 20, 20)

        label_style = "font-size: 13px; font-weight: bold; color: #cce0ff;"
        input_style = (
            "background-color: #3c3f41; color: white; "
            "border: 1px solid #555; border-radius: 4px; padding: 4px;"
        )
        btn_style = (
            "background-color: #5c6671; color: white; "
            "border: 2px solid #888; border-radius: 4px; padding: 6px;"
        )

        # --- Выбор темы из дерева ---
        root.addWidget(self._lbl("📂  Выберите тему из скачанных материалов:", label_style))

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabel("downloads/")
        self.tree.setFixedHeight(180)
        self.tree.setStyleSheet(
            "QTreeWidget { background: #1e1e1e; color: white; border: 1px solid #555; }"
            "QTreeWidget::item:selected { background: #3a5f8a; }"
        )
        self._populate_tree()
        self.tree.itemClicked.connect(self._on_tree_select)
        root.addWidget(self.tree)

        # --- Разделитель ---
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #555;")
        root.addWidget(line)

        root.addWidget(self._lbl("✏️  Или укажите путь вручную:", label_style))

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(6)

        self.le_subject = QtWidgets.QLineEdit()
        self.le_subject.setPlaceholderText("Предмет (папка 1-го уровня)")
        self.le_subject.setStyleSheet(input_style)

        self.le_section = QtWidgets.QLineEdit()
        self.le_section.setPlaceholderText("Раздел (папка 2-го уровня)")
        self.le_section.setStyleSheet(input_style)

        self.le_topic = QtWidgets.QLineEdit()
        self.le_topic.setPlaceholderText("Тема (папка 3-го уровня / имя .db)")
        self.le_topic.setStyleSheet(input_style)

        grid.addWidget(self._lbl("Предмет:", label_style), 0, 0)
        grid.addWidget(self.le_subject, 0, 1)
        grid.addWidget(self._lbl("Раздел:", label_style), 1, 0)
        grid.addWidget(self.le_section, 1, 1)
        grid.addWidget(self._lbl("Тема:", label_style), 2, 0)
        grid.addWidget(self.le_topic, 2, 1)
        root.addLayout(grid)

        # --- Вопрос ---
        line2 = QtWidgets.QFrame()
        line2.setFrameShape(QtWidgets.QFrame.HLine)
        line2.setStyleSheet("color: #555;")
        root.addWidget(line2)

        root.addWidget(self._lbl("❓  Текст вопроса:", label_style))
        self.te_question = QtWidgets.QTextEdit()
        self.te_question.setFixedHeight(70)
        self.te_question.setStyleSheet(input_style)
        self.te_question.setPlaceholderText("Введите вопрос...")
        root.addWidget(self.te_question)

        # --- Варианты ответов ---
        root.addWidget(self._lbl("🔘  Варианты ответов (минимум 2):", label_style))

        self.answer_edits = []
        self.answer_radios = []
        self.answers_group = QtWidgets.QButtonGroup(self)

        self.answers_container = QtWidgets.QVBoxLayout()
        for i in range(4):
            row, le, rb = self._make_answer_row(i, input_style)
            self.answers_container.addLayout(row)
            self.answer_edits.append(le)
            self.answer_radios.append(rb)
            self.answers_group.addButton(rb, i)

        root.addLayout(self.answers_container)

        # --- Кнопки ---
        btn_row = QtWidgets.QHBoxLayout()
        btn_save = QtWidgets.QPushButton("💾  Сохранить вопрос")
        btn_save.setStyleSheet(btn_style)
        btn_save.setFixedHeight(40)
        btn_save.clicked.connect(self._save_question)

        btn_cancel = QtWidgets.QPushButton("Отмена")
        btn_cancel.setStyleSheet(btn_style)
        btn_cancel.setFixedHeight(40)
        btn_cancel.clicked.connect(self.reject)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_cancel)
        root.addLayout(btn_row)

        # Статус
        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 12px;")
        root.addWidget(self.lbl_status)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _lbl(text, style=""):
        lbl = QtWidgets.QLabel(text)
        if style:
            lbl.setStyleSheet(style)
        return lbl

    def _make_answer_row(self, idx, input_style):
        row = QtWidgets.QHBoxLayout()
        rb = QtWidgets.QCheckBox(f"Правильный ответ {idx + 1}")
        rb.setStyleSheet("""
            QCheckBox {
                color: #aaffaa;
                font-size: 14px;
                font-weight: bold;
                spacing: 8px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #aaffaa;
                border-radius: 4px;
                background-color: #2b2b2b;
            }
            QCheckBox::indicator:checked {
                background-color: #aaffaa;
                border: 2px solid #00cc00;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #aaffaa;
                background-color: #3a5f3a;
            }
        """)
        le = QtWidgets.QLineEdit()
        le.setPlaceholderText(f"Ответ {idx + 1}")
        le.setStyleSheet(input_style)
        row.addWidget(rb)
        row.addWidget(le)
        return row, le, rb

    # ------------------------------------------------------------------ #
    #  Дерево downloads
    # ------------------------------------------------------------------ #
    def _populate_tree(self):
        base = "./downloads"
        self.tree.clear()
        if not os.path.exists(base):
            self.tree.setHeaderLabel("Папка downloads не найдена")
            return
        self._fill_tree_node(base, self.tree.invisibleRootItem(), depth=0)

    def _fill_tree_node(self, path, parent, depth):
        """Рекурсивно строит дерево до 3-го уровня (тема)."""
        if depth > 2:
            return
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isdir(full):
                item = QtWidgets.QTreeWidgetItem(parent, [name])
                item.setData(0, QtCore.Qt.UserRole, full)
                self._fill_tree_node(full, item, depth + 1)

    def _on_tree_select(self, item, _col):
        """Заполняет текстовые поля при выборе элемента в дереве."""
        path = item.data(0, QtCore.Qt.UserRole)
        if not path:
            return
        # Разбиваем путь относительно downloads/
        rel = os.path.relpath(path, "./downloads")
        parts = rel.replace("\\", "/").split("/")
        fields = [self.le_subject, self.le_section, self.le_topic]
        for i, field in enumerate(fields):
            field.setText(parts[i] if i < len(parts) else "")

    # ------------------------------------------------------------------ #
    #  Сохранение
    # ------------------------------------------------------------------ #
    def _save_question(self):
        # 1. Путь
        subject = self.le_subject.text().strip()
        section = self.le_section.text().strip()
        topic = self.le_topic.text().strip()

        if not subject or not section or not topic:
            self._status("⚠️ Укажите Предмет, Раздел и Тему.", "#ffaa44")
            return

        # 2. Текст вопроса
        question_text = self.te_question.toPlainText().strip()
        if not question_text:
            self._status("⚠️ Введите текст вопроса.", "#ffaa44")
            return

        # 3. Ответы
        answers = [le.text().strip() for le in self.answer_edits]
        filled = [a for a in answers if a]
        if len(filled) < 2:
            self._status("⚠️ Введите минимум 2 варианта ответа.", "#ffaa44")
            return

        correct_idx = self.answers_group.checkedId()
        if correct_idx == -1:
            self._status("⚠️ Отметьте правильный ответ.", "#ffaa44")
            return

        correct_answer = answers[correct_idx]
        if not correct_answer:
            self._status("⚠️ Правильный ответ не может быть пустым — заполните его текст.", "#ffaa44")
            return
        if correct_answer not in filled:
            self._status("⚠️ Правильный ответ должен быть среди заполненных вариантов.", "#ffaa44")
            return

        options_str = "|".join(filled)  # Формат: "А|Б|В|Г"

        # 4. Создаём папки
        # Очищаем имена от запрещённых символов (как в DownloadMenu)
        def sanitize(name):
            return re.sub(r'[\\/*?:"<>|]', "", name)

        safe_subject = sanitize(subject)
        safe_section = sanitize(section)
        safe_topic = sanitize(topic)

        topic_dir = os.path.join("downloads", safe_subject, safe_section, safe_topic)
        os.makedirs(topic_dir, exist_ok=True)

        # 5. Открываем / создаём .db файл
        db_name = safe_topic + ".db"
        db_path = os.path.join(topic_dir, db_name)

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Создаём таблицу, если её ещё нет (совместима с start_combined_test)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS local_questions (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    text    TEXT    NOT NULL,
                    options TEXT    NOT NULL,
                    answer  TEXT    NOT NULL
                )
            """)

            cursor.execute(
                "INSERT INTO local_questions (text, options, answer) VALUES (?, ?, ?)",
                (question_text, options_str, correct_answer)
            )
            conn.commit()
            conn.close()

            self._status(f"✅ Вопрос сохранён в {db_path}", "#aaffaa")
            self._clear_form()

        except Exception as e:
            self._status(f"❌ Ошибка: {e}", "#ff6666")

    def _status(self, text, color="#ffffff"):
        self.lbl_status.setText(text)
        self.lbl_status.setStyleSheet(f"font-size: 12px; color: {color};")

    def _clear_form(self):
        self.te_question.clear()
        for le in self.answer_edits:
            le.clear()
        self.answers_group.setExclusive(False)
        for rb in self.answer_radios:
            rb.setChecked(False)
        self.answers_group.setExclusive(True)
        # Обновляем дерево (вдруг создали новую тему)
        self._populate_tree()


if __name__ == "__main__":
            app = QtWidgets.QApplication([])

            widget = MyWidget()
            widget.resize(1000, 800)
            widget.show()

            sys.exit(app.exec())