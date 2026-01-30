#!/usr/bin/env python3
"""
Demo Data Generator for AI-Powered Document Forensics System
Creates realistic sample documents for video demonstration.
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

def create_demo_directory():
    """Create demo directory structure."""
    demo_dir = Path("demo_data")
    demo_dir.mkdir(exist_ok=True)
    
    subdirs = ["original_documents", "tampered_documents", "batch_samples", "reports"]
    for subdir in subdirs:
        (demo_dir / subdir).mkdir(exist_ok=True)
    
    return demo_dir

def create_legal_contract(filename, contract_date, value, signature_date, tampered=False):
    """Create a realistic legal contract document."""
    
    # Simulate tampering by changing dates/values
    display_date = contract_date
    display_value = value
    display_sig_date = signature_date
    
    if tampered:
        # Change contract date to previous year
        display_date = contract_date.replace(year=contract_date.year - 1)
        # Increase value
        display_value = int(value * 1.5)
    
    contract_content = f"""
PROFESSIONAL SERVICES AGREEMENT

Contract Number: PSA-{contract_date.year}-{contract_date.month:02d}{contract_date.day:02d}
Contract Date: {display_date.strftime('%B %d, %Y')}

PARTIES:
Client: Acme Legal Corporation
Address: 123 Business District, Legal City, LC 12345
Phone: (555) 123-4567

Service Provider: Document Analysis Services LLC  
Address: 456 Forensics Avenue, Expert Town, ET 67890
Phone: (555) 987-6543

SCOPE OF SERVICES:
The Service Provider agrees to perform comprehensive document forensics 
and verification services for the Client, including but not limited to:

1. Digital document authenticity verification
2. Tampering detection and analysis
3. Metadata extraction and examination
4. Expert witness testimony preparation
5. Forensic report generation

CONTRACT TERMS:
Service Period: {contract_date.strftime('%B %d, %Y')} to {(contract_date + timedelta(days=365)).strftime('%B %d, %Y')}
Total Contract Value: ${display_value:,}.00
Payment Terms: Net 30 days
Deliverables: Monthly forensic analysis reports

SPECIAL PROVISIONS:
- All analysis must meet Daubert standard requirements
- Chain of custody must be maintained for all evidence
- Reports must be suitable for expert witness testimony
- 99% accuracy guarantee on tampering detection

SIGNATURES:

Client Representative: _________________________ Date: {display_sig_date.strftime('%B %d, %Y')}
John Smith, Legal Director
Acme Legal Corporation

Service Provider: _____________________________ Date: {display_sig_date.strftime('%B %d, %Y')}
Dr. Sarah Johnson, Chief Forensics Officer
Document Analysis Services LLC

WITNESS: _____________________________________ Date: {display_sig_date.strftime('%B %d, %Y')}
Michael Brown, Notary Public
License #: NP-2026-789

This contract has been reviewed and approved by legal counsel.
Document Hash: {hashlib.sha256(str(display_value).encode()).hexdigest()[:16]}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(contract_content)
    
    return contract_content

def create_certificate(filename, issue_date, cert_number, tampered=False):
    """Create a professional certificate document."""
    
    display_date = issue_date
    display_number = cert_number
    
    if tampered:
        # Change issue date
        display_date = issue_date + timedelta(days=30)
        # Change certificate number
        display_number = f"{cert_number[:-3]}999"
    
    certificate_content = f"""
═══════════════════════════════════════════════════════════════
                    CERTIFICATE OF AUTHENTICITY
═══════════════════════════════════════════════════════════════

Certificate Number: {display_number}
Issue Date: {display_date.strftime('%B %d, %Y')}

This is to certify that the document analysis performed by the
AI-Powered Document Forensics & Verification System has been
conducted in accordance with established forensic standards.

DOCUMENT DETAILS:
Subject Document: Legal Services Agreement PSA-2026-0115
Analysis Date: {issue_date.strftime('%B %d, %Y')}
Analysis Method: Multi-Modal AI Analysis
Confidence Level: 99.4%

FINDINGS:
✓ Document integrity verified
✓ Metadata consistency confirmed  
✓ No tampering indicators detected
✓ Chain of custody maintained
✓ Legal admissibility standards met

CERTIFICATION:
This analysis meets the requirements of:
- Federal Rules of Evidence 702
- Daubert Standard for Scientific Evidence
- ISO/IEC 27037:2012 Digital Evidence Guidelines

Certified by: AI Forensics System v1.0
Digital Signature: {hashlib.sha256(display_number.encode()).hexdigest()[:32]}
Verification Code: {hashlib.md5(f"{display_date}{display_number}".encode()).hexdigest()[:8].upper()}

═══════════════════════════════════════════════════════════════
This certificate is valid only with accompanying forensic report.
For verification, visit: https://forensics.example.com/verify
═══════════════════════════════════════════════════════════════
"""
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(certificate_content)
    
    return certificate_content

def create_batch_samples(demo_dir):
    """Create multiple documents for batch processing demo."""
    batch_dir = demo_dir / "batch_samples"
    
    documents = []
    base_date = datetime(2026, 1, 15)
    
    for i in range(5):
        doc_date = base_date + timedelta(days=i*7)
        
        # Mix of authentic and tampered documents
        is_tampered = i in [1, 3]  # Documents 2 and 4 are tampered
        
        if i < 3:
            # Create contracts
            filename = batch_dir / f"contract_{i+1:02d}.txt"
            create_legal_contract(
                filename, 
                doc_date, 
                50000 + i*10000, 
                doc_date + timedelta(days=1),
                tampered=is_tampered
            )
            doc_type = "contract"
        else:
            # Create certificates
            filename = batch_dir / f"certificate_{i+1:02d}.txt"
            create_certificate(
                filename,
                doc_date,
                f"CERT-2026-{i+1:03d}",
                tampered=is_tampered
            )
            doc_type = "certificate"
        
        documents.append({
            "filename": filename.name,
            "type": doc_type,
            "date": doc_date.isoformat(),
            "tampered": is_tampered,
            "expected_confidence": 95 if is_tampered else 98
        })
    
    # Create batch manifest
    manifest = {
        "batch_id": "DEMO-BATCH-2026-001",
        "created": datetime.now().isoformat(),
        "total_documents": len(documents),
        "documents": documents
    }
    
    with open(batch_dir / "batch_manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return documents

def create_sample_reports(demo_dir):
    """Create sample forensic reports."""
    reports_dir = demo_dir / "reports"
    
    # Executive Summary Report
    exec_summary = """
EXECUTIVE SUMMARY - FORENSIC ANALYSIS REPORT

Document ID: DOC-2026-001
Analysis Date: January 17, 2026
Analyst: AI Forensics System v1.0

CASE OVERVIEW:
Analysis of legal services agreement for potential tampering or modification.
Client requested verification due to discrepancies in contract terms.

KEY FINDINGS:
• HIGH CONFIDENCE tampering detected (94.2%)
• Multiple indicators suggest document modification
• Date field shows font inconsistency
• Metadata reveals timestamp discrepancies
• Value field exhibits pixel-level anomalies

EVIDENCE SUMMARY:
1. Font Analysis: Contract date uses different typeface than body text
2. Metadata Examination: Creation timestamp predates claimed contract date
3. Pixel Analysis: Statistical anomalies in modified regions
4. Comparison Analysis: Deviations from standard contract template

LEGAL IMPLICATIONS:
This document should not be considered authentic in its current form.
Recommend further investigation and comparison with original source.

EXPERT TESTIMONY READINESS:
This analysis meets Daubert standard requirements and is suitable
for expert witness testimony in legal proceedings.

Prepared by: Dr. Sarah Johnson, Chief Forensics Officer
Certification: Board Certified Digital Forensics Examiner
"""
    
    with open(reports_dir / "executive_summary.txt", 'w', encoding='utf-8') as f:
        f.write(exec_summary)
    
    # Technical Report
    technical_report = """
TECHNICAL FORENSIC ANALYSIS REPORT

METHODOLOGY:
Multi-modal analysis combining:
- Computer vision algorithms for pixel-level examination
- Natural language processing for text consistency
- Statistical analysis for anomaly detection
- Metadata extraction and timeline analysis

DETAILED FINDINGS:

1. FONT ANALYSIS:
   - Body text: Times New Roman, 12pt
   - Contract date: Arial, 12pt (INCONSISTENT)
   - Confidence: 97.3%

2. METADATA EXAMINATION:
   - File creation: 2026-01-10 14:23:15 UTC
   - Last modified: 2026-01-15 09:45:32 UTC
   - Contract date claim: 2025-01-15 (TEMPORAL INCONSISTENCY)

3. PIXEL-LEVEL ANALYSIS:
   - Compression artifacts around date field
   - Color histogram anomalies in modified regions
   - Edge detection reveals insertion boundaries

4. STATISTICAL VALIDATION:
   - Chi-square test: p < 0.001 (significant)
   - Benford's law analysis: Deviation detected
   - Frequency analysis: Anomalous patterns

CONFIDENCE METRICS:
Overall Tampering Confidence: 94.2%
- Font inconsistency: 97.3%
- Metadata discrepancy: 91.8%
- Pixel anomalies: 89.7%
- Statistical tests: 96.1%

CHAIN OF CUSTODY:
Document received: 2026-01-17 08:30:00 UTC
Analysis started: 2026-01-17 08:35:15 UTC
Analysis completed: 2026-01-17 08:47:23 UTC
Report generated: 2026-01-17 09:15:00 UTC

All procedures followed ISO/IEC 27037:2012 guidelines.
"""
    
    with open(reports_dir / "technical_analysis.txt", 'w', encoding='utf-8') as f:
        f.write(technical_report)

def create_api_examples(demo_dir):
    """Create API request/response examples for demo."""
    api_examples = {
        "document_upload": {
            "request": {
                "method": "POST",
                "url": "/api/v1/documents/upload",
                "headers": {
                    "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "Content-Type": "multipart/form-data"
                },
                "body": {
                    "file": "contract_tampered.txt",
                    "description": "Legal services agreement for verification",
                    "priority": 5,
                    "encrypt": True
                }
            },
            "response": {
                "success": True,
                "document_id": "doc_123456789",
                "message": "Document uploaded successfully",
                "hash": "a1b2c3d4e5f6...",
                "size_bytes": 2048
            }
        },
        "analysis_request": {
            "request": {
                "method": "POST", 
                "url": "/api/v1/analysis/analyze",
                "body": {
                    "document_id": "doc_123456789",
                    "include_metadata": True,
                    "include_tampering": True,
                    "include_authenticity": True,
                    "priority": 5
                }
            },
            "response": {
                "analysis_id": "analysis_987654321",
                "status": "processing",
                "estimated_completion": "2026-01-17T09:05:00Z",
                "progress_url": "/api/v1/analysis/analysis_987654321/status"
            }
        },
        "batch_processing": {
            "request": {
                "method": "POST",
                "url": "/api/v1/batch/process", 
                "body": {
                    "document_ids": ["doc_001", "doc_002", "doc_003", "doc_004", "doc_005"],
                    "priority": "high",
                    "webhook_url": "https://client.example.com/webhook/forensics",
                    "notification_email": "analyst@example.com"
                }
            },
            "response": {
                "batch_id": "batch_456789123",
                "status": "queued",
                "total_documents": 5,
                "estimated_completion": "2026-01-17T09:15:00Z",
                "status_url": "/api/v1/batch/batch_456789123/status"
            }
        }
    }
    
    with open(demo_dir / "api_examples.json", 'w') as f:
        json.dump(api_examples, f, indent=2)

def main():
    """Generate all demo data."""
    print("🎬 Creating demo data for AI-Powered Document Forensics System...")
    
    # Create directory structure
    demo_dir = create_demo_directory()
    print(f"✅ Created demo directory: {demo_dir}")
    
    # Create original documents
    base_date = datetime(2026, 1, 15)
    
    # Original contract
    original_contract = demo_dir / "original_documents" / "legal_contract_original.txt"
    create_legal_contract(original_contract, base_date, 50000, base_date + timedelta(days=1), tampered=False)
    print(f"✅ Created original contract: {original_contract}")
    
    # Tampered contract
    tampered_contract = demo_dir / "tampered_documents" / "legal_contract_tampered.txt"
    create_legal_contract(tampered_contract, base_date, 50000, base_date + timedelta(days=1), tampered=True)
    print(f"✅ Created tampered contract: {tampered_contract}")
    
    # Original certificate
    original_cert = demo_dir / "original_documents" / "authenticity_certificate_original.txt"
    create_certificate(original_cert, base_date, "CERT-2026-001", tampered=False)
    print(f"✅ Created original certificate: {original_cert}")
    
    # Tampered certificate
    tampered_cert = demo_dir / "tampered_documents" / "authenticity_certificate_tampered.txt"
    create_certificate(tampered_cert, base_date, "CERT-2026-001", tampered=True)
    print(f"✅ Created tampered certificate: {tampered_cert}")
    
    # Batch processing samples
    batch_docs = create_batch_samples(demo_dir)
    print(f"✅ Created {len(batch_docs)} batch processing samples")
    
    # Sample reports
    create_sample_reports(demo_dir)
    print("✅ Created sample forensic reports")
    
    # API examples
    create_api_examples(demo_dir)
    print("✅ Created API request/response examples")
    
    print("\n🎉 Demo data creation complete!")
    print(f"\nDemo files available in: {demo_dir}")
    print("\nFile structure:")
    print("├── original_documents/")
    print("│   ├── legal_contract_original.txt")
    print("│   └── authenticity_certificate_original.txt")
    print("├── tampered_documents/")
    print("│   ├── legal_contract_tampered.txt")
    print("│   └── authenticity_certificate_tampered.txt")
    print("├── batch_samples/")
    print("│   ├── contract_01.txt through contract_03.txt")
    print("│   ├── certificate_04.txt through certificate_05.txt")
    print("│   └── batch_manifest.json")
    print("├── reports/")
    print("│   ├── executive_summary.txt")
    print("│   └── technical_analysis.txt")
    print("└── api_examples.json")
    
    print("\n📋 Next steps:")
    print("1. Run: python demo_setup.py")
    print("2. Start screen recording software")
    print("3. Follow demo_recording_guide.md")
    print("4. Use demo_storyboard.md for visual guidance")

if __name__ == "__main__":
    main()