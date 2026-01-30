"""Fix batch processing upload method call."""

import sys

def fix_batch_upload():
    """Fix the upload_document method call in batch processing."""
    file_path = "/app/src/document_forensics/web/streamlit_app.py"
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace the incorrect method call
        old_code = """                    for idx, file in enumerate(uploaded_files):
                        # Upload document
                        result = self.upload_document(file)
                        if result.get("success"):
                            doc_id = result.get("document_id")
                            document_ids.append(doc_id)
                            
                            # Start analysis for this document
                            self.start_analysis(doc_id)"""
        
        new_code = """                    for idx, file in enumerate(uploaded_files):
                        # Upload document
                        file_data = file.read()
                        result = self.upload_document_to_api(file_data, file.name)
                        if result.get("success"):
                            doc_id = result.get("document_id")
                            document_ids.append(doc_id)
                            
                            # Start analysis for this document
                            self.start_analysis(doc_id)"""
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            
            with open(file_path, 'w') as f:
                f.write(content)
            
            print("✅ Successfully fixed batch upload method call")
            return 0
        else:
            print("⚠️ Code pattern not found - may already be fixed")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(fix_batch_upload())
