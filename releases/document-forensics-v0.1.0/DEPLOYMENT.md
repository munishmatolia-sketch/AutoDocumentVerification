# Deployment Guide

This guide covers deploying the Document Forensics application in various environments.

## Table of Contents

1. [Quick Start (Docker)](#quick-start-docker)
2. [Production Deployment](#production-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start (Docker)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/docforensics/document-forensics.git
cd document-forensics

# 2. Copy environment file
cp .env.example .env

# 3. Edit .env with your configuration
# Update SECRET_KEY, JWT_SECRET_KEY, and database credentials

# 4. Start services (simplified setup)
docker-compose -f docker-compose.simple.yml up -d

# 5. Verify services are running
docker-compose -f docker-compose.simple.yml ps

# 6. Check logs
docker-compose -f docker-compose.simple.yml logs -f

# 7. Access the application
# Web UI: http://localhost:8501
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Full Stack with Workers

```bash
# Start all services including Celery workers
docker-compose up -d

# Scale workers
docker-compose up -d --scale worker=3
```

---

## Production Deployment

### Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Python 3.9+
- PostgreSQL 15+
- Redis 7+
- Nginx (for reverse proxy)
- SSL certificate

### 1. System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip \
    postgresql-15 redis-server nginx certbot python3-certbot-nginx \
    libmagic1 libpq-dev build-essential

# Install Docker (optional, for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 2. Database Setup

```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE docforensics;
CREATE USER docforensics_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE docforensics TO docforensics_user;
\q
EOF
```

### 3. Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash docforensics
sudo su - docforensics

# Clone repository
git clone https://github.com/docforensics/document-forensics.git
cd document-forensics

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# Download spaCy model
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
nano .env  # Edit with production values
```

### 4. Database Migration

```bash
# Run migrations
alembic upgrade head

# Verify
alembic current
```

### 5. Systemd Services

Create `/etc/systemd/system/docforensics-api.service`:

```ini
[Unit]
Description=Document Forensics API
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=docforensics
Group=docforensics
WorkingDirectory=/home/docforensics/document-forensics
Environment="PATH=/home/docforensics/document-forensics/venv/bin"
ExecStart=/home/docforensics/document-forensics/venv/bin/uvicorn \
    document_forensics.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/docforensics-worker.service`:

```ini
[Unit]
Description=Document Forensics Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=docforensics
Group=docforensics
WorkingDirectory=/home/docforensics/document-forensics
Environment="PATH=/home/docforensics/document-forensics/venv/bin"
ExecStart=/home/docforensics/document-forensics/venv/bin/celery \
    -A document_forensics.core.celery_app worker \
    --loglevel=info \
    --concurrency=4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/docforensics-web.service`:

```ini
[Unit]
Description=Document Forensics Web Interface
After=network.target

[Service]
Type=simple
User=docforensics
Group=docforensics
WorkingDirectory=/home/docforensics/document-forensics
Environment="PATH=/home/docforensics/document-forensics/venv/bin"
ExecStart=/home/docforensics/document-forensics/venv/bin/streamlit run \
    src/document_forensics/web/streamlit_app.py \
    --server.port 8501 \
    --server.address 0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable docforensics-api docforensics-worker docforensics-web
sudo systemctl start docforensics-api docforensics-worker docforensics-web

# Check status
sudo systemctl status docforensics-api
sudo systemctl status docforensics-worker
sudo systemctl status docforensics-web
```

### 6. Nginx Configuration

Create `/etc/nginx/sites-available/docforensics`:

```nginx
# API Server
upstream api_backend {
    server 127.0.0.1:8000;
}

# Web Interface
upstream web_backend {
    server 127.0.0.1:8501;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name docforensics.example.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name docforensics.example.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/docforensics.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/docforensics.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # File Upload Size
    client_max_body_size 100M;

    # API Location
    location /api/ {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # API Docs
    location /docs {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Web Interface
    location / {
        proxy_pass http://web_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    # Health Check
    location /health {
        proxy_pass http://api_backend/health;
        access_log off;
    }
}
```

Enable site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/docforensics /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. SSL Certificate

```bash
# Obtain certificate
sudo certbot --nginx -d docforensics.example.com

# Auto-renewal is configured by default
# Test renewal
sudo certbot renew --dry-run
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3+ (optional)

### 1. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Configure Secrets

```bash
# Create secrets
kubectl create secret generic docforensics-secrets \
    --from-literal=secret-key='your-secret-key' \
    --from-literal=jwt-secret='your-jwt-secret' \
    --from-literal=db-password='your-db-password' \
    -n docforensics

# Or apply from file
kubectl apply -f k8s/secrets.yaml
```

### 3. Deploy Services

```bash
# Deploy in order
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/api.yaml
kubectl apply -f k8s/web.yaml
kubectl apply -f k8s/worker.yaml
kubectl apply -f k8s/ingress.yaml

# Or deploy all at once
kubectl apply -f k8s/
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n docforensics

# Check services
kubectl get svc -n docforensics

# Check ingress
kubectl get ingress -n docforensics

# View logs
kubectl logs -f deployment/docforensics-api -n docforensics
```

### 5. Scale Deployment

```bash
# Scale API
kubectl scale deployment docforensics-api --replicas=3 -n docforensics

# Scale workers
kubectl scale deployment docforensics-worker --replicas=5 -n docforensics
```

---

## Cloud Deployment

### AWS

#### Using ECS

```bash
# Build and push images
docker build -t docforensics-api:latest .
docker tag docforensics-api:latest <account-id>.dkr.ecr.<region>.amazonaws.com/docforensics-api:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/docforensics-api:latest

# Deploy using ECS CLI or CloudFormation
```

#### Using EKS

```bash
# Create EKS cluster
eksctl create cluster --name docforensics --region us-east-1

# Deploy application
kubectl apply -f k8s/
```

### Google Cloud Platform

```bash
# Create GKE cluster
gcloud container clusters create docforensics \
    --zone us-central1-a \
    --num-nodes 3

# Deploy application
kubectl apply -f k8s/
```

### Azure

```bash
# Create AKS cluster
az aks create \
    --resource-group docforensics-rg \
    --name docforensics-cluster \
    --node-count 3

# Get credentials
az aks get-credentials --resource-group docforensics-rg --name docforensics-cluster

# Deploy application
kubectl apply -f k8s/
```

---

## Configuration

### Environment Variables

Key configuration options:

```bash
# Application
APP_NAME=Document Forensics
APP_VERSION=0.1.0
ENVIRONMENT=production

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
JWT_EXPIRATION_HOURS=24

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/docforensics
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# File Upload
MAX_UPLOAD_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS=pdf,jpg,jpeg,png,docx,xlsx
UPLOAD_DIR=/var/lib/docforensics/uploads

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_TIMEOUT=300

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_RATE_LIMIT=100/minute

# Web
WEB_HOST=0.0.0.0
WEB_PORT=8501

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/docforensics/app.log
```

---

## Monitoring

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Redis health
curl http://localhost:8000/health/redis
```

### Prometheus Metrics

Metrics available at `/metrics`:

- Request count
- Response time
- Error rate
- Active connections
- Queue length

### Logging

Logs are written to:
- `/var/log/docforensics/app.log` - Application logs
- `/var/log/docforensics/audit.log` - Audit logs
- `/var/log/docforensics/error.log` - Error logs

---

## Troubleshooting

### Common Issues

#### Services won't start

```bash
# Check logs
docker-compose logs -f
# or
sudo journalctl -u docforensics-api -f

# Check ports
sudo netstat -tulpn | grep -E '8000|8501|5432|6379'
```

#### Database connection errors

```bash
# Test connection
psql -h localhost -U docforensics_user -d docforensics

# Check PostgreSQL status
sudo systemctl status postgresql
```

#### Redis connection errors

```bash
# Test connection
redis-cli ping

# Check Redis status
sudo systemctl status redis
```

#### File upload errors

```bash
# Check permissions
ls -la /var/lib/docforensics/uploads

# Fix permissions
sudo chown -R docforensics:docforensics /var/lib/docforensics/uploads
sudo chmod 755 /var/lib/docforensics/uploads
```

---

## Backup and Recovery

### Database Backup

```bash
# Backup
pg_dump -U docforensics_user docforensics > backup_$(date +%Y%m%d).sql

# Restore
psql -U docforensics_user docforensics < backup_20260130.sql
```

### File Backup

```bash
# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz /var/lib/docforensics/uploads

# Restore
tar -xzf uploads_backup_20260130.tar.gz -C /
```

---

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Set up regular backups
- [ ] Configure monitoring and alerts
- [ ] Review and update security headers
- [ ] Enable audit logging
- [ ] Implement intrusion detection
- [ ] Regular security updates

---

For additional support, please contact team@docforensics.com or open an issue on GitHub.
