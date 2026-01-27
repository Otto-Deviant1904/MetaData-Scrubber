from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import io
import os

app = Flask(__name__)
CORS(app)  # Allow frontend to communicate with backend

@app.route('/')
def home():
    return "Metadata Scrubber API is running!"

@app.route('/scrub', methods=['POST'])
def scrub_metadata():
    try:
        # Get the uploaded file
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        # Open image with PIL
        img = Image.open(file.stream)
        
        # Create a new image without metadata
        # Convert to RGB if necessary (handles transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Save to bytes buffer without metadata
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')  # PNG format, no EXIF data
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='scrubbed_image.png')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)