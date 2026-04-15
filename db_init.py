import sqlite3


def get_or_create(cursor, table, name, parent_col=None, parent_id=None):
    # Ищем, есть ли уже такая запись
    if parent_col:
        cursor.execute(f"SELECT id FROM {table} WHERE name = ? AND {parent_col} = ?", (name, parent_id))
    else:
        cursor.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))

    result = cursor.fetchone()
    if result:
        return result[0]

    # Если нет — создаем
    if parent_col:
        cursor.execute(f"INSERT INTO {table} (name, {parent_col}) VALUES (?, ?)", (name, parent_id))
    else:
        cursor.execute(f"INSERT INTO {table} (name) VALUES (?)", (name,))
    return cursor.lastrowid

conn = sqlite3.connect('project.db')
cursor = conn.cursor()

# Включаем поддержку внешних ключей
cursor.execute("PRAGMA foreign_keys = ON")

# Создаем таблицы
cursor.executescript('''
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
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
    answers_json TEXT NOT NULL, -- Здесь храним варианты ответов (например, через separator или JSON)
    true_answer TEXT NOT NULL,
    FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
);
''')
conn.commit()

conn = sqlite3.connect('project.db')
cursor = conn.cursor()

# 1. Добавляем Предмет
cursor.execute("INSERT INTO subjects (name) VALUES (?)", ("Высшая математика",))
subject_id = cursor.lastrowid # Получаем ID только что созданного предмета

# 2. Добавляем Раздел
cursor.execute("INSERT INTO sections (subject_id, name) VALUES (?, ?)",
               (subject_id, "Математический анализ"))
section_id = cursor.lastrowid

# 3. Добавляем Тему
cursor.execute("INSERT INTO topics (section_id, name) VALUES (?, ?)",
               (section_id, "Пределы и производные"))
topic_id = cursor.lastrowid

# 4. Добавляем Вопрос
# Для удобства варианты ответов записываем через разделитель |
question_data = (
    topic_id,
    "Чему равен предел sin(x)/x при x стремящемся к 0?",
    "0|1|Бесконечность|e", # Варианты ответов
    "1" # Правильный ответ
)

cursor.execute("""
    INSERT INTO questions (topic_id, question_text, answers_json, true_answer) 
    VALUES (?, ?, ?, ?)
""", question_data)

# Структура: (Предмет, Раздел, Тема, Текст вопроса, Варианты, Ответ)
data_to_import = [
    # Раздел: Линейная алгебра
    (
        "Высшая математика",
        "Линейная алгебра",
        "Матрицы",
        "Как называется квадратная матрица, у которой все элементы вне главной диагонали равны нулю?",
        "Нулевая|Диагональная|Единичная|Транспонированная",
        "Диагональная"
    ),
    (
        "Высшая математика",
        "Линейная алгебра",
        "Определители",
        "Чему равен определитель матрицы, если поменять местами две её строки?",
        "Не изменится|Станет равен 0|Изменит знак на противоположный|Увеличится вдвое",
        "Изменит знак на противоположный"
    ),

    # Раздел: Математический анализ
    (
        "Высшая математика",
        "Математический анализ",
        "Дифференциальное исчисление",
        "Чему равна производная функции ln(x)?",
        "e^x|1/x|1/ln(x)|x^2",
        "1/x"
    ),
    (
        "Высшая математика",
        "Математический анализ",
        "Интегральное исчисление",
        "Чему равен неопределенный интеграл от функции 1/x?",
        "ln|x| + C|x^2 + C|e^x + C|-1/x^2 + C",
        "ln|x| + C"
    ),

    # Раздел: Дифференциальные уравнения
    (
        "Высшая математика",
        "Дифференциальные уравнения",
        "Обычные ДУ",
        "Как называется уравнение вида M(x,y)dx + N(x,y)dy = 0, если его левая часть является полным дифференциалом?",
        "Линейное|Бернулли|В полных дифференциалах|Однородное",
        "В полных дифференциалах"
    ),

    # Раздел: Теория вероятностей
    (
        "Высшая математика",
        "Теория вероятностей",
        "Случайные события",
        "Чему равна вероятность достоверного события?",
        "0|0.5|1|Бесконечность",
        "1"
    )
]
for item in data_to_import:
    subj, sect, topic, q_text, q_ans, q_true = item

    # Сначала получаем ID (используя функцию get_or_create из предыдущего ответа)
    s_id = get_or_create(cursor, "subjects", subj)
    sec_id = get_or_create(cursor, "sections", sect, "subject_id", s_id)
    t_id = get_or_create(cursor, "topics", topic, "section_id", sec_id)

    # Формируем кортеж для вставки в таблицу questions
    question_data = (
        t_id,  # topic_id
        q_text,  # текст вопроса
        q_ans,  # варианты через |
        q_true  # правильный ответ
    )

    cursor.execute("""
        INSERT INTO questions (topic_id, question_text, answers_json, true_answer)
        VALUES (?, ?, ?, ?)
    """, question_data)

conn.commit()

conn.commit()
conn.close()