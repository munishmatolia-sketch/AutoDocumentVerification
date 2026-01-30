# Document Forensics CLI

A command-line interface for the Document Forensics & Verification System built with Click and Rich for enhanced user experience.

## Features

- **Single Document Analysis**: Upload and analyze individual documents
- **Batch Processing**: Process multiple documents from directories
- **Real-time Progress Tracking**: Monitor analysis progress with progress bars
- **Rich Output Formatting**: Colorized and formatted output for better readability
- **Report Downloads**: Download analysis reports in multiple formats
- **Status Monitoring**: Check document and batch processing status
- **Comprehensive Error Handling**: Clear error messages and recovery suggestions

## Installation

The CLI is installed automatically with the document forensics package:

```bash
pip install -e .
```

This creates the `forensics` command-line tool.

## Usage

### Basic Commands

#### Analyze a Single Document

```bash
# Basic analysis
forensics analyze document.pdf

# With metadata and options
forensics analyze document.pdf \
  --description "Contract analysis" \
  --tags legal,contract \
  --priority 8 \
  --wait

# With report download
forensics analyze document.pdf \
  --wait \
  --output report.pdf \
  --format pdf
```

#### Check Document Status

```bash
forensics status <document-id>
```

#### Get Analysis Results

```bash
# Display results in terminal
forensics results <document-id>

# Save results to file
forensics results <document-id> --output results.json --format json
```

#### Batch Processing

```bash
# Process all PDFs in a directory
forensics batch /path/to/documents --pattern "*.pdf"

# With options and monitoring
forensics batch /path/to/documents \
  --pattern "*.pdf" \
  --description "Legal document batch" \
  --priority 7 \
  --wait \
  --max-files 50
```

#### Check Batch Status

```bash
forensics batch-status <batch-id>
```

#### Download Reports

```bash
# Download PDF report
forensics download <document-id> report.pdf --format pdf

# Download JSON data
forensics download <document-id> data.json --format json
```

### Command Reference

#### Global Options

- `--api-url`: API base URL (default: http://localhost:8000/api/v1)
- `--token`: Authentication token for API access

#### `analyze` Command

Analyze a single document with optional metadata and processing options.

**Arguments:**
- `file_path`: Path to the document file (required)

**Options:**
- `--description, -d`: Document description
- `--tags, -t`: Document tags (can be used multiple times)
- `--priority, -p`: Processing priority (1-10, default: 5)
- `--no-encrypt`: Disable encryption for stored document
- `--wait, -w`: Wait for analysis completion
- `--output, -o`: Output file for report download
- `--format, -f`: Report format (pdf, json, xml)

**Examples:**
```bash
forensics analyze contract.pdf -d "Legal contract" -t legal -t contract -p 8 -w
forensics analyze image.jpg --wait --output analysis.pdf --format pdf
```

#### `status` Command

Check the processing status of a document.

**Arguments:**
- `document_id`: ID of the document to check

**Example:**
```bash
forensics status doc-123-456-789
```

#### `results` Command

Retrieve and display analysis results for a document.

**Arguments:**
- `document_id`: ID of the document

**Options:**
- `--output, -o`: Save results to file
- `--format, -f`: Output format (json, pdf, xml)

**Examples:**
```bash
forensics results doc-123-456-789
forensics results doc-123-456-789 -o report.json -f json
```

#### `batch` Command

Process multiple documents from a directory.

**Arguments:**
- `directory`: Directory containing documents to process

**Options:**
- `--pattern, -p`: File pattern to match (default: *)
- `--description, -d`: Batch description
- `--priority`: Processing priority (1-10, default: 5)
- `--wait, -w`: Wait for batch completion
- `--max-files`: Maximum number of files to process (default: 100)

**Examples:**
```bash
forensics batch /documents --pattern "*.pdf" -d "Legal documents" --wait
forensics batch /images --pattern "*.{jpg,png}" --max-files 20
```

#### `batch-status` Command

Check the status of a batch processing operation.

**Arguments:**
- `batch_id`: ID of the batch to check

**Example:**
```bash
forensics batch-status batch-123-456-789
```

#### `download` Command

Download analysis reports in various formats.

**Arguments:**
- `document_id`: ID of the document
- `output_path`: Path where to save the report

**Options:**
- `--format, -f`: Report format (pdf, json, xml, default: pdf)

**Examples:**
```bash
forensics download doc-123-456-789 report.pdf
forensics download doc-123-456-789 data.json --format json
```

## Output Formats

### Analysis Results Display

The CLI provides rich, colorized output for analysis results:

```
🔍 ANALYSIS RESULTS
============================================================
Summary
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric             ┃ Value                                  ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Overall Risk       │ MEDIUM                                 │
│ Confidence Score   │ 85.0%                                  │
│ Processing Time    │ 2.50s                                  │
└────────────────────┴────────────────────────────────────────┘

🔍 TAMPERING ANALYSIS
⚠️  2 potential modifications detected:
  1. Text modification detected (Confidence: 80.0%)
  2. Image manipulation found (Confidence: 90.0%)

✅ AUTHENTICITY ANALYSIS
⚠️  Moderate authenticity confidence (60.0%)

📊 VISUAL EVIDENCE (2 items)
  1. tampering_heatmap: Heatmap analysis
  2. pixel_analysis: Pixel inconsistencies
```

### Batch Status Display

```
📦 BATCH STATUS
==================================================
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric             ┃ Value                                  ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Status             │ COMPLETED                              │
│ Progress           │ 100.0%                                 │
│ Total Documents    │ 10                                     │
│ Processed          │ 9                                      │
│ Failed             │ 1                                      │
│ Success Rate       │ 88.9%                                  │
└────────────────────┴────────────────────────────────────────┘
```

## Configuration

### Environment Variables

- `FORENSICS_API_URL`: Default API base URL
- `FORENSICS_AUTH_TOKEN`: Default authentication token
- `FORENSICS_DEFAULT_FORMAT`: Default report format

### Configuration File

Create a configuration file at `~/.forensics/config.json`:

```json
{
  "api_url": "https://api.forensics.example.com/v1",
  "auth_token": "your-auth-token",
  "default_format": "pdf",
  "default_priority": 5
}
```

## Authentication

### Token-based Authentication

```bash
# Set token via command line
forensics --token your-auth-token analyze document.pdf

# Set token via environment variable
export FORENSICS_AUTH_TOKEN=your-auth-token
forensics analyze document.pdf
```

### Interactive Authentication

```bash
# The CLI will prompt for credentials if needed
forensics analyze document.pdf
# Username: your-username
# Password: [hidden]
```

## Error Handling

The CLI provides clear error messages and suggestions:

```bash
❌ Upload failed: Invalid file format
💡 Supported formats: PDF, JPG, PNG, TIFF, DOCX, XLSX, TXT

❌ Document not found: doc-invalid-id
💡 Check the document ID and try again

❌ Network error: Connection refused
💡 Ensure the API server is running at http://localhost:8000
```

## Progress Tracking

Real-time progress indicators for long-running operations:

```bash
🔄 Analyzing document... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:15
✅ Analysis completed!

📦 Processing batch... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 75% 0:02:30
🔄 Processing...
```

## Scripting and Automation

### Bash Script Example

```bash
#!/bin/bash
# Batch process all PDFs in a directory

DOCS_DIR="/path/to/documents"
OUTPUT_DIR="/path/to/reports"

# Start batch processing
BATCH_ID=$(forensics batch "$DOCS_DIR" --pattern "*.pdf" --format json | grep -o 'batch-[a-f0-9-]*')

# Wait for completion
while true; do
    STATUS=$(forensics batch-status "$BATCH_ID" --format json | jq -r '.status')
    if [ "$STATUS" = "completed" ]; then
        break
    fi
    sleep 10
done

echo "Batch processing completed: $BATCH_ID"
```

### Python Integration

```python
import subprocess
import json

def analyze_document(file_path):
    """Analyze a document using the CLI."""
    result = subprocess.run([
        'forensics', 'analyze', file_path, 
        '--wait', '--format', 'json'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        raise Exception(f"Analysis failed: {result.stderr}")

# Usage
results = analyze_document('document.pdf')
print(f"Risk level: {results['overall_risk_assessment']}")
```

## Troubleshooting

### Common Issues

1. **Command not found**: Ensure the package is installed with `pip install -e .`
2. **API connection errors**: Check the API URL and ensure the server is running
3. **Authentication failures**: Verify your token or credentials
4. **File not found**: Check file paths and permissions
5. **Timeout errors**: Increase timeout or check network connectivity

### Debug Mode

Enable verbose output for debugging:

```bash
forensics --verbose analyze document.pdf
```

### Log Files

CLI logs are written to:
- Linux/Mac: `~/.forensics/logs/cli.log`
- Windows: `%USERPROFILE%\.forensics\logs\cli.log`

## Development

### Adding New Commands

1. Add command function to `src/document_forensics/cli/main.py`
2. Use Click decorators for options and arguments
3. Add corresponding tests in `tests/test_cli_interface.py`
4. Update this documentation

### Testing

Run CLI tests:
```bash
python -m pytest tests/test_cli_interface.py -v
```

### Building

Build the CLI for distribution:
```bash
python -m build
pip install dist/document_forensics-*.whl
```