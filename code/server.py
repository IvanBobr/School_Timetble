from flask import Flask, send_file, request, jsonify
import os
import data_to_jsonFile
import sys
from werkzeug.utils import secure_filename
import json

UPLOAD_TOKEN = "X_1YCfKVPuZc_UqvBA39_e1kXZmmlfnQ3nOPNLVGfs3453-0dfvVSFsLMUWcBKESSK6b-12QlcPV1LJb4DA4J62412GGQMcJYUcJ84909526WgVSFVG26s635464vsd"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, 'downloads')
os.makedirs(DATA_FOLDER, exist_ok=True)

app = Flask(__name__)

def _check_auth():
    token = request.headers.get('X-Auth-Token') or request.form.get('token')
    return token == UPLOAD_TOKEN

@app.route('/downloads/<filename>')
def download_file(filename):
    safe_path = os.path.join(DATA_FOLDER, os.path.basename(filename))
    if not os.path.exists(safe_path):
        return 'Файл не найден', 404
    return send_file(safe_path, as_attachment=True)

@app.route('/upload/schedule', methods=['POST'])
def upload_schedule():
    if not _check_auth():
        return jsonify({"error": "Forbidden"}), 403
    if 'file' not in request.files:
        return jsonify({"error": "Нет файла"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "Имя файла пустое"}), 400

    original_lower = file.filename.lower()
    if not (original_lower.endswith('.xls') or original_lower.endswith('.xlsx')):
        return jsonify({"error": "Нужен файл .xls или .xlsx"}), 400
    safe_name = secure_filename(file.filename) or 'upload.xls'

    target = os.path.join(DATA_FOLDER, 'rasp.xls')
    file.save(target)
    print(f"[upload/schedule] Saved {safe_name} -> rasp.xls")
    return jsonify({"status": "ok", "saved_as": "rasp.xls"}), 200


@app.route('/upload/changes', methods=['POST'])
def upload_changes():
    if not _check_auth():
        return jsonify({"error": "Forbidden"}), 403
    if 'file' not in request.files:
        return jsonify({"error": "Нет файла"}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({"error": "Имя файла пустое"}), 400

    # Проверяем расширение по оригинальному имени (до secure_filename)
    original_lower = file.filename.lower()

    docx_target = os.path.join(DATA_FOLDER, 'changes.docx')
    pdf_target = os.path.join(DATA_FOLDER, 'changes.pdf')

    if original_lower.endswith('.docx'):
        if os.path.exists(pdf_target):
            os.remove(pdf_target)
        file.save(docx_target)
        saved = 'changes.docx'
    elif original_lower.endswith('.pdf'):
        if os.path.exists(docx_target):
            os.remove(docx_target)
        file.save(pdf_target)
        saved = 'changes.pdf'
    else:
        return jsonify({"error": "Поддерживаются только .docx и .pdf"}), 400

    print(f"[upload/changes] Saved '{file.filename}' -> {saved}")
    return jsonify({"status": "ok", "saved_as": saved}), 200


_cached_json = None
_cached_mtime = None


def _files_mtime():
    """Возвращает максимальное время изменения файлов расписания. 0, если файлов нет."""
    mtimes = []
    for fname in ('rasp.xls', 'changes.docx', 'changes.pdf'):
        path = os.path.join(DATA_FOLDER, fname)
        if os.path.exists(path):
            mtimes.append(os.path.getmtime(path))
    return max(mtimes) if mtimes else 0


@app.route('/api/schedule')
def get_schedule():
    global _cached_json, _cached_mtime
    try:
        current_mtime = _files_mtime()
        if _cached_json is None or current_mtime != _cached_mtime:
            data = data_to_jsonFile.make_jsonFile()
            data = json.loads(json.dumps(data, default=str))
            _cached_json = data
            _cached_mtime = current_mtime
            print(f"[schedule] Rebuilt cache (mtime={current_mtime})")
        else:
            print("[schedule] Serving from cache")
        return jsonify(_cached_json)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Если передан аргумент командной строки, используем его
    if len(sys.argv) > 1:
        host_ip = sys.argv[1]
    else:
        # Иначе читаем из переменной окружения или используем по умолчанию
        host_ip = os.environ.get('SERVER_HOST', '0.0.0.0')
    app.run(host=host_ip, port=5000)
