"""Fix datetime import issue in analysis router."""

import sys

# Read the file
with open('src/document_forensics/api/routers/analysis.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and fix the duplicate import
old_code = '''            # Save results to database
            # Convert Pydantic models to dicts with datetime serialization
            import json
            from datetime import datetime
            
            def serialize_for_json(obj):'''

new_code = '''            # Save results to database
            # Convert Pydantic models to dicts with datetime serialization
            import json
            
            def serialize_for_json(obj):'''

# Replace the code
if old_code in content:
    content = content.replace(old_code, new_code)
    print("✓ Fixed datetime import issue")
else:
    print("✗ Could not find the code to replace")
    sys.exit(1)

# Write the file back
with open('src/document_forensics/api/routers/analysis.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ File updated successfully")
