import sqlite3

# 1. Функция помощник
def get_or_create(cursor, table, name, parent_col=None, parent_id=None):
    if parent_col:
        cursor.execute(f"SELECT id FROM {table} WHERE name = ? AND {parent_col} = ?", (name, parent_id))
    else:
        cursor.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))

    result = cursor.fetchone()
    if result:
        return result[0]

    if parent_col:
        cursor.execute(f"INSERT INTO {table} (name, {parent_col}) VALUES (?, ?)", (name, parent_id))
    else:
        cursor.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    return cursor.lastrowid

# 2. Инициализация
conn = sqlite3.connect('project.db')
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

# 3. Создание таблиц
cursor.executescript('''
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        answers_json TEXT NOT NULL,
        true_answer TEXT NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
    );
''')

# 4. Данные для импорта
data_to_import = [
    ("Высшая математика", "Линейная алгебра", "Матрицы", "Как называется квадратная матрица, у которой все элементы вне главной диагонали равны нулю?", "Нулевая|Диагональная|Единичная|Транспонированная", "Диагональная"),
    ("Высшая математика", "Линейная алгебра", "Определители", "Чему равен определитель матрицы, если поменять местами две её строки?", "Не изменится|Станет равен 0|Изменит знак на противоположный|Увеличится вдвое", "Изменит знак на противоположный"),
    ("Высшая математика", "Математический анализ", "Дифференциальное исчисление", "Чему равна производная функции ln(x)?", "e^x|1/x|1/ln(x)|x^2", "1/x"),
    ("Высшая математика", "Математический анализ", "Интегральное исчисление", "Чему равен неопределенный интеграл от функции 1/x?", "ln|x| + C|x^2 + C|e^x + C|-1/x^2 + C", "ln|x| + C"),
    ("Высшая математика", "Дифференциальные уравнения", "Обычные ДУ", "Как называется уравнение вида M(x,y)dx + N(x,y)dy = 0, если его левая часть является полным дифференциалом?", "Линейное|Бернулли|В полных дифференциалах|Однородное", "В полных дифференциалах"),
    ("Высшая математика", "Теория вероятностей", "Случайные события", "Чему равна вероятность достоверного события?", "0|0.5|1|Бесконечность", "1")
]

# 5. Выполнение импорта
for item in data_to_import:
    subj, sect, topic, q_text, q_ans, q_true = item

    s_id = get_or_create(cursor, "subjects", subj)
    sec_id = get_or_create(cursor, "sections", sect, "subject_id", s_id)
    t_id = get_or_create(cursor, "topics", topic, "section_id", sec_id)

    cursor.execute("""
        INSERT INTO questions (topic_id, question_text, answers_json, true_answer)
        VALUES (?, ?, ?, ?)
    """, (t_id, q_text, q_ans, q_true))

conn.commit()
conn.close()
print("База данных успешно инициализирована.")

import sqlite3
import os
import re

# Название итоговой (локальной) базы данных
DEST_DB = 'project.db'


def migrate_data():
    # 1. Подключаемся к основной базе
    conn_dest = sqlite3.connect(DEST_DB)
    cursor_dest = conn_dest.cursor()

    # Получаем список всех файлов topic_*.db
    files = [f for f in os.listdir('./materials') if f.startswith('topic_') and f.endswith('.db')]

    for file_name in files:
        print(f"Обработка файла: {file_name}...")

        # Извлекаем ID топика из названия файла (например, из 'topic_1.db' получим 1)
        topic_id_match = re.search(r'\d+', file_name)
        if not topic_id_match:
            continue
        topic_id = int(topic_id_match.group())

        # 2. Подключаемся к файлу топика
        conn_src = sqlite3.connect(file_name)
        cursor_src = conn_src.cursor()

        try:
            # Читаем данные из локальной таблицы
            cursor_src.execute("SELECT text, options, answer FROM local_questions")
            rows = cursor_src.fetchall()

            # 3. Записываем данные в основную таблицу questions
            for row in rows:
                cursor_dest.execute("""
                    INSERT INTO questions (topic_id, question_text, answers_json, true_answer)
                    VALUES (?, ?, ?, ?)
                """, (topic_id, row[0], row[1], row[2]))

            conn_dest.commit()
            print(f"Добавлено записей: {len(rows)}")

        except sqlite3.Error as e:
            print(f"Ошибка при обработке {file_name}: {e}")
        finally:
            conn_src.close()

    conn_dest.close()
    print("Миграция завершена!")


import sqlite3

def create_resources_db(db_name="project.db"):
    # Подключаемся к базе (если файла нет, он будет создан)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Создаем таблицу ресурсов
    # parent_type: указывает на уровень дерева ('subject', 'section' или 'topic')
    # parent_id: ID соответствующей записи из таблиц subjects, sections или topics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER NOT NULL,
            parent_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            checksum TEXT,
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print(f"База данных {db_name} и таблица 'resources' успешно созданы.")


def fill_resources_table():
    conn = sqlite3.connect('project.db')
    cursor = conn.cursor()

    # Путь, где реально лежат ваши .db файлы на сервере
    materials_dir = './materials'

    if not os.path.exists(materials_dir):
        print(f"Папка {materials_dir} не найдена!")
        return

    files = [f for f in os.listdir(materials_dir) if f.endswith('.db')]

    for file_name in files:
        # 1. Вытаскиваем ID из имени файла (например, 3 из topic_3.db)
        match = re.search(r'\d+', file_name)
        if match:
            t_id = int(match.group())
            full_path = os.path.abspath(os.path.join(materials_dir, file_name))
            size = os.path.getsize(full_path)

            # 2. Записываем информацию в таблицу resources
            # Это именно то, что потом будет читать сервер Flask!
            cursor.execute("""
                INSERT INTO resources (parent_id, parent_type, file_name, file_path, file_size)
                VALUES (?, 'topic', ?, ?, ?)
            """, (t_id, file_name, full_path, size))

    conn.commit()
    conn.close()
    print("Таблица resources успешно заполнена информацией о файлах.")


if __name__ == "__main__":
    # 1. Создаем структуру (subjects, sections, topics, questions)
    # Здесь должны появиться те ID, которые есть в названиях ваших файлов!

    # 2. Создаем таблицу ресурсов
    create_resources_db()

    # 3. ЗАПОЛНЯЕМ таблицу ресурсов данными о файлах
    fill_resources_table()

    # 4. Если нужно перелить вопросы из файлов в общую базу:
    # migrate_data()