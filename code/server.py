from flask import Flask, send_file, request, jsonify
import os
import data_to_jsonFile
import sys

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
DOWNLOAD_FOLDER = 'files'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/downloads/<filename>')
def download_file(filename):
    safe_path = os.path.join(DOWNLOAD_FOLDER, os.path.basename(filename))
    if not os.path.exists(safe_path):
        return 'Файл не найден', 404
    return send_file(safe_path, as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'Нет файла', 400
    file = request.files['file']
    if file.filename == '':
        return 'Имя файла пустое', 400
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    return 'Файл загружен', 200


CURRENT_SCHEDULE = None

@app.route('/api/schedule')
def get_schedule():
    try:
        data = data_to_jsonFile.make_jsonFile()
        # Принудительная сериализация с заменой несериализуемых объектов на строки
        import json
        data = json.loads(json.dumps(data, default=str))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(data)


if __name__ == '__main__':
    # Если передан аргумент командной строки, используем его
    if len(sys.argv) > 1:
        host_ip = sys.argv[1]
    else:
        # Иначе читаем из переменной окружения или используем по умолчанию
        host_ip = os.environ.get('SERVER_HOST', '0.0.0.0')
    app.run(host=host_ip, port=5000)
