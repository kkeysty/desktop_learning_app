import sqlite3
import os

def generate_topic_files():
    main_db = 'project.db'
    storage_dir = 'materials'

    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)

    if not os.path.exists(main_db):
        print(f"Ошибка: Файл {main_db} не найден. Сначала запустите скрипт инициализации!")
        return

    # Подключаемся к основной базе, чтобы узнать, какие темы у нас есть
    conn = sqlite3.connect(main_db)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM topics")
    topics = cursor.fetchall()
    conn.close()

    for t_id, t_name in topics:
        file_name = f"topic_{t_id}.db"
        file_path = os.path.join(storage_dir, file_name)

        # Создаем новую базу данных для конкретной темы
        topic_conn = sqlite3.connect(file_path)
        topic_cursor = topic_conn.cursor()

        # Создаем таблицу внутри этого файла
        topic_cursor.execute('''
            CREATE TABLE IF NOT EXISTS local_questions (
                id INTEGER PRIMARY KEY,
                text TEXT,
                options TEXT,
                answer TEXT
            )
        ''')

        # Добавим тестовую запись, чтобы файл не был пустым
        topic_cursor.execute('''
            INSERT INTO local_questions (text, options, answer)
            VALUES (?, ?, ?)
        ''', (f"Тестовый вопрос по теме {t_name}", "Вариант А|Вариант Б", "Вариант А"))

        topic_conn.commit()
        topic_conn.close()
        print(f"Создан файл: {file_path}")


def add_resource(parent_id, parent_type, name, path, size, file_hash):
    conn = sqlite3.connect("project.db")
    cursor = conn.cursor()

    query = '''
        INSERT INTO resources (parent_id, parent_type, file_name, file_path, file_size, checksum)
        VALUES (?, ?, ?, ?, ?, ?)
    '''
    cursor.execute(query, (parent_id, parent_type, name, path, size, file_hash))

    conn.commit()
    conn.close()


# Пример использования:
# Предмет (subject) с ID 1, Раздел (section) с ID 5, Тема (topic) с ID 42
add_resource(42, 'topic', 'Кинематика_тесты.db', '/storage/files/t42_v1.db', 8192, 'd41d8cd98f00b204e9800998ecf8427e')

if __name__ == "__main__":
    generate_topic_files()