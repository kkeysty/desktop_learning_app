from flask import Flask, jsonify, send_file
import sqlite3
import os

app = Flask(__name__)

# Укажи путь к своему файлу базы данных
DB_PATH = 'project.db'

# Определяем путь к папке materials относительно этого файла
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, 'materials')

from flask import send_from_directory


@app.route('/download/<int:topic_id>')
def download_file(topic_id):
    conn = sqlite3.connect("project.db")
    cursor = conn.cursor()

    # Ищем файл в новой таблице resources
    cursor.execute("SELECT file_path, file_name FROM resources WHERE parent_id = ? AND parent_type = 'topic'",
                   (topic_id,))
    res = cursor.fetchone()
    conn.close()

    if res:
        server_path, original_name = res
        # send_file отправит содержимое, а download_name скажет клиенту, как файл назывался в БД
        return send_file(server_path, download_name=original_name, as_attachment=True)
    else:
        return "File not found", 404


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Чтобы обращаться к полям по именам
    return conn

@app.route('/get_structure', methods=['GET'])
def get_structure():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Получаем все предметы
    cursor.execute("SELECT id, name FROM subjects")
    subjects = [dict(row) for row in cursor.fetchall()]

    for subject in subjects:
        # 2. Для каждого предмета ищем его секции
        cursor.execute("SELECT id, name FROM sections WHERE subject_id = ?", (subject['id'],))
        sections = [dict(row) for row in cursor.fetchall()]
        subject['sections'] = sections

        for section in sections:
            # 3. Для каждой секции ищем её темы
            cursor.execute("SELECT id, name FROM topics WHERE section_id = ?", (section['id'],))
            topics = [dict(row) for row in cursor.fetchall()]
            section['topics'] = topics

    conn.close()
    return jsonify(subjects)

@app.route('/download/<int:topic_id>', methods=['GET'])
def download_material(topic_id):
    # Пример эндпоинта для скачивания (если файлы лежат в папке materials)
    # Название файла можно также хранить в БД в таблице topics
    file_path = f"materials/topic_{topic_id}.pdf"
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)

    return jsonify({"error": "File not found"}), 404

def start_download(self):
    # 1. Собираем ID всех отмеченных тем в дереве
    selected_ids = []
    it = QTreeWidgetItemIterator(self.tree, QTreeWidgetItemIterator.Checked)
    while it.value():
        data = it.value().data(0, Qt.UserRole)
        # Проверяем, что это именно тема, а не предмет или секция
        if data and data.get("type") == "topic":
            selected_ids.append(data["id"])
        it += 1

    if not selected_ids:
        print("Вы не выбрали ни одной темы для скачивания.")
        return

    # 2. Определяем путь для сохранения
    save_path = "downloads"
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # 3. Проходим циклом по всем выбранным ID и скачиваем их
    for topic_id in selected_ids:
        try:
            url = f"http://127.0.0.1:5000/download/{topic_id}"
            # Делаем запрос к серверу
            response = requests.get(url, stream=True)

            # --- ВОТ СЮДА ВСТАВЛЯЕТСЯ ВАШ КОД ---
            if response.status_code == 200:
                # Сохраняем как .db, чтобы файл оставался валидной базой данных
                filename = f"topic_{topic_id}.db"
                full_file_path = os.path.join(save_path, filename)

                with open(full_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Файл {filename} успешно скачан в папку {save_path}")
            else:
                print(f"Ошибка сервера (ID {topic_id}): статус {response.status_code}")
            # ------------------------------------

        except requests.exceptions.ConnectionError:
            print("Ошибка: Сервер не запущен! Запустите server.py")
            break # Прерываем цикл, если сервер недоступен
        except Exception as e:
            print(f"Произошла ошибка при скачивании темы {topic_id}: {e}")

    # Декоратор @app.route говорит серверу:
    # "Если пришел запрос, начинающийся на /download/, выполни эту функцию"
    @app.route('/download/<int:topic_id>')
    def give_file_to_client(topic_id):
        # 1. Идем в таблицу resources и ищем путь к файлу по его ID
        # server_path может быть вообще в другом месте, например: "C:/data/hidden_storage/f_934.db"
        file_info = db.execute("SELECT file_path, file_name FROM resources WHERE parent_id=?", (topic_id,)).fetchone()

        if file_info:
            path, name = file_info
            # 2. Отправляем физический файл, маскируя его под красивым именем
            return send_file(path, download_name=name, as_attachment=True)
        return "Файл не найден", 404

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)