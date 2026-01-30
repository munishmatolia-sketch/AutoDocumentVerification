# AI-Powered Document Forensics & Verification System

A comprehensive platform that combines traditional digital forensics techniques with modern machine learning approaches to detect document tampering, verify authenticity, and extract forensic evidence.

## Features

- **Document Upload & Processing**: Support for multiple file formats (PDF, images, Office documents)
- **Metadata Extraction**: Comprehensive extraction of EXIF data, creation timestamps, and software signatures
- **AI-Powered Tampering Detection**: Machine learning models for detecting pixel-level inconsistencies and text modifications
- **🆕 Advanced Forgery Detection**: Format-specific forgery detection for Word, Excel, Text, Images, and PDF documents
  - **Word**: Revision history, hidden text, style inconsistencies, track changes analysis
  - **Excel**: Formula tampering, hidden content, macro detection, data validation bypass
  - **Text**: Encoding manipulation, invisible characters, homoglyph attacks
  - **Images**: Clone detection, noise analysis, compression artifacts, lighting inconsistencies
  - **PDF**: Digital signature verification, incremental updates, object manipulation
- **Authenticity Verification**: Multi-factor authenticity assessment with confidence scoring
- **Comprehensive Reporting**: Detailed forensic reports with visual evidence and expert testimony formatting
- **Batch Processing**: Efficient processing of multiple documents with progress tracking
- **Security & Audit**: Cryptographic hashing, encryption, and immutable audit trails
- **API Integration**: RESTful APIs for system integration and automation

## Architecture

The system follows a microservices architecture with the following components:

- **API Service**: FastAPI-based REST API
- **Worker Service**: Celery workers for background processing
- **Database**: PostgreSQL for data persistence
- **Cache/Queue**: Redis for caching and message queuing
- **Web Interface**: Streamlit-based user interface

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- PostgreSQL (if running without Docker)
- Redis (if running without Docker)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd document-forensics
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

### Running with Docker

1. Start all services:
```bash
docker-compose up -d
```

2. Access the services:
- API: http://localhost:8000
- Web Interface: http://localhost:8501
- Flower (Celery monitoring): http://localhost:5555

### Running Locally

1. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

2. Initialize the database:
```bash
python -m document_forensics.database.init_db
```

3. Start the API server:
```bash
uvicorn document_forensics.api.main:app --reload
```

4. Start Celery worker (in another terminal):
```bash
celery -A document_forensics.core.celery_app worker --loglevel=info
```

5. Start the web interface (in another terminal):
```bash
streamlit run src/document_forensics/web/app.py
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=document_forensics

# Run property-based tests
pytest -m property
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## API Documentation

Once the API server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Forgery Detection API

The system provides specialized forgery detection endpoints:

#### Detect Forgery
```bash
POST /api/v1/analysis/detect-forgery
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "document_id": 123
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Forgery detection completed. Risk level: HIGH",
  "data": {
    "document_id": 123,
    "document_type": "word",
    "overall_risk": "HIGH",
    "confidence_score": 0.85,
    "indicators": [
      {
        "type": "HIDDEN_TEXT",
        "description": "Hidden text found in paragraph 5",
        "confidence": 0.95,
        "severity": "HIGH",
        "location": {"paragraph": 5, "run": 3},
        "evidence": {"text_content": "hidden content..."}
      }
    ],
    "detection_methods_used": ["hidden_text_detection", "revision_history_analysis"]
  }
}
```

#### Get Forgery Report
```bash
GET /api/v1/analysis/forgery-report/{document_id}
Authorization: Bearer YOUR_TOKEN
```

Returns a comprehensive forgery analysis report with recommendations.

### Python SDK Usage

```python
from document_forensics.analysis.forgery_detector import ForgeryDetector

# Initialize detector
detector = ForgeryDetector()

# Detect forgery
results = await detector.detect_forgery(
    document_path="path/to/document.docx",
    document_id=123
)

# Access results
print(f"Risk Level: {results.overall_risk}")
print(f"Confidence: {results.confidence_score:.1%}")

# Review indicators
for indicator in results.indicators:
    print(f"{indicator.severity}: {indicator.type}")
    print(f"  {indicator.description}")
```

For detailed forgery detection documentation, see [FORGERY_DETECTION_COMPLETE.md](FORGERY_DETECTION_COMPLETE.md).

## Configuration

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/document_forensics

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here

# File Upload
MAX_FILE_SIZE=104857600  # 100MB
UPLOAD_DIRECTORY=uploads

# Processing
MAX_CONCURRENT_JOBS=4
JOB_TIMEOUT_MINUTES=30
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on the GitHub repository.