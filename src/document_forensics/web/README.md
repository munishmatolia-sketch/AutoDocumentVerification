# Document Forensics Web Interface

A Streamlit-based web interface for the Document Forensics & Verification System.

## Features

- **Document Upload & Analysis**: Upload documents and start forensic analysis
- **Real-time Progress Tracking**: Monitor analysis progress with live updates
- **Interactive Results Display**: View analysis results with visual evidence
- **Batch Processing**: Upload and process multiple documents simultaneously
- **Report Generation**: Download comprehensive forensic reports in multiple formats
- **Document Library**: Manage and browse analyzed documents
- **Visual Evidence Display**: View tampering heatmaps and pixel analysis

## Getting Started

### Prerequisites

- Python 3.9+
- All project dependencies installed (`pip install -r requirements.txt`)
- Document Forensics API server running

### Running the Web Interface

1. **Using the entry point script:**
   ```bash
   forensics-web
   ```

2. **Using Python module:**
   ```bash
   python -m streamlit run src/document_forensics/web/streamlit_app.py
   ```

3. **Direct execution:**
   ```bash
   python src/document_forensics/web/run.py
   ```

The web interface will be available at `http://localhost:8501`

## Usage Guide

### 1. Authentication
- Enter your username and password in the sidebar
- Click "Login" to authenticate with the API

### 2. Document Upload & Analysis
- Navigate to "Upload & Analyze" page
- Choose a document file (PDF, images, Word docs, Excel files, text files)
- Add optional metadata (description, tags, priority)
- Click "Upload & Start Analysis"
- Monitor real-time progress updates

### 3. Viewing Results
- Analysis results are displayed in multiple tabs:
  - **Summary**: Key findings and overall assessment
  - **Tampering**: Detected modifications and inconsistencies
  - **Authenticity**: Authenticity scores and validation results
  - **Visual Evidence**: Heatmaps and annotated visualizations

### 4. Batch Processing
- Navigate to "Batch Processing" page
- Upload multiple documents at once
- Monitor batch progress and individual file status
- View summary statistics

### 5. Document Library
- Browse all uploaded and analyzed documents
- Filter by status, risk level, or search terms
- View document details and download reports

### 6. Reports & Analytics
- Generate comprehensive reports in PDF, JSON, or XML format
- View analytics dashboard with processing statistics
- Download visual evidence and supporting materials

## Configuration

The web interface can be configured through environment variables or the settings module:

- `API_BASE_URL`: Base URL for the Document Forensics API (default: `http://localhost:8000/api/v1`)
- `STREAMLIT_SERVER_PORT`: Port for the web interface (default: 8501)
- `STREAMLIT_SERVER_ADDRESS`: Address to bind to (default: 0.0.0.0)

## Components

### Core Components
- `DocumentForensicsWebApp`: Main application class
- `VisualEvidenceRenderer`: Renders visual evidence with annotations
- `MetricsDisplay`: Displays metrics and statistics
- `DocumentLibraryTable`: Document management interface
- `BatchProgressDisplay`: Batch processing progress tracking
- `ReportGenerator`: Report generation utilities

### Pages
- **Upload & Analyze**: Single document processing
- **Document Library**: Document management and browsing
- **Batch Processing**: Multi-document processing
- **Reports**: Analytics and report generation

## API Integration

The web interface communicates with the Document Forensics API through REST endpoints:

- `POST /api/v1/documents/upload`: Upload documents
- `POST /api/v1/analysis/start`: Start analysis
- `GET /api/v1/documents/{id}/status`: Check processing status
- `GET /api/v1/analysis/{id}`: Get analysis results
- `GET /api/v1/reports/{id}`: Download reports
- `POST /api/v1/batch/upload`: Batch upload
- `GET /api/v1/batch/{id}/status`: Batch status

## Troubleshooting

### Common Issues

1. **Connection Error**: Ensure the API server is running and accessible
2. **Upload Failures**: Check file format and size limits
3. **Authentication Issues**: Verify credentials and token validity
4. **Slow Performance**: Consider reducing file sizes or batch sizes

### Debug Mode

Enable debug mode by setting the environment variable:
```bash
STREAMLIT_DEBUG=true
```

## Development

### Adding New Features

1. Create new components in `src/document_forensics/web/components.py`
2. Add new pages to the main application class
3. Update the navigation in `render_sidebar()`
4. Add corresponding tests in `tests/test_web_interface.py`

### Testing

Run the web interface tests:
```bash
python -m pytest tests/test_web_interface.py -v
```

## Security Considerations

- Authentication tokens are stored in session state
- File uploads are validated for type and size
- API communications use HTTPS in production
- Sensitive data is not logged or cached
- User sessions are isolated and secure