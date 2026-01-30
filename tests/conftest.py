"""Pytest configuration and fixtures for document forensics tests."""

import os
import tempfile
import pytest
from typing import Generator


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Generate sample PDF content for testing."""
    # Simple PDF content for testing
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
300
%%EOF"""


@pytest.fixture
def sample_image_content() -> bytes:
    """Generate sample image content for testing."""
    # Simple 1x1 PNG image
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a4944415478da6300010000050001d72db3520000000049454e44ae"
        "426082"
    )


@pytest.fixture
def sample_text_content() -> str:
    """Generate sample text content for testing."""
    return "This is a sample text document for testing purposes."