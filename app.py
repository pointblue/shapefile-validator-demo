#!/usr/bin/env python3
"""
Fixed Flask Web Application for Shapefile Validation

This version fixes the validation logic to properly report results
and eliminates the conflicting success/failure messages.

Requirements:
- Flask
- GDAL/OGR Python bindings
- werkzeug (for secure file handling)

Usage:
    python app.py
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
import logging
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Import our shapefile validator
try:
    from shapefile_validator import ShapefileValidator
except ImportError:
    print("ERROR: shapefile_validator.py not found in the current directory.")
    print("Please ensure the ShapefileValidator class is available.")
    sys.exit(1)

# Configure Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shapefile_validator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'zip'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Clean up old uploaded files (older than 1 hour)."""
    try:
        upload_folder = Path(app.config['UPLOAD_FOLDER'])
        current_time = datetime.now().timestamp()
        
        for file_path in upload_folder.glob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > 3600:  # 1 hour in seconds
                    file_path.unlink()
                    logger.info(f"Cleaned up old file: {file_path.name}")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

@app.route('/')
def index():
    """Serve the main HTML page."""
    # In production, you'd serve this from a templates directory
    # For now, we'll return a simple redirect message
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Shapefile Validator</title>
        <meta http-equiv="refresh" content="0; url=/static/index.html">
    </head>
    <body>
        <p>If you're not redirected automatically, <a href="/static/index.html">click here</a>.</p>
    </body>
    </html>
    '''

@app.route('/validate', methods=['POST'])
def validate_shapefile():
    """API endpoint to validate uploaded shapefile."""
    
    # Clean up old files before processing
    cleanup_old_files()
    
    # Check if file was uploaded
    if 'file' not in request.files:
        logger.warning("No file uploaded")
        return jsonify({
            'valid': False,
            'error': 'No file uploaded',
            'report': 'ERROR: No file was uploaded. Please select a ZIP file containing your shapefile.',
            'shapefiles': [],
            'errors': ['No file was uploaded'],
            'warnings': []
        }), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if file.filename == '':
        logger.warning("No file selected")
        return jsonify({
            'valid': False,
            'error': 'No file selected',
            'report': 'ERROR: No file was selected. Please choose a ZIP file.',
            'shapefiles': [],
            'errors': ['No file was selected'],
            'warnings': []
        }), 400
    
    # Check file extension
    if not allowed_file(file.filename):
        logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({
            'valid': False,
            'error': 'Invalid file type',
            'report': 'ERROR: Invalid file type. Please upload a ZIP file containing your shapefile.',
            'shapefiles': [],
            'errors': ['Invalid file type - must be ZIP'],
            'warnings': []
        }), 400
    
    # Secure the filename
    filename = secure_filename(file.filename)
    if not filename:
        filename = 'upload.zip'
    
    # Generate unique filename to avoid conflicts
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    
    # Save uploaded file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    try:
        file.save(filepath)
        logger.info(f"File uploaded: {unique_filename} ({file.content_length} bytes)")
        
        # Validate the shapefile
        validator = ShapefileValidator()
        is_valid, shapefiles = validator.validate_zip_archive(filepath)
        
        # Build the report step by step
        report_sections = []
        
        # Add file info
        report_sections.append(f"Processing file: {filename}")
        report_sections.append(f"File size: {file.content_length} bytes")
        report_sections.append("")
        
        # Add shapefile discovery results
        if shapefiles:
            report_sections.append(f"Found {len(shapefiles)} shapefile(s):")
            for shp in shapefiles:
                report_sections.append(f"  - {shp}")
            report_sections.append("")
        else:
            report_sections.append("❌ No shapefiles found in ZIP archive")
            report_sections.append("")
        
        # Add detailed validation results from the validator
        validation_report = validator.get_validation_report()
        if validation_report.strip():
            report_sections.append(validation_report)
            report_sections.append("")
        
        # Add final status - this is the key fix!
        if is_valid:
            final_status = f"✅ VALIDATION PASSED for {filename}"
            status_summary = "All validation checks passed successfully!"
        else:
            final_status = f"❌ VALIDATION FAILED for {filename}"
            if validator.errors:
                error_count = len(validator.errors)
                status_summary = f"Validation failed with {error_count} error(s). See details above."
            else:
                status_summary = "Validation failed for unknown reasons."
        
        report_sections.append("=" * 50)
        report_sections.append("FINAL RESULT")
        report_sections.append("=" * 50)
        report_sections.append(final_status)
        report_sections.append("")
        report_sections.append(status_summary)
        
        # Combine all sections
        full_report = "\n".join(report_sections)
        
        # Log validation result
        logger.info(f"Validation result for {unique_filename}: {'PASSED' if is_valid else 'FAILED'}")
        if not is_valid and validator.errors:
            logger.info(f"Validation errors: {validator.errors}")
        
        # Clean up uploaded file
        try:
            os.remove(filepath)
            logger.info(f"Cleaned up uploaded file: {unique_filename}")
        except Exception as e:
            logger.warning(f"Failed to clean up file {unique_filename}: {str(e)}")
        
        # Return consistent response
        response_data = {
            'valid': is_valid,
            'report': full_report,
            'shapefiles': shapefiles,
            'errors': validator.errors,
            'warnings': validator.warnings,
            'filename': filename,
            'summary': status_summary
        }
        
        # Set appropriate HTTP status code
        status_code = 200 if is_valid else 422  # 422 = Unprocessable Entity (validation failed)
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"Error processing file {unique_filename}: {str(e)}")
        
        # Clean up file on error
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass
        
        return jsonify({
            'valid': False,
            'error': 'Processing error',
            'report': f'ERROR: An error occurred while processing the file: {str(e)}',
            'shapefiles': [],
            'errors': [f'Processing error: {str(e)}'],
            'warnings': [],
            'filename': filename,
            'summary': 'File processing failed due to an internal error.'
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.1.0'  # Updated version
    })

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file size limit exceeded."""
    logger.warning("File size limit exceeded")
    return jsonify({
        'valid': False,
        'error': 'File too large',
        'report': 'ERROR: File size exceeds the 50MB limit. Please upload a smaller file.',
        'shapefiles': [],
        'errors': ['File size exceeds 50MB limit'],
        'warnings': [],
        'summary': 'File too large to process.'
    }), 413

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found.'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again.'
    }), 500

# Development server configuration
if __name__ == '__main__':
    # Create a simple static file server for development
    @app.route('/static/<path:filename>')
    def static_files(filename):
        """Serve static files in development."""
        # In production, use a proper web server like nginx for static files
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, filename)
    
    # Print startup information
    print("="*50)
    print("🗺️  Shapefile Validator Web Application (Fixed)")
    print("="*50)
    print(f"📁 Upload folder: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    print(f"📏 Max file size: {app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB")
    print(f"🌐 Server starting at: http://localhost:5000")
    print("🔧 Fixed validation result reporting logic")
    print("="*50)
    
    # Run the development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )