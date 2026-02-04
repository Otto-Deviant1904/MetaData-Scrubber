from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import io
import os
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Limit upload size (important)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25 MB

# Enable CORS properly
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True
)

# Thread pool (not used yet, but fine to keep)
executor = ThreadPoolExecutor(max_workers=4)

# ---- CORS HEADERS FOR ALL RESPONSES ----
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

# ---- IMAGE PROCESSING ----
def process_image_fast(file_stream, original_format):
    img = Image.open(file_stream)
    width, height = img.size

    # Resize very large images
    MAX_DIMENSION = 8192
    if max(width, height) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(width, height)
        img = img.resize(
            (int(width * ratio), int(height * ratio)),
            Image.Resampling.LANCZOS
        )

    # Handle transparency
    if img.mode in ('RGBA', 'LA', 'P'):
        if original_format == 'JPEG':
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert('RGBA')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img_io = io.BytesIO()

    if original_format == 'PNG':
        img.save(img_io, 'PNG', optimize=True, compress_level=6)
        mimetype = 'image/png'
        filename = 'scrubbed_image.png'
    elif original_format == 'WEBP':
        img.save(img_io, 'WEBP', quality=90, method=4)
        mimetype = 'image/webp'
        filename = 'scrubbed_image.webp'
    else:
        img.save(img_io, 'JPEG', quality=92, optimize=True, progressive=True)
        mimetype = 'image/jpeg'
        filename = 'scrubbed_image.jpg'

    img_io.seek(0)
    return img_io, mimetype, filename

# ---- ROUTES ----
@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'Metadata Scrubber API',
        'version': '2.0'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'time': time.time()})

# ---- IMPORTANT: OPTIONS HANDLER (CORS PREFLIGHT) ----
@app.route('/scrub', methods=['OPTIONS'])
def scrub_options():
    return '', 204

@app.route('/scrub', methods=['POST'])
def scrub_metadata():
    start_time = time.time()

    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    format_map = {
        '.jpg': 'JPEG',
        '.jpeg': 'JPEG',
        '.png': 'PNG',
        '.webp': 'WEBP'
    }
    original_format = format_map.get(ext, 'JPEG')

    img_io, mimetype, filename = process_image_fast(file.stream, original_format)
    processing_time = time.time() - start_time

    response = send_file(
        img_io,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename
    )
    response.headers['X-Processing-Time'] = f'{processing_time:.3f}'
    return response

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print(" METADATA SCRUBBER API v2.0")
    print(" Running on http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000, threaded=True)
