#!/usr/bin/env python3
"""
Demo Setup Script for AI-Powered Document Forensics System
Prepares the system for video demonstration recording.
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def print_status(message, status="INFO"):
    """Print colored status messages."""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m", 
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}{status}: {message}{colors['RESET']}")

def check_prerequisites():
    """Check if required tools are installed."""
    print_status("Checking prerequisites...")
    
    required_tools = ["docker", "docker-compose", "python"]
    missing_tools = []
    
    for tool in required_tools:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
            print_status(f"✅ {tool} is installed", "SUCCESS")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(tool)
            print_status(f"❌ {tool} is not installed", "ERROR")
    
    if missing_tools:
        print_status(f"Please install missing tools: {', '.join(missing_tools)}", "ERROR")
        return False
    
    return True

def create_demo_documents():
    """Create sample documents for demonstration."""
    print_status("Creating demo documents...")
    
    demo_dir = Path("demo_documents")
    demo_dir.mkdir(exist_ok=True)
    
    # Create original document content
    original_content = """
LEGAL CONTRACT AGREEMENT

Contract Date: January 15, 2026
Contract Number: LC-2026-001

PARTIES:
- Client: Acme Corporation
- Provider: Legal Services LLC

TERMS:
This agreement establishes the terms for legal document review services.
The contract period is from January 15, 2026 to December 31, 2026.

Total Contract Value: $50,000.00

SIGNATURES:
Client Representative: [Signature]
Date Signed: January 15, 2026

Provider Representative: [Signature] 
Date Signed: January 15, 2026
"""
    
    # Create tampered document content (date changed)
    tampered_content = """
LEGAL CONTRACT AGREEMENT

Contract Date: January 15, 2025
Contract Number: LC-2026-001

PARTIES:
- Client: Acme Corporation
- Provider: Legal Services LLC

TERMS:
This agreement establishes the terms for legal document review services.
The contract period is from January 15, 2026 to December 31, 2026.

Total Contract Value: $75,000.00

SIGNATURES:
Client Representative: [Signature]
Date Signed: January 15, 2026

Provider Representative: [Signature] 
Date Signed: January 15, 2026
"""
    
    # Write demo documents
    with open(demo_dir / "original_contract.txt", "w") as f:
        f.write(original_content)
    
    with open(demo_dir / "tampered_contract.txt", "w") as f:
        f.write(tampered_content)
    
    print_status("✅ Demo documents created in demo_documents/", "SUCCESS")
    return True

def start_system():
    """Start the document forensics system."""
    print_status("Starting AI-Powered Document Forensics System...")
    
    try:
        # Start Docker Compose services
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            capture_output=True,
            text=True,
            check=True
        )
        print_status("✅ Docker services started", "SUCCESS")
        
        # Wait for services to be ready
        print_status("Waiting for services to initialize...")
        time.sleep(30)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print_status(f"Failed to start services: {e}", "ERROR")
        print_status(f"Error output: {e.stderr}", "ERROR")
        return False

def check_service_health():
    """Check if all services are healthy and responding."""
    print_status("Checking service health...")
    
    services = {
        "API Server": "http://localhost:8000/health",
        "Web Interface": "http://localhost:8501",
        "Flower (Celery)": "http://localhost:5555"
    }
    
    all_healthy = True
    
    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print_status(f"✅ {service_name} is healthy", "SUCCESS")
            else:
                print_status(f"⚠️ {service_name} returned status {response.status_code}", "WARNING")
                all_healthy = False
        except requests.exceptions.RequestException as e:
            print_status(f"❌ {service_name} is not responding: {e}", "ERROR")
            all_healthy = False
    
    return all_healthy

def create_demo_script():
    """Create a demo script with step-by-step instructions."""
    demo_script = """
# AI-Powered Document Forensics - Demo Recording Script

## Pre-Recording Checklist
- [ ] System is running (all services healthy)
- [ ] Demo documents are prepared
- [ ] Screen recording software is ready
- [ ] Audio recording is configured

## Recording Sequence

### 1. System Overview (30 seconds)
- Open browser to http://localhost:8000/docs
- Show API documentation with all endpoints
- Highlight key features: documents, analysis, reports, webhooks

### 2. Web Interface Demo (90 seconds)
- Navigate to http://localhost:8501
- Upload demo_documents/tampered_contract.txt
- Show real-time analysis progress
- Display results with confidence scores
- Highlight tampering detection and visual evidence

### 3. Report Generation (45 seconds)
- Click "Generate Report" button
- Show report options (PDF, JSON, XML)
- Download and open generated PDF report
- Highlight expert testimony formatting

### 4. API Integration (30 seconds)
- Return to http://localhost:8000/docs
- Demonstrate batch processing endpoint
- Show webhook configuration
- Execute sample API calls

### 5. Monitoring & Security (30 seconds)
- Open http://localhost:5555 (Flower)
- Show task monitoring and worker status
- Highlight security features and audit trails

## Key Points to Emphasize
- 100% test coverage and production readiness
- AI-powered multi-modal analysis
- Legal compliance and expert testimony formatting
- Real-time processing and batch capabilities
- Forensic-grade security and audit trails

## Post-Recording
- Stop services: docker-compose down
- Clean up demo files if needed
"""
    
    with open("demo_recording_guide.md", "w") as f:
        f.write(demo_script)
    
    print_status("✅ Demo recording guide created", "SUCCESS")

def main():
    """Main demo setup function."""
    print_status("🎬 AI-Powered Document Forensics Demo Setup", "INFO")
    print_status("=" * 50, "INFO")
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Create demo documents
    if not create_demo_documents():
        sys.exit(1)
    
    # Start the system
    if not start_system():
        sys.exit(1)
    
    # Check service health
    if not check_service_health():
        print_status("Some services may not be fully ready. Wait a few more minutes.", "WARNING")
    
    # Create demo script
    create_demo_script()
    
    print_status("=" * 50, "SUCCESS")
    print_status("🎉 Demo setup complete!", "SUCCESS")
    print_status("", "INFO")
    print_status("System is ready for video recording:", "INFO")
    print_status("- Web Interface: http://localhost:8501", "INFO")
    print_status("- API Docs: http://localhost:8000/docs", "INFO")
    print_status("- Monitoring: http://localhost:5555", "INFO")
    print_status("", "INFO")
    print_status("Demo documents available in: demo_documents/", "INFO")
    print_status("Recording guide: demo_recording_guide.md", "INFO")
    print_status("", "INFO")
    print_status("To stop the system: docker-compose down", "INFO")

if __name__ == "__main__":
    main()