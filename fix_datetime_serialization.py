"""Fix datetime serialization in analysis router."""

import sys

# Read the file
with open('src/document_forensics/api/routers/analysis.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section where results are stored
old_code = '''            # Save results to database
            result_record = AnalysisResult(
                document_id=doc_id,
                analysis_type="full",
                results=analysis_results.model_dump() if hasattr(analysis_results, 'model_dump') else {},
                confidence_score=analysis_results.confidence_score if hasattr(analysis_results, 'confidence_score') else None,
                risk_level=analysis_results.overall_risk_assessment.value if hasattr(analysis_results, 'overall_risk_assessment') else None,
                metadata_analysis=analysis_results.metadata_analysis.model_dump() if hasattr(analysis_results, 'metadata_analysis') and analysis_results.metadata_analysis else None,
                tampering_analysis=analysis_results.tampering_analysis.model_dump() if hasattr(analysis_results, 'tampering_analysis') and analysis_results.tampering_analysis else None,
                authenticity_analysis=analysis_results.authenticity_analysis.model_dump() if hasattr(analysis_results, 'authenticity_analysis') and analysis_results.authenticity_analysis else None
            )'''

new_code = '''            # Save results to database
            # Convert Pydantic models to dicts with datetime serialization
            import json
            from datetime import datetime
            
            def serialize_for_json(obj):
                """Convert Pydantic model to JSON-serializable dict."""
                if hasattr(obj, 'model_dump'):
                    data = obj.model_dump()
                else:
                    data = obj if isinstance(obj, dict) else {}
                
                # Convert datetime objects to ISO format strings
                def convert_datetimes(d):
                    if isinstance(d, dict):
                        return {k: convert_datetimes(v) for k, v in d.items()}
                    elif isinstance(d, list):
                        return [convert_datetimes(item) for item in d]
                    elif isinstance(d, datetime):
                        return d.isoformat()
                    else:
                        return d
                
                return convert_datetimes(data)
            
            result_record = AnalysisResult(
                document_id=doc_id,
                analysis_type="full",
                results=serialize_for_json(analysis_results) if hasattr(analysis_results, 'model_dump') else {},
                confidence_score=analysis_results.confidence_score if hasattr(analysis_results, 'confidence_score') else None,
                risk_level=analysis_results.overall_risk_assessment.value if hasattr(analysis_results, 'overall_risk_assessment') else None,
                metadata_analysis=serialize_for_json(analysis_results.metadata_analysis) if hasattr(analysis_results, 'metadata_analysis') and analysis_results.metadata_analysis else None,
                tampering_analysis=serialize_for_json(analysis_results.tampering_analysis) if hasattr(analysis_results, 'tampering_analysis') and analysis_results.tampering_analysis else None,
                authenticity_analysis=serialize_for_json(analysis_results.authenticity_analysis) if hasattr(analysis_results, 'authenticity_analysis') and analysis_results.authenticity_analysis else None
            )'''

# Replace the code
if old_code in content:
    content = content.replace(old_code, new_code)
    print("✓ Fixed datetime serialization in analysis router")
else:
    print("✗ Could not find the code to replace")
    sys.exit(1)

# Write the file back
with open('src/document_forensics/api/routers/analysis.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ File updated successfully")
