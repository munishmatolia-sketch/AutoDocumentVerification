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
