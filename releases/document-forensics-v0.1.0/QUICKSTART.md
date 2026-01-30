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
