#!/bin/bash

echo "========================================="
echo "Document Forensics v0.3.0 Installation"
echo "========================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3.9+ is required"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if [ "$(printf '%s\n' "3.9" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.9" ]; then
    echo "Error: Python 3.9 or higher is required (found $PYTHON_VERSION)"
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

# Create necessary directories
echo "Creating directories..."
mkdir -p uploads/documents uploads/metadata uploads/temp
mkdir -p logs/audit
mkdir -p models

echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Set up PostgreSQL database (optional)"
echo "3. Run tests: pytest tests/ -v"
echo "4. Start the application:"
echo "   - API: uvicorn document_forensics.api.main:app --reload"
echo "   - Web: streamlit run src/document_forensics/web/streamlit_app.py"
echo ""
echo "Or use Docker:"
echo "   docker-compose -f docker-compose.simple.yml up -d"
echo ""
echo "Documentation:"
echo "   - README.md - Main documentation"
echo "   - QUICKSTART.md - Quick start guide"
echo "   - TEST_SUCCESS_SUMMARY.md - Test results"
echo ""
