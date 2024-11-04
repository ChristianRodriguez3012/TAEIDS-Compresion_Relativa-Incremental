from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import wave
import contextlib
import subprocess

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'  # Carpeta de salida para archivos convertidos
ALLOWED_EXTENSIONS = {'mp3', 'wav'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Leer el sample rate y bitrate del archivo de audio
        original_samplerate = None
        original_bitrate = None
        
        if filename.endswith('.wav'):
            with contextlib.closing(wave.open(file_path, 'r')) as f:
                original_samplerate = f.getframerate()
                original_bitrate = f.getnchannels() * f.getsampwidth() * 8 * original_samplerate / 1000
        elif filename.endswith('.mp3'):
            # Para MP3, se puede usar ffmpeg para obtener el sample rate y bitrate
            command = f"ffmpeg -i {file_path} 2>&1 | grep 'bitrate' | awk '{{print $6}}'"
            original_bitrate = subprocess.check_output(command, shell=True).decode().strip()
            command = f"ffmpeg -i {file_path} 2>&1 | grep 'Duration' | awk '{{print $3}}'"
            duration = subprocess.check_output(command, shell=True).decode().strip()
            # Aquí puedes establecer un valor predeterminado para el sample rate
            original_samplerate = 44100  # Reemplazar con un comando adecuado si deseas obtener el valor real

        return jsonify({'original_bitrate': original_bitrate, 'original_samplerate': original_samplerate})
    return jsonify({'error': 'Invalid file type'})

@app.route('/convert', methods=['POST'])
def convert_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        bitrate = request.form['bitrate']
        samplerate = request.form['samplerate']
        
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)  # Crea la carpeta de salida si no existe
        output_filename = f"{os.path.splitext(filename)[0]}({bitrate}-{samplerate}).mp3"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)  # Cambia la ruta de salida

        # Comando de conversión utilizando ffmpeg
        command = f"ffmpeg -i {input_path} -b:a {bitrate}k -ar {samplerate} {output_path}"
        try:
            # Captura de errores
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                return jsonify({'error': 'Error al convertir el archivo: ' + result.stderr})

            if os.path.exists(output_path):
                return jsonify({'message': 'Archivo convertido y guardado en: ' + output_path})  # Confirmación
            else:
                return jsonify({'error': 'Error al crear el archivo convertido.'})
        except Exception as e:
            return jsonify({'error': 'Error al convertir el archivo: ' + str(e)})

    return jsonify({'error': 'Invalid file type'})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    app.run(debug=True)
