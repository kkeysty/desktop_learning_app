import os
import sqlite3
import re

# Настраиваем точные абсолютные пути относительно этого файла
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'server', 'project.db')
MATERIALS_DIR = os.path.join(BASE_DIR, 'server', 'materials')


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # Полностью сбрасываем старые таблицы для чистого перезапуска
    cursor.execute("DROP TABLE IF EXISTS resources")
    cursor.execute("DROP TABLE IF EXISTS questions")
    cursor.execute("DROP TABLE IF EXISTS topics")
    cursor.execute("DROP TABLE IF EXISTS sections")
    cursor.execute("DROP TABLE IF EXISTS subjects")

    cursor.executescript('''
        CREATE TABLE subjects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE sections (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
        );
        CREATE TABLE topics (
            id INTEGER PRIMARY KEY,
            section_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE CASCADE
        );
        CREATE TABLE questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            true_answer TEXT NOT NULL,
            FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
        );
        CREATE TABLE resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
        );
    ''')
    conn.commit()
    conn.close()
    print("Таблицы базы данных успешно пересозданы.")


def insert_initial_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ВЫСТАВЛЯЕМ ID СТРОГО В СООТВЕТСТВИИ С ВАШИМИ НАЗВАНИЯМИ ПАПОК И ФАЙЛОВ

    # 1. Алгоритмы и структуры данных (subject_id_1 -> section_id_1 -> topic_1, topic_2)
    cursor.execute("INSERT INTO subjects (id, name) VALUES (1, 'Алгоритмы и структуры данных')")
    cursor.execute("INSERT INTO sections (id, subject_id, name) VALUES (1, 1, 'Сортировки')")
    cursor.execute("INSERT INTO topics (id, section_id, name) VALUES (1, 1, 'Быстрая сортировка')")
    cursor.execute("INSERT INTO topics (id, section_id, name) VALUES (2, 1, 'Сортировка слиянием')")

    # Графы (для примера, если у вас будут папки под них)
    cursor.execute("INSERT INTO sections (id, subject_id, name) VALUES (2, 1, 'Графы')")
    cursor.execute("INSERT INTO topics (id, section_id, name) VALUES (4, 2, 'Обход в ширину')")

    # 2. Дискретная математика
    cursor.execute("INSERT INTO subjects (id, name) VALUES (2, 'Дискретная математика')")
    cursor.execute("INSERT INTO sections (id, subject_id, name) VALUES (3, 2, 'Логика')")
    cursor.execute("INSERT INTO topics (id, section_id, name) VALUES (3, 3, 'Булевы функции')")

    # 3. Безопасность компьютерных систем (subject_id_3 -> section_id_4 -> topic_5)
    cursor.execute("INSERT INTO subjects (id, name) VALUES (3, 'Безопасность компьютерных систем')")
    cursor.execute("INSERT INTO sections (id, subject_id, name) VALUES (4, 3, 'Криптография')")
    cursor.execute("INSERT INTO topics (id, section_id, name) VALUES (5, 4, 'Криптография')")

    conn.commit()
    conn.close()
    print("Структура предметов и тем с правильными ID успешно записана.")


def process_and_register_files():
    if not os.path.exists(MATERIALS_DIR):
        print(f"Папка {MATERIALS_DIR} не найдена!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Рекурсивный обход папки server/materials/
    for root, dirs, files in os.walk(MATERIALS_DIR):
        for file_name in files:
            full_path = os.path.join(root, file_name)

            # Вычисляем путь относительно папки server/, чтобы Flask мог его прочитать
            rel_path = os.path.relpath(full_path, start=os.path.dirname(DB_PATH))
            size = os.path.getsize(full_path)
            topic_id = None

            # Шаг 1: Если это файл вопросов (topic_X.db), вытаскиваем ID напрямую из имени
            if file_name.startswith('topic_') and file_name.endswith('.db'):
                match = re.search(r'\d+', file_name)
                if match:
                    topic_id = int(match.group())

            # Шаг 2: Если это теория (.pdf), связываем её по названию темы из нашей БД
            elif file_name.endswith('.pdf'):
                clean_name = os.path.splitext(file_name)[0]
                cursor.execute("SELECT id FROM topics WHERE name LIKE ?", (f"%{clean_name}%",))
                res = cursor.fetchone()
                if res:
                    topic_id = res[0]

            # Шаг 3: Записываем в таблицу ресурсов, если для файла подтвержден topic_id
            if topic_id:
                # Проверяем, существует ли такой topic_id в нашей таблице topics
                cursor.execute("SELECT id FROM topics WHERE id = ?", (topic_id,))
                if cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO resources (topic_id, file_name, file_path, file_size)
                        VALUES (?, ?, ?, ?)
                    """, (topic_id, file_name, rel_path, size))
                    print(f"[Успешно связано] Тема ID {topic_id} -> файл {file_name}")
                else:
                    print(f"[Пропущено] Для файла {file_name} определен ID {topic_id}, но его нет в таблице topics!")

    conn.commit()
    conn.close()
    print("Регистрация всех файлов завершена.")


if __name__ == "__main__":
    print("--- СТАРТ ПЕРЕСОЗДАНИЯ СИНХРОННОЙ БАЗЫ ---")
    init_database()
    insert_initial_data()
    process_and_register_files()
    print("--- ГОТОВО ---")