from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
import io
import os
import time
from pathlib import Path
from enum import Enum

app = Flask(__name__)
CORS(app)


class ErrorCategory(Enum):
    """Error categories for better error handling."""
    INPUT_ERROR = "input_error"
    PERMISSION_ERROR = "permission_error"
    OUTPUT_ERROR = "output_error"
    PROCESSING_ERROR = "processing_error"


class ImageScrubber:
    """Professional image metadata scrubber."""
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    MAX_DIMENSION = 8192  # Prevent processing extremely large images
    
    @classmethod
    def can_handle(cls, filename: str) -> bool:
        """Check if file format is supported."""
        ext = Path(filename).suffix.lower()
        return ext in cls.SUPPORTED_FORMATS
    
    @classmethod
    def validate_image(cls, file_stream) -> tuple[bool, str, Image.Image]:
        """
        Validate image file before processing.
        
        Returns:
            (is_valid, error_message, image_object)
        """
        try:
            img = Image.open(file_stream)
            
            # Check if format is determined
            if not img.format:
                return False, "Could not determine image format", None
            
            # Check image size for safety
            width, height = img.size
            if width <= 0 or height <= 0:
                return False, "Invalid image dimensions", None
            
            if width > 50000 or height > 50000:
                return False, "Image dimensions too large (max 50000x50000)", None
            
            return True, "", img
            
        except UnidentifiedImageError:
            return False, "Not a valid image file or unsupported format", None
        except Exception as e:
            return False, f"Image validation failed: {str(e)}", None
    
    @classmethod
    def scrub_metadata(cls, img: Image.Image, original_format: str) -> tuple[io.BytesIO, str, str]:
        """
        Remove metadata from image.
        
        Returns:
            (image_bytes, mimetype, filename)
        """
        try:
            # Store original dimensions
            width, height = img.size
            
            # Optimization: Resize if too large
            if max(width, height) > cls.MAX_DIMENSION:
                ratio = cls.MAX_DIMENSION / max(width, height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Handle transparency for JPEG
            if img.mode in ('RGBA', 'LA', 'P'):
                if original_format == 'JPEG':
                    # JPEG doesn't support transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1])
                        img = background
                else:
                    img = img.convert('RGBA')
            elif img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Create clean image by extracting pixel data only
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)
            
            # Save to BytesIO with format-specific optimization
            img_io = io.BytesIO()
            
            if original_format == 'JPEG':
                clean_img.save(img_io, 'JPEG', quality=95, optimize=True, progressive=True)
                mimetype = 'image/jpeg'
                filename = 'scrubbed_image.jpg'
            elif original_format == 'PNG':
                clean_img.save(img_io, 'PNG', optimize=True, compress_level=6)
                mimetype = 'image/png'
                filename = 'scrubbed_image.png'
            elif original_format == 'WEBP':
                clean_img.save(img_io, 'WEBP', quality=95, method=4)
                mimetype = 'image/webp'
                filename = 'scrubbed_image.webp'
            else:
                # Default to JPEG for other formats
                clean_img.save(img_io, 'JPEG', quality=95, optimize=True)
                mimetype = 'image/jpeg'
                filename = 'scrubbed_image.jpg'
            
            img_io.seek(0)
            return img_io, mimetype, filename
            
        except OSError as e:
            raise RuntimeError(f"I/O error during processing: {e}")
        except (ValueError, RuntimeError) as e:
            raise RuntimeError(f"Processing failed: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {type(e).__name__}: {e}")


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


@app.route('/formats', methods=['GET'])
def supported_formats():
    """Return supported file formats."""
    return jsonify({
        'formats': list(ImageScrubber.SUPPORTED_FORMATS),
        'max_dimension': ImageScrubber.MAX_DIMENSION
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })


@app.route('/scrub', methods=['POST'])
def scrub_metadata():
    """
    Scrub metadata from uploaded image.
    
    Expects:
        - multipart/form-data with 'image' file
    
    Returns:
        - Clean image file or error JSON
    """
    start_time = time.time()
    
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({
                'error': 'No image provided',
                'category': ErrorCategory.INPUT_ERROR.value,
                'hint': 'Include an image file with key "image" in the request'
            }), 400
        
        file = request.files['image']
        
        # Validate filename
        if not file.filename:
            return jsonify({
                'error': 'Empty filename',
                'category': ErrorCategory.INPUT_ERROR.value,
                'hint': 'Provide a valid filename'
            }), 400
        
        # Check if format is supported
        if not ImageScrubber.can_handle(file.filename):
            supported = ', '.join(ImageScrubber.SUPPORTED_FORMATS)
            return jsonify({
                'error': f'Unsupported file format',
                'category': ErrorCategory.INPUT_ERROR.value,
                'hint': f'Supported formats: {supported}',
                'received_format': Path(file.filename).suffix.lower()
            }), 400
        
        # Validate image
        is_valid, error_msg, img = ImageScrubber.validate_image(file.stream)
        
        if not is_valid:
            return jsonify({
                'error': error_msg,
                'category': ErrorCategory.INPUT_ERROR.value,
                'hint': 'Ensure the file is a valid image in a supported format'
            }), 400
        
        # Get original format
        original_format = img.format
        
        try:
            # Scrub metadata
            img_io, mimetype, filename = ImageScrubber.scrub_metadata(img, original_format)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Create response
            response = send_file(
                img_io,
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
            
            # Add custom headers
            response.headers['X-Processing-Time'] = f'{processing_time:.3f}'
            response.headers['X-Original-Format'] = original_format
            response.headers['X-Metadata-Removed'] = 'EXIF, IPTC, XMP'
            
            return response
            
        except RuntimeError as e:
            return jsonify({
                'error': str(e),
                'category': ErrorCategory.PROCESSING_ERROR.value,
                'hint': 'File may be corrupted or use an unusual image variant'
            }), 500
        
        finally:
            # Clean up image object
            if img:
                img.close()
    
    except Exception as e:
        error_time = time.time() - start_time
        app.logger.error(f"Unexpected error after {error_time:.2f}s: {str(e)}")
        
        return jsonify({
            'error': f'Unexpected server error: {type(e).__name__}',
            'category': ErrorCategory.PROCESSING_ERROR.value,
            'hint': 'Report this error if it persists',
            'processing_time': f'{error_time:.3f}'
        }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors."""
    return jsonify({
        'error': 'File too large',
        'category': ErrorCategory.INPUT_ERROR.value,
        'hint': 'Maximum file size is 100MB',
        'max_size': '100MB'
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors."""
    return jsonify({
        'error': 'Internal server error',
        'category': ErrorCategory.PROCESSING_ERROR.value,
        'hint': 'An unexpected error occurred. Please try again.'
    }), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 METADATA SCRUBBER API v2.1 - PROFESSIONAL")
    print("="*60)
    print("📍 Running on: http://127.0.0.1:5000")
    print("🔧 Error Handling: Enhanced")
    print("✅ Validation: Enabled")
    print("⚡ Optimizations: Active")
    print(f"📁 Supported: {', '.join(ImageScrubber.SUPPORTED_FORMATS)}")
    print("="*60 + "\n")
    
    # Configure max upload size (100MB)
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
    
    app.run(debug=True, port=5000, threaded=True)