from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import io
import os
from concurrent.futures import ThreadPoolExecutor
import time

app = Flask(__name__)
CORS(app)

# Thread pool for async processing
executor = ThreadPoolExecutor(max_workers=4)

def process_image_fast(file_stream, original_format):
    """Fast image processing with optimizations"""
    
    
    img = Image.open(file_stream)
    
    
    width, height = img.size
    
    # Optimization 1: Resize huge images for faster processing, pain in the ahh
    MAX_DIMENSION = 8192  # Seems legit
    if max(width, height) > MAX_DIMENSION:
        ratio = MAX_DIMENSION / max(width, height)
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    # Optimization 2: Handle transparency efficiently, idk why but ok
    if img.mode in ('RGBA', 'LA', 'P'):
        if original_format == 'JPEG':
            # Convert to RGB for JPEG (no transparency), for coloured images
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
                img = background
        else:
            # Keep RGBA for PNG
            img = img.convert('RGBA')
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Optimization 3: Use BytesIO for in-memory processing
    img_io = io.BytesIO()
    
    # Optimization 4: Format-specific optimizations, JPEG is easy tbh
    if original_format == 'JPEG':
        # JPEG: Fast with good quality
        img.save(img_io, 'JPEG', quality=92, optimize=True, progressive=True)
        mimetype = 'image/jpeg'
        filename = 'scrubbed_image.jpg'
    elif original_format == 'PNG':
        # PNG: Balanced compression (6 is sweet spot)
        img.save(img_io, 'PNG', optimize=True, compress_level=6)
        mimetype = 'image/png'
        filename = 'scrubbed_image.png'
    elif original_format == 'WEBP':
        # WEBP: Best compression/quality ratio
        img.save(img_io, 'WEBP', quality=90, method=4)
        mimetype = 'image/webp'
        filename = 'scrubbed_image.webp'
    else:
        # Default to JPEG for speed
        img.save(img_io, 'JPEG', quality=92, optimize=True)
        mimetype = 'image/jpeg'
        filename = 'scrubbed_image.jpg'
    
    img_io.seek(0)
    return img_io, mimetype, filename

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'Metadata Scrubber API',
        'version': '2.0',
        'endpoints': ['/scrub']
    })

@app.route('/scrub', methods=['POST'])
def scrub_metadata():
    """Optimized metadata scrubbing endpoint"""
    
    start_time = time.time()
    
    try:
        # Validation
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        if not file.filename:
            return jsonify({'error': 'Empty filename'}), 400
        
        # Detect format from file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        format_map = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.png': 'PNG',
            '.webp': 'WEBP',
            '.bmp': 'BMP',
            '.tiff': 'TIFF'
        }
        original_format = format_map.get(file_ext, 'JPEG')
        
        # Process image
        img_io, mimetype, filename = process_image_fast(file.stream, original_format)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Add custom header with processing time
        response = send_file(
            img_io,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        response.headers['X-Processing-Time'] = f'{processing_time:.3f}'
        
        return response
    
    except Exception as e:
        error_time = time.time() - start_time
        print(f"Error after {error_time:.2f}s: {str(e)}")
        return jsonify({
            'error': str(e),
            'processing_time': f'{error_time:.3f}'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print(" METADATA SCRUBBER API v2.0 - OPTIMIZED")
    print("="*60)
    print(" Running on: http://127.0.0.1:5000")
    print(" Optimizations: Enabled")
    print(" Max workers: 4")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, threaded=True)