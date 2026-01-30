# Project Structure & Organization

## Directory Layout

```
src/document_forensics/           # Main application package
├── analysis/                    # Core analysis modules
│   ├── authenticity_scorer.py   # Authenticity verification logic
│   ├── metadata_extractor.py    # Document metadata extraction
│   └── tampering_detector.py    # Tampering detection algorithms
├── api/                         # FastAPI REST API
│   ├── routers/                 # API route handlers
│   │   ├── analysis.py          # Analysis endpoints
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── batch.py             # Batch processing endpoints
│   │   ├── documents.py         # Document management endpoints
│   │   ├── reports.py           # Report generation endpoints
│   │   └── webhooks.py          # Webhook endpoints
│   ├── auth.py                  # Authentication logic
│   ├── exceptions.py            # Custom exception handlers
│   ├── main.py                  # FastAPI application factory
│   ├── middleware.py            # Custom middleware
│   └── server.py                # Server configuration
├── cli/                         # Command-line interface
│   ├── main.py                  # CLI command definitions
│   └── run.py                   # CLI entry point
├── core/                        # Core application logic
│   ├── config.py                # Configuration management
│   ├── models.py                # Pydantic data models
│   └── validation.py            # Input validation logic
├── database/                    # Database layer
│   ├── connection.py            # Database connection management
│   └── models.py                # SQLAlchemy ORM models
├── integration/                 # System integration
│   ├── deployment_manager.py    # Deployment orchestration
│   ├── health_monitor.py        # Health checking
│   ├── service_registry.py      # Service discovery
│   └── system_integrator.py     # System integration logic
├── reporting/                   # Report generation
│   └── report_manager.py        # Report creation and formatting
├── security/                    # Security and audit
│   ├── audit_logger.py          # Audit trail logging
│   ├── chain_of_custody.py      # Evidence chain management
│   ├── encryption_manager.py    # Encryption utilities
│   └── user_tracker.py          # User activity tracking
├── upload/                      # File upload handling
│   ├── manager.py               # Upload orchestration
│   ├── progress.py              # Upload progress tracking
│   └── storage.py               # File storage management
├── utils/                       # Utility functions
│   └── crypto.py                # Cryptographic utilities
├── web/                         # Streamlit web interface
│   ├── components.py            # Reusable UI components
│   ├── run.py                   # Web app entry point
│   └── streamlit_app.py         # Main Streamlit application
└── workflow/                    # Workflow management
    └── workflow_manager.py      # Processing workflow orchestration
```

## Architecture Patterns

### Layered Architecture
- **API Layer**: FastAPI routers handle HTTP requests/responses
- **Business Logic**: Core analysis and processing modules
- **Data Layer**: SQLAlchemy models and database operations
- **Integration Layer**: External service integrations

### Module Organization
- **Single Responsibility**: Each module has a focused purpose
- **Dependency Injection**: Configuration and dependencies injected via settings
- **Async/Await**: Async patterns throughout for performance
- **Type Safety**: Full type hints with MyPy validation

### File Naming Conventions
- **Snake Case**: All Python files use snake_case naming
- **Descriptive Names**: File names clearly indicate functionality
- **Module Grouping**: Related functionality grouped in packages
- **Test Mirroring**: Test files mirror source structure with `test_` prefix

## Configuration Structure

### Environment Files
- `.env.example`: Template for environment variables
- `.env`: Local development configuration (gitignored)
- `docker-compose.yml`: Container orchestration
- `pyproject.toml`: Python package configuration

### Deployment Files
```
k8s/                            # Kubernetes manifests
├── namespace.yaml              # Namespace definition
├── configmap.yaml              # Configuration data
├── secrets.yaml                # Secret management
├── postgres.yaml               # Database deployment
├── redis.yaml                  # Cache deployment
├── api.yaml                    # API service deployment
├── web.yaml                    # Web interface deployment
├── worker.yaml                 # Worker deployment
├── ingress.yaml                # Ingress configuration
└── monitoring.yaml             # Monitoring setup
```

### Scripts Directory
```
scripts/                        # Deployment and utility scripts
├── deploy.py                   # Deployment automation
├── health-check.py             # Health monitoring
├── k8s-deploy.sh               # Kubernetes deployment
└── start-system.py             # System startup orchestration
```

## Testing Structure

### Test Organization
```
tests/                          # Test suite
├── conftest.py                 # Pytest configuration and fixtures
├── test_*.py                   # Unit and integration tests
└── __pycache__/                # Python bytecode cache
```

### Test Patterns
- **Fixtures**: Reusable test data in `conftest.py`
- **Property Testing**: Hypothesis for robust validation
- **Async Testing**: pytest-asyncio for async code
- **Mocking**: Isolated unit tests with mocks
- **Integration**: End-to-end testing with real services

## Data Storage Structure

### Upload Directories
```
uploads/                        # File storage
├── documents/                  # Uploaded documents
├── metadata/                   # Extracted metadata
└── temp/                       # Temporary processing files
```

### Log Structure
```
logs/                           # Application logs
└── audit/                      # Security audit logs
    └── audit.log               # Audit trail
```

## Code Organization Principles

### Import Structure
1. Standard library imports
2. Third-party imports
3. Local application imports
4. Relative imports (minimal use)

### Class Organization
- **Pydantic Models**: Data validation and serialization
- **SQLAlchemy Models**: Database entity definitions
- **Service Classes**: Business logic encapsulation
- **Router Classes**: API endpoint handlers

### Error Handling
- **Custom Exceptions**: Domain-specific error types
- **Exception Handlers**: Centralized error processing
- **Validation**: Pydantic for input validation
- **Logging**: Structured logging throughout