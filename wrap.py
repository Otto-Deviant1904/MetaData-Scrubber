from pathlib import Path
import tempfile
from flask import Flask, request, send_file, jsonify, after_this_request
from flask_cors import CORS
import time
from werkzeug.utils import secure_filename
from image_scrubber import ImageScrubber, ResultType

app = Flask(__name__)
CORS(app)

#Max upload size: 200MB
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024


@app.route('/')
def home():
    """API home endpoint."""
    return jsonify({
        'status': 'running',
        'service': 'Metadata Scrubber API',
        'version': '2.1',
        'endpoints': ['/scrub', '/health', '/formats'],
        'supported_formats': list(ImageScrubber.SUPPORTED_FORMATS)
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route('/scrub', methods=['POST'])
def scrub():
    start_time = time.time()

    # ---- basic request validation ----
    if 'image' not in request.files:
        return jsonify({
            "error": "No image provided",
            "category": "input_error",
            "hint": "Send multipart/form-data with key 'image'"
        }), 400

    file = request.files['image']

    if not file.filename:
        return jsonify({
            "error": "Empty filename",
            "category": "input_error"
        }), 400

    # ---- temp filesystem boundary ----
    tmpdir = Path(tempfile.mkdtemp(prefix="metadata_scrubber_"))

    @after_this_request
    def cleanup_temp_dir(response):
        for _ in range(3):
            try:
                for file_path in tmpdir.glob('*'):
                    file_path.unlink(missing_ok=True)
                tmpdir.rmdir()
                break
            except OSError:
                time.sleep(0.05)
        return response

    safe_name = secure_filename(file.filename)
    if not safe_name:
        return jsonify({
            "error": "Invalid filename",
            "category": "input_error",
            "hint": "Use a standard image filename"
        }), 400

    input_path = tmpdir / safe_name
    output_path = tmpdir / f"scrubbed_{safe_name}"

    # Save uploaded file
    file.save(input_path)

    # ---- call CORE logic ----
    result = ImageScrubber.scrub(input_path, output_path)

    if result.result_type == ResultType.ERROR:
        return jsonify({
            "error": result.error,
            "category": result.error_category.value,
            "hint": result.fix_hint
        }), 400

    processing_time = time.time() - start_time

    # ---- success response ----
    response = send_file(
        output_path,
        as_attachment=True,
        download_name=output_path.name
    )

    response.headers['X-Processing-Time'] = f"{processing_time:.3f}"
    response.headers['X-Metadata-Removed'] = result.metadata_removed or "EXIF/IPTC/XMP"

    return response


@app.errorhandler(413)
def file_too_large(_):
    return jsonify({
        "error": "File too large",
        "category": "input_error",
        "hint": "Maximum file size is 200MB"
    }), 413


@app.errorhandler(500)
def internal_error(_):
    return jsonify({
        "error": "Internal server error",
        "category": "processing_error",
        "hint": "Check server logs"
    }), 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" METADATA SCRUBBER FLASK WRAPPER")
    print("=" * 60)
    print(" http://127.0.0.1:5000")
    print(" Core-driven architecture")
    print(" Metadata stripping delegated to core")
    print("=" * 60 + "\n")

    app.run(debug=True, port=5000, threaded=True)
                                                                                   
