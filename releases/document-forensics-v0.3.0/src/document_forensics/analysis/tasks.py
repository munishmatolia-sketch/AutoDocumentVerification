"""Celery tasks for document analysis."""

from celery import current_app as celery_app
from document_forensics.analysis.authenticity_scorer import AuthenticityScorer
from document_forensics.analysis.metadata_extractor import MetadataExtractor
from document_forensics.analysis.tampering_detector import TamperingDetector


@celery_app.task(bind=True)
def analyze_document_authenticity(self, document_path: str, document_id: str):
    """Analyze document authenticity."""
    try:
        scorer = AuthenticityScorer()
        result = scorer.calculate_authenticity_score(document_path)
        return {
            "document_id": document_id,
            "authenticity_score": result.authenticity_score,
            "confidence": result.confidence,
            "factors": result.factors,
            "status": "completed"
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def extract_document_metadata(self, document_path: str, document_id: str):
    """Extract document metadata."""
    try:
        extractor = MetadataExtractor()
        metadata = extractor.extract_metadata(document_path)
        return {
            "document_id": document_id,
            "metadata": metadata.dict(),
            "status": "completed"
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def detect_document_tampering(self, document_path: str, document_id: str):
    """Detect document tampering."""
    try:
        detector = TamperingDetector()
        result = detector.detect_tampering(document_path)
        return {
            "document_id": document_id,
            "tampering_detected": result.tampering_detected,
            "confidence": result.confidence,
            "anomalies": result.anomalies,
            "status": "completed"
        }
    except Exception as exc:
        self.retry(exc=exc, countdown=60, max_retries=3)