import os
import sqlite3
from flask import Flask, jsonify, send_file

app = Flask(__name__)

DB_PATH = 'project.db'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, 'materials')


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
        cursor.execute(
            "SELECT id, name FROM sections WHERE subject_id = ?",
            (subject['id'],),
        )
        sections = [dict(row) for row in cursor.fetchall()]
        subject['sections'] = sections

        for section in sections:
            # 3. Для каждой секции ищем её темы
            cursor.execute(
                "SELECT id, name FROM topics WHERE section_id = ?",
                (section['id'],),
            )
            topics = [dict(row) for row in cursor.fetchall()]
            section['topics'] = topics

    conn.close()
    return jsonify(subjects)


@app.route('/download/<int:topic_id>', methods=['GET'])
def download_file(topic_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Сначала всё же проверяем таблицу resources (на всякий случай)
    cursor.execute("SELECT file_path, file_name FROM resources WHERE parent_id = ? AND parent_type = 'topic'",
                   (topic_id,))
    res = cursor.fetchone()
    conn.close()

    if res:
        server_path, original_name = res
        if not os.path.isabs(server_path):
            server_path = os.path.join(BASE_DIR, server_path)
        if os.path.exists(server_path):
            return send_file(server_path, download_name=original_name, as_attachment=True)

    # --- ЕСЛИ В БД НЕТ ЗАПИСИ: Ищем файл topic_X.db рекурсивно во всех подпапках ---
    target_filename = f"topic_{topic_id}.db"

    # os.walk полностью обходит materials, включая subject_id_X и section_id_Y
    for root, dirs, files in os.walk(STORAGE_DIR):
        if target_filename in files:
            full_path = os.path.join(root, target_filename)
            # Отправляем найденный файл .db
            return send_file(full_path, download_name=target_filename, as_attachment=True)

    # Если нигде не нашли
    return jsonify({"error": f"Файл topic_{topic_id}.db не найден ни в одной из подпапок materials"}), 404

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)