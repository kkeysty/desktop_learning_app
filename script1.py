import sys
import time
import openai
from functools import partial
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QPoint
from PySide6.QtCore import QDir
import csv
import os
import openai
from openai import OpenAI

#треш. я быдло ахахах


class MyWidget(QtWidgets.QWidget): #окно
    def __init__(self):
        super().__init__()

        #все элементы окна, здесь сразу инициализируются для первой страницы

        #задаём background label, будет на каждой странице
        self.background_label = QtWidgets.QLabel(self)
        self.background_label.setGeometry(0, 0, 1000, 800)  # Размеры как у окна
        self.background_label.setStyleSheet("background-color: #7393b3;")

        #задаём QPushButtons, будут только на главной странице
        self.button1 = QtWidgets.QPushButton("Скачать дополнительные материалы", self)
        self.button2 = QtWidgets.QPushButton("Начать тест",self)

        #счётчик для всего подряд
        self.k = 0

        #добавление кнопок и текста в лэйаут
        self.resize(1000,800)
        self.layout = QtWidgets.QHBoxLayout(self)

        # Список для хранения ссылок на кнопки
        self.buttons = []

        font = QtGui.QFont()
        font.setFamily("Bookman Old Style")  # Название шрифта
        font.setPointSize(14)  # Размер шрифта
        self.button1.setFont(font)
        self.button2.setFont(font)
        self.button1.setStyleSheet("background-color: #5c6671; color: white; border: 2px solid black;")
        self.button2.setStyleSheet("background-color: #5c6671; color: white; border: 2px solid black;")
        self.button1.move(50, 700)
        self.button2.move(550, 700)
        self.button1.setFixedSize(400, 50)
        self.button2.setFixedSize(400, 50)

        #коннект
        self.button1.clicked.connect(self.check_action)
        self.button2.clicked.connect(self.tests_menu)

        #ещё одна пушбаттон, скорее всего можно было обойтись без неё
        #просто переделать существующие
        self.button_push = QtWidgets.QPushButton("Go out", self)
        self.button_push.hide()

        #строка прогресса
        self.prog_bar = QtWidgets.QProgressBar(self)
        self.prog_bar.hide()

        #текст
        self.question = QtWidgets.QTextEdit("Добро пожаловать!",self)
        self.question.move(200,100)
        self.question.resize(700, 150)  # размеры
        self.question.setFont(QtGui.QFont("Sylfaen", 52, italic = True))
        self.question.setTextColor("#F0F8FF")
        self.question.setStyleSheet("background-color: rgba(255, 0, 0, 0); border:  none"); #последний параметр - прозрачность
        self.question.setReadOnly(True)  # Запрет на изменение текста
        self.question.show()

        self.all_questions = {}
        self.question_ids = []
        self.current_index = 0
        #таймер (нужен для строки прогресса)
        self.decrease_timer = QtCore.QTimer(self)
        self.last_id = 0 #чтобы избегать совпадающих айди

        self.user_progress_right = []
        self.user_progress_wrong = []


    #выводит скачанные модули вопросов
    def tests_menu(self):
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
        one_step = height / (len(dir_list) - 1) if len(dir_list) > 1 else 1
        #пряяем кнопки
        self.button2.hide()
        self.button1.hide()
        self.question.hide()
        for i in range(len(dir_list)):
            # 1. Создаем кнопку и сразу передаем текст из списка
            button = QtWidgets.QPushButton(dir_list[i], self)

            # 2. Рассчитываем позицию Y (индекс * шаг)
            y_position = int(i * one_step) + 200

            # 3. Устанавливаем размер и положение кнопки
            button.setFixedWidth(500)
            button.setFixedHeight(80)
            button.move(50, y_position)  # x=50, y=рассчитанный шаг
            button.clicked.connect(partial(self.start_test, dir_list[i]))
            button.show()
            self.buttons.append(button)



        print(dir_list)

#функция начала теста
    def start_test(self, dir_path):
        print(dir_path)
        dir = QDir(dir_path)
        filters = QDir.Files | QDir.NoDotAndDotDot
        dir.setNameFilters({"*.csv"})
        files_list = dir.entryList(filters)


        os.chdir(dir_path)
        with open(files_list[0], mode='r', encoding='utf-8', newline='') as file:
            reader = csv.reader(file)
            count = 0
            questions_dict = {}
            for rowd in reader:
                #print(rowd)  # row - это список значений
                row = rowd[0].split(";")
                if count >= 1:
                    questions_dict[str(row[0])] = {
                        "text": row[1],
                        "audio" : row[2],
                        "video" : row[3],
                        "photo": row[4],
                        "answers": row[5],
                        "true_answer": row[6]
                    }
                    print(questions_dict)
                    self.all_questions = questions_dict
                    self.question_ids = list(questions_dict.keys())
                    self.current_index = 0
                    self.displayQA()  # Вызываем без аргументов, берем данные из self
                count += 1
            #print(questions_dict)

        os.chdir("../")
        return

    def displayQA(self):
        # 1. Очистка старых виджетов
        if len(self.buttons) > 0:
            for obj in self.buttons:
                obj.hide()
                obj.deleteLater()
        self.buttons = []

        # Проверка: остались ли еще вопросы?
        if self.current_index >= len(self.question_ids):
            self.end_of_the_test()
            return

        # 2. Получаем текущий вопрос
        current_id = self.question_ids[self.current_index]
        q_data = self.all_questions[str(current_id)]

        # 3. Отрисовка вопроса
        self.question.setText(q_data["text"].strip('"'))
        self.question.move(100, 50)
        self.question.show()

        # 4. Отрисовка кнопок ответов
        answers_list = q_data["answers"].split("|")
        width, height = 1000, 800
        work_height = height - 350
        one_step = work_height / (max(1, len(answers_list) - 1))

        for i in range(len(answers_list)):
            button = QtWidgets.QPushButton(answers_list[i], self)
            y_position = int(i * one_step) + 200
            button.setFixedWidth(500)
            button.setFixedHeight(80)
            button.move(width / 2 - 250, y_position)

            # Важно: передаем индекс i, чтобы потом проверить правильность
            button.clicked.connect(partial(self.check_answer, q_data, i))
            button.show()
            self.buttons.append(button)

        # 5. Прогресс-бар (PRbox)
        pr_text = f"Вопрос {self.current_index + 1} из {len(self.all_questions)}"
        pr_box = QtWidgets.QTextEdit(pr_text, self)
        pr_box.move(0, 750)
        pr_box.resize(500, 50)
        pr_box.setStyleSheet("background: transparent; border: none; color: white;")
        pr_box.setFont(QtGui.QFont("Sylfaen", 14))
        pr_box.setReadOnly(True)
        pr_box.show()
        self.buttons.append(pr_box)

    def check_answer(self, que, n):
        tr_an = que["true_answer"]
        if ( que["answers"].split("|") )[n] == tr_an:
            self.user_progress_right.append(self.question_ids[self.current_index])
        else:
            self.user_progress_wrong.append(self.question_ids[self.current_index])
        self.current_index += 1
        self.displayQA()
        print(self.user_progress_right)
        return

    def end_of_the_test(self):
        pr_text = f"Статистика: {( len(self.user_progress_right)/len(self.question_ids) ) * 100}% правильных ответов"
        pr_box = QtWidgets.QTextEdit(pr_text, self)
        pr_box.move(100, 250)
        pr_box.resize(1000, 50)
        pr_box.setStyleSheet("background: transparent; border: none; color: white;")
        pr_box.setFont(QtGui.QFont("Sylfaen", 24))
        pr_box.setReadOnly(True)
        pr_box.show()
        self.buttons.append(pr_box)
        recs = self.get_ai_recommendations()
        print(recs)

    def prepare_ai_prompt(self):
        report = "Проанализируй результаты теста и дай краткие рекомендации:\n"

        for q_id in self.question_ids:
            q_data = self.all_questions[q_id]
            status = "Правильно" if q_id in self.user_progress_right else "Неправильно"

            report += f"- Вопрос: {q_data['text']}\n"
            report += f"  Результат: {status}\n"

            return report

    def get_ai_recommendations(self):
        # 1. Формируем список вопросов и ответов для анализа
        test_summary = "Результаты теста:\n"
        for q_id in self.question_ids:
            q_data = self.all_questions[q_id]
            status = "Верно" if q_id in self.user_progress_right else "Ошибка"
            test_summary += f"- Вопрос: {q_data['text']}. Результат: {status}\n"

        # 2. Инициализируем клиента DeepSeek
        client = OpenAI(
            api_key="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",
            base_url="https://api.deepseek.com"
        )

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",  # Или deepseek-reasoner для более глубокой аналитики
                messages=[
                    {"role": "system",
                     "content": "Ты — ассистент-преподаватель. Проанализируй ошибки ученика и дай краткие рекомендации по темам."},
                    {"role": "user", "content": test_summary},
                ],
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Не удалось связаться с DeepSeek: {str(e)}"



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







if __name__ == "__main__":
            app = QtWidgets.QApplication([])

            widget = MyWidget()
            widget.resize(1000, 800)
            widget.show()

            sys.exit(app.exec())
