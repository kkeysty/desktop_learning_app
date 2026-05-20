import os
import sqlite3
from flask import Flask, jsonify, send_file

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Указываем на тот же самый файл project.db в папке server
DB_PATH = os.path.join(BASE_DIR, 'project.db')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Позволяет обращаться к полям по именам: row['name']
    return conn


# 1. ЭНДПОИНТ ДЛЯ ПОСТРОЕНИЯ ДЕРЕВА (Именно его запрашивает твой load_data)
@app.route('/get_structure', methods=['GET'])
def get_structure():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Шаг 1: Получаем все предметы
        cursor.execute("SELECT id, name FROM subjects")
        subjects = [dict(row) for row in cursor.fetchall()]

        for subject in subjects:
            # Шаг 2: Получаем разделы для текущего предмета
            cursor.execute("SELECT id, name FROM sections WHERE subject_id = ?", (subject['id'],))
            sections = [dict(row) for row in cursor.fetchall()]
            subject['sections'] = sections

            for section in sections:
                # Шаг 3: Получаем темы для каждого раздела
                cursor.execute("SELECT id, name FROM topics WHERE section_id = ?", (section['id'],))
                section['topics'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jsonify(subjects), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 2. ЭНДПОИНТ ДЛЯ ПОЛУЧЕНИЯ СПИСКА РЕСУРСОВ ТЕМЫ (Запрашивает start_download)
@app.route('/get_resources/<int:topic_id>', methods=['GET'])
def get_resources(topic_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Выбираем файлы, привязанные к конкретной теме
        cursor.execute("SELECT id, file_name FROM resources WHERE topic_id = ?", (topic_id,))
        resources = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jsonify(resources), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 3. ЭНДПОИНТ ДЛЯ СКАЧИВАНИЯ КОНКРЕТНОГО ФАЙЛА (Отдает .db или .pdf)
@app.route('/download/resource/<int:resource_id>', methods=['GET'])
def download_resource(resource_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT file_path, file_name FROM resources WHERE id = ?", (resource_id,))
        res = cursor.fetchone()
        conn.close()

        if not res:
            return jsonify({"error": "Ресурс не найден в базе данных"}), 404

        # Переводим сохраненный относительный путь в абсолютный
        file_path = os.path.abspath(res['file_path'])

        if os.path.exists(file_path):
            return send_file(file_path, download_name=res['file_name'], as_attachment=True)
        else:
            return jsonify({"error": f"Файл физически отсутствует на сервере по пути: {file_path}"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Запускаем сервер на локальном порту 5000
    app.run(host='127.0.0.1', port=5000, debug=True)