from flask import Flask, send_file, request, jsonify
import os
import data_to_jsonFile

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
    global CURRENT_SCHEDULE
    data = data_to_jsonFile.make_jsonFile()
    print("made from json: ", data)
    return jsonify(data)  # Flask автоматически сериализует словарь в JSON

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)