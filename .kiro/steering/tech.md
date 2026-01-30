# Technology Stack & Build System

## Core Technologies

### Backend Stack
- **Python 3.9+**: Primary language with type hints and modern features
- **FastAPI**: High-performance async web framework for REST APIs
- **SQLAlchemy 2.0+**: Modern ORM with async support
- **Pydantic 2.5+**: Data validation and serialization with type safety
- **PostgreSQL**: Primary database for data persistence
- **Redis**: Caching and message queuing
- **Celery**: Distributed task queue for background processing

### AI/ML Libraries
- **OpenCV**: Computer vision and image processing
- **scikit-image**: Advanced image analysis algorithms
- **spaCy**: Natural language processing
- **NLTK**: Text analysis and linguistic processing
- **NumPy/Pandas**: Data manipulation and analysis

### Security & Cryptography
- **cryptography**: Modern cryptographic primitives
- **passlib**: Password hashing with bcrypt
- **python-jose**: JWT token handling

### Web Interface
- **Streamlit**: Interactive web application framework
- **Matplotlib**: Data visualization and plotting
- **ReportLab**: PDF report generation

## Build System & Package Management

### Project Structure
- **pyproject.toml**: Modern Python packaging with setuptools
- **requirements.txt**: Pinned dependencies for reproducible builds
- **Docker**: Containerized deployment with multi-stage builds
- **docker-compose.yml**: Local development environment

### Development Tools
- **Black**: Code formatting (line length: 88)
- **Flake8**: Linting and style checking
- **MyPy**: Static type checking with strict configuration
- **pytest**: Testing framework with async support
- **Hypothesis**: Property-based testing for robust validation

## Common Commands

### Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Set up environment
cp .env.example .env
```

### Running Services
```bash
# Full system with Docker
docker-compose up -d

# API server (development)
uvicorn document_forensics.api.main:app --reload

# Celery worker
celery -A document_forensics.core.celery_app worker --loglevel=info

# Web interface
streamlit run src/document_forensics/web/streamlit_app.py

# CLI interface
forensics --help
```

### Testing & Quality
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=document_forensics

# Property-based tests
pytest -m property

# Code formatting
black src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Operations
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Initialize database
python -m document_forensics.database.init_db
```

## Configuration Management

### Environment Variables
- Use `.env` files for local development
- Environment-specific settings in `src/document_forensics/core/config.py`
- Pydantic Settings for validation and type safety
- Docker environment variables for containerized deployment

### Key Settings
- **Database**: PostgreSQL connection strings
- **Redis**: Cache and queue configuration
- **Security**: JWT secrets and encryption keys
- **File Upload**: Size limits and allowed types
- **Processing**: Concurrency and timeout settings