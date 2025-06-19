# 🐳 Docker Quick Start Guide

Get your Shapefile Validator running in Docker in under 5 minutes!

## 📋 Prerequisites

- Docker installed on your system
- Docker Compose (usually comes with Docker Desktop)

## 🚀 Quick Setup

### 1. Create Project Directory
```bash
mkdir shapefile-validator-docker
cd shapefile-validator-docker
```

### 2. Download/Create Files

Create the following file structure:
```
shapefile-validator-docker/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── app.py
├── shapefile_validator.py
├── static/
│   └── index.html
├── uploads/          # Will be created automatically
└── logs/            # Will be created automatically
```

**Save each artifact file to its corresponding location:**
- `Dockerfile` → root directory
- `docker-compose.yml` → root directory  
- `requirements.txt` → root directory
- `app.py` → root directory (Flask backend from previous artifact)
- `shapefile_validator.py` → root directory (original validation script)
- `index.html` → `static/` directory (frontend from previous artifact)

### 3. Build and Run

**Option A: Simple Docker Run**
```bash
# Build the image
docker build -t shapefile-validator .

# Run the container
docker run -p 5000:5000 --name shapefile-validator shapefile-validator
```

**Option B: Docker Compose (Recommended)**
```bash
# Build and start in one command
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 4. Access the Application

Open your browser and go to:
```
http://localhost:5000
```

## 🎯 Testing the Setup

1. **Upload a test ZIP file** containing shapefiles
2. **Check the validation results** in the browser
3. **View logs** to ensure everything is working:
   ```bash
   docker-compose logs -f shapefile-validator
   ```

## 🛠️ Development Commands

### View Running Containers
```bash
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs shapefile-validator

# Follow logs in real-time
docker-compose logs -f
```

### Stop Services
```bash
docker-compose down
```

### Rebuild After Changes
```bash
docker-compose down
docker-compose up --build
```

### Clean Up Everything
```bash
docker-compose down --volumes --rmi all
```

## 🔧 Configuration Options

### Environment Variables

Modify `docker-compose.yml` to customize:

```yaml
environment:
  - FLASK_ENV=development  # or production
  - FLASK_SECRET_KEY=your-secret-key
  - MAX_FILE_SIZE=104857600  # 100MB in bytes
  - LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### Volume Mounts

Keep uploaded files and logs persistent:

```yaml
volumes:
  - ./uploads:/app/uploads      # Uploaded files
  - ./logs:/app/logs           # Application logs
  - ./custom-config:/app/config # Custom configuration
```

### Port Configuration

Change the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8080:5000"  # Access via http://localhost:8080
```

## 🏗️ Production Setup with Nginx

For a production-like setup with Nginx:

1. **Create nginx.conf:**
```nginx
events {
    worker_connections 1024;
}

http {
    upstream shapefile_app {
        server shapefile-validator:5000;
    }

    server {
        listen 80;
        client_max_body_size 50M;

        location / {
            proxy_pass http://shapefile_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        location /static {
            alias /usr/share/nginx/html/static;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

2. **Run with Nginx:**
```bash
docker-compose --profile production up --build
```

3. **Access via:** `http://localhost` (port 80)

## 🧪 Testing Different Scenarios

### Test with Sample Files

Create test shapefiles to validate the setup:

```bash
# Create a sample directory structure for testing
mkdir test-files
cd test-files

# You can download sample shapefiles or create basic ones
# Then zip them for testing
zip sample-shapefile.zip *.shp *.shx *.dbf *.prj
```

### Load Testing

Test with multiple files:

```bash
# Upload multiple files simultaneously to test performance
curl -X POST -F "file=@test1.zip" http://localhost:5000/validate &
curl -X POST -F "file=@test2.zip" http://localhost:5000/validate &
curl -X POST -F "file=@test3.zip" http://localhost:5000/validate &
```

## 🐛 Troubleshooting

### Common Issues

**1. Container won't start:**
```bash
# Check logs
docker-compose logs shapefile-validator

# Check if port is in use
netstat -tulpn | grep :5000
```

**2. GDAL import errors:**
```bash
# Rebuild with no cache
docker-compose build --no-cache
```

**3. Permission denied errors:**
```bash
# Fix file permissions
chmod -R 755 uploads logs
```

**4. File upload fails:**
```bash
# Check container resources
docker stats shapefile-validator

# Increase memory if needed
docker-compose down
docker-compose up --build -m 2g
```

### Health Check

The container includes a health check endpoint:

```bash
# Check health status
curl http://localhost:5000/health

# View health status in Docker
docker inspect --format='{{.State.Health.Status}}' shapefile-validator
```

## 📊 Monitoring

### Container Metrics
```bash
# View resource usage
docker stats shapefile-validator

# View container details
docker inspect shapefile-validator
```

### Application Logs
```bash
# View recent logs
docker-compose logs --tail=50 shapefile-validator

# Monitor logs in real-time
docker-compose logs -f shapefile-validator
```

## 🎉 Success!

If you can access `http://localhost:5000` and see the shapefile validator interface, you're all set! The Docker container provides a complete, isolated environment with all dependencies pre-installed.

## Next Steps

1. **Test with real shapefiles** to validate functionality
2. **Customize the configuration** for your specific needs  
3. **Set up production deployment** using the provided configurations
4. **Scale horizontally** by running multiple container instances

Your shapefile validator is now running in a portable, reproducible Docker environment! 🎯
