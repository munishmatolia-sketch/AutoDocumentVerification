#!/bin/bash

# Document Forensics Release Script
# This script creates a release package for the application

set -e

VERSION="0.1.0"
RELEASE_NAME="document-forensics-v${VERSION}"
RELEASE_DIR="releases/${RELEASE_NAME}"

echo "========================================="
echo "Document Forensics Release Creator"
echo "Version: ${VERSION}"
echo "========================================="
echo ""

# Create release directory
echo "Creating release directory..."
mkdir -p "${RELEASE_DIR}"

# Copy application files
echo "Copying application files..."
cp -r src "${RELEASE_DIR}/"
cp -r tests "${RELEASE_DIR}/"
cp -r k8s "${RELEASE_DIR}/"
cp -r scripts "${RELEASE_DIR}/"

# Copy configuration files
echo "Copying configuration files..."
cp requirements.txt "${RELEASE_DIR}/"
cp pyproject.toml "${RELEASE_DIR}/"
cp Dockerfile "${RELEASE_DIR}/"
cp docker-compose.yml "${RELEASE_DIR}/"
cp docker-compose.simple.yml "${RELEASE_DIR}/"
cp .env.example "${RELEASE_DIR}/"
cp .gitignore "${RELEASE_DIR}/"

# Copy documentation
echo "Copying documentation..."
cp README.md "${RELEASE_DIR}/"
cp RELEASE_NOTES.md "${RELEASE_DIR}/"
cp CHANGELOG.md "${RELEASE_DIR}/"
cp DEPLOYMENT.md "${RELEASE_DIR}/"

# Create LICENSE file if it doesn't exist
if [ ! -f LICENSE ]; then
    echo "Creating LICENSE file..."
    cat > "${RELEASE_DIR}/LICENSE" << 'EOF'
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
EOF
else
    cp LICENSE "${RELEASE_DIR}/"
fi

# Create installation script
echo "Creating installation script..."
cat > "${RELEASE_DIR}/install.sh" << 'EOF'
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
EOF

chmod +x "${RELEASE_DIR}/install.sh"

# Create quick start guide
echo "Creating quick start guide..."
cat > "${RELEASE_DIR}/QUICKSTART.md" << 'EOF'
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

```bash
# 1. Run installation script
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
EOF

# Create checksums
echo "Creating checksums..."
cd releases
find "${RELEASE_NAME}" -type f -exec sha256sum {} \; > "${RELEASE_NAME}.sha256"
cd ..

# Create tarball
echo "Creating release tarball..."
cd releases
tar -czf "${RELEASE_NAME}.tar.gz" "${RELEASE_NAME}"
cd ..

# Create zip archive
echo "Creating release zip..."
cd releases
zip -r "${RELEASE_NAME}.zip" "${RELEASE_NAME}" > /dev/null
cd ..

# Generate release summary
echo "Generating release summary..."
cat > "releases/${RELEASE_NAME}-SUMMARY.txt" << EOF
Document Forensics v${VERSION} Release Summary
================================================

Release Date: $(date +"%Y-%m-%d")
Release Type: Initial Alpha Release

Files Included:
- ${RELEASE_NAME}.tar.gz (Linux/macOS)
- ${RELEASE_NAME}.zip (Windows)
- ${RELEASE_NAME}.sha256 (Checksums)

Installation:
1. Extract the archive
2. Run ./install.sh (Linux/macOS) or follow QUICKSTART.md
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
$(sha256sum "releases/${RELEASE_NAME}.tar.gz" 2>/dev/null || echo "N/A")
$(sha256sum "releases/${RELEASE_NAME}.zip" 2>/dev/null || echo "N/A")
EOF

echo ""
echo "========================================="
echo "Release Created Successfully!"
echo "========================================="
echo ""
echo "Release files:"
echo "  - releases/${RELEASE_NAME}.tar.gz"
echo "  - releases/${RELEASE_NAME}.zip"
echo "  - releases/${RELEASE_NAME}.sha256"
echo "  - releases/${RELEASE_NAME}-SUMMARY.txt"
echo ""
echo "Next steps:"
echo "1. Test the release package"
echo "2. Create GitHub release"
echo "3. Upload release artifacts"
echo "4. Announce the release"
echo ""
