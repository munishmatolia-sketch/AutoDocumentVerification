# Document Forensics Release Script (PowerShell)
# This script creates a release package for the application

$ErrorActionPreference = "Stop"

$VERSION = "0.1.0"
$RELEASE_NAME = "document-forensics-v$VERSION"
$RELEASE_DIR = "releases\$RELEASE_NAME"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Document Forensics Release Creator" -ForegroundColor Cyan
Write-Host "Version: $VERSION" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Create release directory
Write-Host "Creating release directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $RELEASE_DIR | Out-Null

# Copy application files
Write-Host "Copying application files..." -ForegroundColor Yellow
Copy-Item -Path "src" -Destination "$RELEASE_DIR\" -Recurse -Force
Copy-Item -Path "tests" -Destination "$RELEASE_DIR\" -Recurse -Force
Copy-Item -Path "k8s" -Destination "$RELEASE_DIR\" -Recurse -Force
Copy-Item -Path "scripts" -Destination "$RELEASE_DIR\" -Recurse -Force

# Copy configuration files
Write-Host "Copying configuration files..." -ForegroundColor Yellow
Copy-Item -Path "requirements.txt" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path "pyproject.toml" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path "Dockerfile" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path "docker-compose.yml" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path "docker-compose.simple.yml" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path ".env.example" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path ".gitignore" -Destination "$RELEASE_DIR\" -Force

# Copy documentation
Write-Host "Copying documentation..." -ForegroundColor Yellow
Copy-Item -Path "README.md" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path "RELEASE_NOTES.md" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path "CHANGELOG.md" -Destination "$RELEASE_DIR\" -Force
Copy-Item -Path "DEPLOYMENT.md" -Destination "$RELEASE_DIR\" -Force

# Create LICENSE file if it doesn't exist
if (-not (Test-Path "LICENSE")) {
    Write-Host "Creating LICENSE file..." -ForegroundColor Yellow
    @"
MIT License

Copyright (c) 2026 Document Forensics Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"@ | Out-File -FilePath "$RELEASE_DIR\LICENSE" -Encoding UTF8
} else {
    Copy-Item -Path "LICENSE" -Destination "$RELEASE_DIR\" -Force
}

# Create installation script (bash for Linux/macOS)
Write-Host "Creating installation script..." -ForegroundColor Yellow
@'
#!/bin/bash

echo "========================================="
echo "Document Forensics Installation"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "Warning: Docker is not installed. Docker deployment will not be available."
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# Download spaCy model
echo "Downloading spaCy model..."
python -m spacy download en_core_web_sm || echo "Warning: Failed to download spaCy model"

# Create .env file
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
fi

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Set up PostgreSQL database"
echo "3. Run database migrations: alembic upgrade head"
echo "4. Start the application:"
echo "   - API: uvicorn document_forensics.api.main:app --reload"
echo "   - Web: streamlit run src/document_forensics/web/streamlit_app.py"
echo ""
echo "Or use Docker:"
echo "   docker-compose -f docker-compose.simple.yml up -d"
echo ""
'@ | Out-File -FilePath "$RELEASE_DIR\install.sh" -Encoding UTF8

# Create installation script (PowerShell for Windows)
@'
# Document Forensics Installation Script (Windows)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Document Forensics Installation" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Python 3 is not installed" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Warning: Docker is not installed. Docker deployment will not be available." -ForegroundColor Yellow
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

# Download spaCy model
Write-Host "Downloading spaCy model..." -ForegroundColor Yellow
python -m spacy download en_core_web_sm

# Create .env file
if (-not (Test-Path .env)) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "Please edit .env file with your configuration" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit .env file with your configuration"
Write-Host "2. Set up PostgreSQL database"
Write-Host "3. Run database migrations: alembic upgrade head"
Write-Host "4. Start the application:"
Write-Host "   - API: uvicorn document_forensics.api.main:app --reload"
Write-Host "   - Web: streamlit run src/document_forensics/web/streamlit_app.py"
Write-Host ""
Write-Host "Or use Docker:"
Write-Host "   docker-compose -f docker-compose.simple.yml up -d"
Write-Host ""
'@ | Out-File -FilePath "$RELEASE_DIR\install.ps1" -Encoding UTF8

# Create quick start guide
Write-Host "Creating quick start guide..." -ForegroundColor Yellow
@'
# Quick Start Guide

## Option 1: Docker (Recommended)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env with your configuration
nano .env

# 3. Start all services
docker-compose -f docker-compose.simple.yml up -d

# 4. Access the application
# Web: http://localhost:8501
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## Option 2: Manual Installation

### Linux/macOS

```bash
# 1. Run installation script
chmod +x install.sh
./install.sh

# 2. Activate virtual environment
source venv/bin/activate

# 3. Set up database
# Create PostgreSQL database and user
# Update DATABASE_URL in .env

# 4. Run migrations
alembic upgrade head

# 5. Start services
# Terminal 1: API
uvicorn document_forensics.api.main:app --reload

# Terminal 2: Web Interface
streamlit run src/document_forensics/web/streamlit_app.py
```

### Windows

```powershell
# 1. Run installation script
.\install.ps1

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Set up database
# Create PostgreSQL database and user
# Update DATABASE_URL in .env

# 4. Run migrations
alembic upgrade head

# 5. Start services
# Terminal 1: API
uvicorn document_forensics.api.main:app --reload

# Terminal 2: Web Interface
streamlit run src/document_forensics/web/streamlit_app.py
```

## Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Access web interface
# Open browser: http://localhost:8501
```

## Next Steps

- Read DEPLOYMENT.md for production deployment
- See README.md for detailed documentation
- Check RELEASE_NOTES.md for features and known issues
'@ | Out-File -FilePath "$RELEASE_DIR\QUICKSTART.md" -Encoding UTF8

# Create checksums
Write-Host "Creating checksums..." -ForegroundColor Yellow
$checksumFile = "releases\$RELEASE_NAME.sha256"
Get-ChildItem -Path $RELEASE_DIR -Recurse -File | ForEach-Object {
    $hash = Get-FileHash -Path $_.FullName -Algorithm SHA256
    $relativePath = $_.FullName.Replace((Get-Location).Path + "\", "")
    "$($hash.Hash)  $relativePath"
} | Out-File -FilePath $checksumFile -Encoding UTF8

# Create zip archive
Write-Host "Creating release zip..." -ForegroundColor Yellow
$zipPath = "releases\$RELEASE_NAME.zip"
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
Compress-Archive -Path $RELEASE_DIR -DestinationPath $zipPath -CompressionLevel Optimal

# Generate release summary
Write-Host "Generating release summary..." -ForegroundColor Yellow
$date = Get-Date -Format "yyyy-MM-dd"
$zipHash = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash

@"
Document Forensics v$VERSION Release Summary
================================================

Release Date: $date
Release Type: Initial Alpha Release

Files Included:
- $RELEASE_NAME.zip (Windows/Linux/macOS)
- $RELEASE_NAME.sha256 (Checksums)

Installation:
1. Extract the archive
2. Run install.ps1 (Windows) or install.sh (Linux/macOS)
3. Configure .env file
4. Start services

Documentation:
- README.md - Main documentation
- QUICKSTART.md - Quick start guide
- DEPLOYMENT.md - Production deployment guide
- RELEASE_NOTES.md - Release notes and features
- CHANGELOG.md - Version history

Support:
- GitHub: https://github.com/docforensics/document-forensics
- Issues: https://github.com/docforensics/document-forensics/issues
- Email: team@docforensics.com

Checksums (SHA-256):
$zipHash  $RELEASE_NAME.zip
"@ | Out-File -FilePath "releases\$RELEASE_NAME-SUMMARY.txt" -Encoding UTF8

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "Release Created Successfully!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Release files:" -ForegroundColor Cyan
Write-Host "  - releases\$RELEASE_NAME.zip" -ForegroundColor White
Write-Host "  - releases\$RELEASE_NAME.sha256" -ForegroundColor White
Write-Host "  - releases\$RELEASE_NAME-SUMMARY.txt" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test the release package"
Write-Host "2. Create GitHub release"
Write-Host "3. Upload release artifacts"
Write-Host "4. Announce the release"
Write-Host ""
