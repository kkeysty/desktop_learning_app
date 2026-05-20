import sqlite3
import os


def populate_with_id_folders():
    main_db = 'project.db'
    storage_dir = 'materials'

    # Данные для добавления (те же предметы, что ты просил)
    data = [
        {
            "subject": "Алгоритмы и структуры данных",
            "sections": [
                {
                    "name": "Сортировки",
                    "topics": [
                        {
                            "name": "Быстрая сортировка",
                            "questions": [
                                ("Сложность QuickSort в среднем?", "O(n log n)|O(n^2)|O(n)|O(log n)", "O(n log n)"),
                                ("Что такое опорный элемент?", "Элемент для разделения|Конец массива|Минимум|Максимум",
                                 "Элемент для разделения"),
                                ("Является ли QuickSort стабильной?",
                                 "Нет|Да|Зависит от реализации|Только для массивов", "Нет")
                            ]
                        },
                        {
                            "name": "Сортировка слиянием",
                            "questions": [
                                ("Принцип Merge Sort?", "Разделяй и властвуй|Жадный выбор|Перебор|Случайный поиск",
                                 "Разделяй и властвуй"),
                                ("Сложность в худшем случае?", "O(n log n)|O(n^2)|O(n)|O(1)", "O(n log n)"),
                                ("Нужна ли доп. память?", "Да|Нет|Только для строк|Нет, если массив мал", "Да")
                            ]
                        }
                    ]
                },
                {
                    "name": "Графы",
                    "topics": [
                        {
                            "name": "Обход в ширину (BFS)",
                            "questions": [
                                ("Структура данных для BFS?", "Очередь|Стек|Дерево|Словарь", "Очередь"),
                                ("Поиск кратчайшего пути?",
                                 "Да (для невзвешенных)|Нет|Только для циклов|Только в деревьях",
                                 "Да (для невзвешенных)"),
                                ("Сложность BFS?", "O(V + E)|O(V*E)|O(V^2)|O(1)", "O(V + E)")
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "subject": "Дискретная математика",
            "sections": [
                {
                    "name": "Логика",
                    "topics": [
                        {
                            "name": "Булевы функции",
                            "questions": [
                                ("Что такое конъюнкция?", "Логическое И|Логическое ИЛИ|Отрицание|Исключающее ИЛИ",
                                 "Логическое И"),
                                ("Результат X AND (NOT X)?", "0|1|X|NOT X", "0"),
                                ("Функция вернет 1 только если аргументы разные?", "XOR|AND|OR|IF", "XOR")
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "subject": "Безопасность компьютерных систем",
            "sections": [
                {
                    "name": "Криптография",
                    "topics": [
                        {
                            "name": "Хеширование",
                            "questions": [
                                ("Хеширование обратимо?", "Нет|Да|Только SHA-1|Только MD5", "Нет"),
                                ("Что такое коллизия?", "Один хеш для разных данных|Вирус|Ошибка сети|Потеря ключа",
                                 "Один хеш для разных данных"),
                                ("Пример надежного алгоритма?", "SHA-256|MD4|ROT13|Base64", "SHA-256")
                            ]
                        }
                    ]
                }
            ]
        }
    ]

    conn = sqlite3.connect(main_db)
    cursor = conn.cursor()

    for s_item in data:
        # 1. Добавляем Предмет в БД
        cursor.execute("INSERT INTO subjects (name) VALUES (?)", (s_item["subject"],))
        subject_id = cursor.lastrowid

        # Создаем папку предмета по ID
        subject_folder = os.path.join(storage_dir, f"subject_id_{subject_id}")

        for sec_item in s_item["sections"]:
            # 2. Добавляем Раздел в БД
            cursor.execute("INSERT INTO sections (subject_id, name) VALUES (?, ?)", (subject_id, sec_item["name"]))
            section_id = cursor.lastrowid

            # Создаем папку раздела внутри предмета по ID
            section_folder = os.path.join(subject_folder, f"section_id_{section_id}")
            if not os.path.exists(section_folder):
                os.makedirs(section_folder)

            for top_item in sec_item["topics"]:
                # 3. Добавляем Тему в БД
                cursor.execute("INSERT INTO topics (section_id, name) VALUES (?, ?)", (section_id, top_item["name"]))
                topic_id = cursor.lastrowid

                # 4. Вопросы в основную базу
                for q_text, q_opts, q_ans in top_item["questions"]:
                    cursor.execute(
                        "INSERT INTO questions (topic_id, question_text, answers_json, true_answer) VALUES (?, ?, ?, ?)",
                        (topic_id, q_text, q_opts, q_ans))

                # 5. Создаем файл темы .db в итоговой папке
                file_name = f"topic_{topic_id}.db"
                file_path = os.path.join(section_folder, file_name)

                t_conn = sqlite3.connect(file_path)
                t_cur = t_conn.cursor()
                t_cur.execute(
                    'CREATE TABLE IF NOT EXISTS local_questions (id INTEGER PRIMARY KEY, text TEXT, options TEXT, answer TEXT)')

                for q_text, q_opts, q_ans in top_item["questions"]:
                    t_cur.execute("INSERT INTO local_questions (text, options, answer) VALUES (?, ?, ?)",
                                  (q_text, q_opts, q_ans))

                t_conn.commit()
                t_conn.close()
                print(f"Файл создан: {file_path}")

    conn.commit()
    conn.close()
    print("\n--- Готово! Все папки и файлы созданы на основе ID. ---")

def cleanup_duplicates():
        conn = sqlite3.connect('project.db')
        cursor = conn.cursor()
        # Удаляем всё, чтобы начать с чистого листа
        cursor.execute("DELETE FROM questions")
        cursor.execute("DELETE FROM topics")
        cursor.execute("DELETE FROM sections")
        cursor.execute("DELETE FROM subjects")
        cursor.execute("DELETE FROM sqlite_sequence")  # Сброс счетчиков ID
        conn.commit()
        conn.close()
        # Также удали папку materials вручную
        print("База очищена.")


if __name__ == "__main__":
    cleanup_duplicates()
    populate_with_id_folders()
