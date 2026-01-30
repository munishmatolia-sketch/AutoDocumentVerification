#!/usr/bin/env python3
"""Fix the document_id type issue in upload manager."""

file_path = '/app/src/document_forensics/upload/manager.py'

# Read the file
with open(file_path, 'r') as f:
    content = f.read()

# Replace the problematic line
content = content.replace(
    '"document_id": document_id,',
    '"document_id": str(document_id),'
)

# Write back
with open(file_path, 'w') as f:
    f.write(content)

print("Fixed document_id type conversion")
