# Shapefile Validation Web Application

A complete web application for validating shapefiles uploaded in ZIP archives. Features a modern, responsive frontend with drag-and-drop upload and a Flask backend that runs comprehensive shapefile validation.

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- GDAL/OGR libraries installed on your system

### Installation

1. **Clone or download the project files:**
   ```bash
   mkdir shapefile-validator
   cd shapefile-validator
   ```

2. **Save the three main files:**
   - `shapefile_validator.py` (the original validation script)
   - `app.py` (Flask backend)
   - `index.html` (frontend - save in a `static/` folder)

3. **Create project structure:**
   ```bash
   mkdir static uploads
   mv index.html static/
   ```

4. **Install Python dependencies:**
   ```bash
   pip install flask gdal werkzeug
   ```

   Or create a `requirements.txt` file:
   ```txt
   Flask>=2.3.0
   GDAL>=3.4.0
   Werkzeug>=2.3.0
   ```

   Then install:
   ```bash
   pip install -r requirements.txt
   ```

### GDAL Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install gdal-bin libgdal-dev
pip install gdal
```

**CentOS/RHEL:**
```bash
sudo yum install gdal gdal-devel
pip install gdal
```

**macOS (with Homebrew):**
```bash
brew install gdal
pip install gdal
```

**Windows:**
```bash
# Using conda (recommended)
conda install gdal

# Or download from OSGeo4W
# https://trac.osgeo.org/osgeo4w/
```

### Running the Application

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

3. **Upload ZIP files containing shapefiles and get instant validation results!**

## 📁 Project Structure

```
shapefile-validator/
├── app.py                 # Flask backend
├── shapefile_validator.py # Core validation logic
├── requirements.txt       # Python dependencies
├── static/
│   └── index.html        # Frontend interface
├── uploads/              # Temporary upload directory
└── shapefile_validator.log # Application logs
```

## 🔧 Configuration

### Environment Variables

You can configure the application using environment variables:

```bash
export FLASK_ENV=production
export FLASK_SECRET_KEY=your-secret-key-here
export MAX_FILE_SIZE=52428800  # 50MB in bytes
export UPLOAD_FOLDER=/path/to/uploads
export LOG_LEVEL=INFO
```

### Application Settings

Edit `app.py` to modify these settings:

```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # Max file size
app.config['UPLOAD_FOLDER'] = 'uploads'              # Upload directory
app.config['SECRET_KEY'] = 'change-this-in-production'
```

## 🌐 Production Deployment

### Using Gunicorn (Recommended)

1. **Install Gunicorn:**
   ```bash
   pip install gunicorn
   ```

2. **Create a WSGI entry point (`wsgi.py`):**
   ```python
   from app import app
   
   if __name__ == "__main__":
       app.run()
   ```

3. **Run with Gunicorn:**
   ```bash
   gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
   ```

### Nginx Configuration

Create `/etc/nginx/sites-available/shapefile-validator`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /path/to/your/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

# Install GDAL
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "wsgi:app"]
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  shapefile-validator:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    environment:
      - FLASK_ENV=production
      - FLASK_SECRET_KEY=your-secret-key
```

## 🔍 API Documentation

### POST /validate

Upload and validate a shapefile ZIP archive.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: File upload with key `file`

**Response:**
```json
{
  "valid": true,
  "report": "Detailed validation report...",
  "shapefiles": ["boundaries", "roads"],
  "errors": [],
  "warnings": []
}
```

**Error Response:**
```json
{
  "valid": false,
  "error": "Error type",
  "report": "Detailed error message..."
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-17T10:30:00",
  "version": "1.0.0"
}
```

## 🛠️ Customization

### Adding Custom Validation Rules

Extend the `ShapefileValidator` class in `shapefile_validator.py`:

```python
def _check_custom_rule(self, shapefile_path: str) -> bool:
    """Add your custom validation logic here."""
    try:
        # Your validation code
        return True
    except Exception as e:
        self.errors.append(f"Custom validation failed: {str(e)}")
        return False
```

### Modifying the Frontend

The frontend is a single HTML file with embedded CSS and JavaScript. Key areas to customize:

- **Styling**: Modify the `<style>` section
- **Validation logic**: Update the JavaScript in the `<script>` section
- **File size limits**: Change the validation in `handleFileSelect()`

### Adding Authentication

Add authentication to protect the upload endpoint:

```python
from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/validate', methods=['POST'])
@login_required
def validate_shapefile():
    # Your existing code
    pass
```

## 📊 Monitoring and Logging

### Log Files

The application generates detailed logs in `shapefile_validator.log`:

```
2025-06-17 10:30:15,123 - INFO - File uploaded: sample.zip (1024 bytes)
2025-06-17 10:30:17,456 - INFO - Validation result for sample.zip: PASSED
2025-06-17 10:30:17,457 - INFO - Cleaned up uploaded file: sample.zip
```

### Monitoring Endpoints

Add monitoring endpoints for production:

```python
@app.route('/metrics')
def metrics():
    return jsonify({
        'uploads_today': get_upload_count_today(),
        'validation_success_rate': get_success_rate(),
        'average_processing_time': get_avg_processing_time()
    })
```

## 🚨 Troubleshooting

### Common Issues

**GDAL Import Error:**
```bash
ImportError: No module named 'osgeo'
```
Solution: Install GDAL system libraries first, then the Python bindings.

**File Upload Fails:**
- Check file size limits in both Flask and nginx
- Verify upload directory permissions
- Check available disk space

**Validation Takes Too Long:**
- Implement processing timeouts
- Add progress indicators
- Consider background job processing for large files

**Memory Issues:**
- Monitor memory usage with large files
- Implement file streaming for very large archives
- Add memory limits in production

### Debug Mode

Enable debug mode for development:

```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Performance Optimization

1. **Enable gzip compression:**
   ```python
   from flask_compress import Compress
   Compress(app)
   ```

2. **Add caching headers:**
   ```python
   @app.after_request
   def after_request(response):
       response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
       return response
   ```

3. **Background processing:**
   ```python
   from celery import Celery
   
   # For large files, process validation in background
   @celery.task
   def validate_shapefile_async(file_path):
       # Your validation logic
       pass
   ```

## 📋 Requirements File

Create `requirements.txt`:

```txt
Flask==2.3.2
GDAL>=3.4.0
Werkzeug==2.3.6
gunicorn==20.1.0
flask-compress==1.13
```

## 🔐 Security Considerations

1. **File Upload Security:**
   - Validate file types strictly
   - Scan uploads for malware
   - Limit file sizes
   - Use secure file handling

2. **Input Validation:**
   - Sanitize all inputs
   - Validate ZIP file contents
   - Prevent path traversal attacks

3. **Rate Limiting:**
   ```python
   from flask_limiter import Limiter
   from flask_limiter.util import get_remote_address
   
   limiter = Limiter(
       app,
       key_func=get_remote_address,
       default_limits=["100 per hour"]
   )
   
   @app.route('/validate', methods=['POST'])
   @limiter.limit("10 per minute")
   def validate_shapefile():
       # Your code
       pass
   ```

## 📈 Scaling Considerations

For high-traffic deployments:

1. **Load Balancing:** Use multiple app instances behind a load balancer
2. **File Storage:** Use cloud storage (AWS S3, Google Cloud Storage)
3. **Background Processing:** Use Celery with Redis/RabbitMQ
4. **Caching:** Implement Redis caching for validation results
5. **Database:** Store validation history and results

---

## 🎯 Ready to Deploy!

Your shapefile validation web application is now ready for production use. The combination of a modern, responsive frontend with a robust Flask backend provides a professional solution for shapefile validation with comprehensive error reporting and logging.