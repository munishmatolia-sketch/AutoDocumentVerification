"""Pydantic models for data validation and API serialization."""

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.types import conint, confloat, constr


class ProcessingStatus(str, Enum):
    """Document processing status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(str, Enum):
    """Supported file type enumeration."""
    PDF = "pdf"
    IMAGE = "image"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"


class RiskLevel(str, Enum):
    """Risk level enumeration for tampering analysis."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ForgeryType(str, Enum):
    """Types of forgery indicators."""
    # Word-specific
    REVISION_MANIPULATION = "revision_manipulation"
    STYLE_INCONSISTENCY = "style_inconsistency"
    FONT_MANIPULATION = "font_manipulation"
    HIDDEN_TEXT = "hidden_text"
    TRACK_CHANGES_ANOMALY = "track_changes_anomaly"
    XML_STRUCTURE_ANOMALY = "xml_structure_anomaly"
    
    # Excel-specific
    FORMULA_TAMPERING = "formula_tampering"
    VALUE_OVERRIDE = "value_override"
    HIDDEN_CONTENT = "hidden_content"
    VALIDATION_BYPASS = "validation_bypass"
    MACRO_SUSPICIOUS = "macro_suspicious"
    NUMBER_FORMAT_MANIPULATION = "number_format_manipulation"
    
    # Text-specific
    ENCODING_MANIPULATION = "encoding_manipulation"
    INVISIBLE_CHARACTERS = "invisible_characters"
    HOMOGLYPH_ATTACK = "homoglyph_attack"
    LINE_ENDING_INCONSISTENCY = "line_ending_inconsistency"
    
    # Image-specific
    CLONE_DETECTION = "clone_detection"
    NOISE_INCONSISTENCY = "noise_inconsistency"
    COMPRESSION_ANOMALY = "compression_anomaly"
    LIGHTING_INCONSISTENCY = "lighting_inconsistency"
    EDGE_INCONSISTENCY = "edge_inconsistency"
    COLOR_SPACE_ANOMALY = "color_space_anomaly"
    
    # PDF-specific
    SIGNATURE_BROKEN = "signature_broken"
    INCREMENTAL_UPDATE = "incremental_update"
    OBJECT_MANIPULATION = "object_manipulation"
    TEXT_LAYER_MISMATCH = "text_layer_mismatch"
    FORM_FIELD_TAMPERING = "form_field_tampering"
    FONT_EMBEDDING_ANOMALY = "font_embedding_anomaly"
    
    # General
    METADATA_INCONSISTENCY = "metadata_inconsistency"
    TIMESTAMP_ANOMALY = "timestamp_anomaly"
    ANALYSIS_ERROR = "analysis_error"


class DocumentType(str, Enum):
    """Document type enumeration for forgery detection."""
    WORD = "word"
    EXCEL = "excel"
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"
    UNKNOWN = "unknown"


class EvidenceType(str, Enum):
    """Visual evidence type enumeration."""
    TAMPERING_HEATMAP = "tampering_heatmap"
    PIXEL_ANALYSIS = "pixel_analysis"
    TEXT_MODIFICATION = "text_modification"
    SIGNATURE_VERIFICATION = "signature_verification"
    METADATA_VISUALIZATION = "metadata_visualization"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    PDF = "pdf"
    JSON = "json"
    XML = "xml"


# Base models for common fields
class TimestampedModel(BaseModel):
    """Base model with timestamp fields."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time: Optional[confloat(ge=0.0)] = None


class ConfidenceModel(BaseModel):
    """Base model with confidence scoring."""
    confidence_score: confloat(ge=0.0, le=1.0) = Field(..., description="Confidence score between 0 and 1")


# Document-related models
class DocumentMetadata(BaseModel):
    """Document metadata extracted from file properties."""
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    author: Optional[str] = None
    creator_software: Optional[str] = None
    file_version: Optional[str] = None
    page_count: Optional[conint(ge=0)] = None
    word_count: Optional[conint(ge=0)] = None
    character_count: Optional[conint(ge=0)] = None
    custom_properties: Dict[str, Any] = Field(default_factory=dict)


class UploadMetadata(BaseModel):
    """Metadata provided during document upload."""
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    priority: conint(ge=1, le=10) = 5
    user_id: Optional[str] = None
    batch_id: Optional[str] = None
    
    @field_validator('batch_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string if needed."""
        if v is not None and hasattr(v, '__str__'):
            return str(v)
        return v


class Document(BaseModel):
    """Document model for API and internal processing."""
    id: Optional[int] = None
    filename: constr(min_length=1, max_length=255)
    file_type: FileType
    size: conint(ge=0)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    hash: constr(min_length=64, max_length=64)
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    metadata: Optional[DocumentMetadata] = None
    upload_metadata: Optional[UploadMetadata] = None

    @field_validator('hash')
    @classmethod
    def validate_hash_format(cls, v):
        """Validate that hash is a valid SHA-256 hex string."""
        if not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('Hash must be a valid hexadecimal string')
        return v.lower()

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        """Validate filename doesn't contain dangerous characters."""
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
        if any(char in v for char in dangerous_chars):
            raise ValueError('Filename contains invalid characters')
        return v

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True


# Analysis result models
class GeoLocation(BaseModel):
    """Geographic location data from EXIF."""
    latitude: confloat(ge=-90.0, le=90.0)
    longitude: confloat(ge=-180.0, le=180.0)
    altitude: Optional[float] = None
    accuracy: Optional[confloat(ge=0.0)] = None


class DeviceFingerprint(BaseModel):
    """Device fingerprint information."""
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    lens_info: Optional[str] = None
    software_version: Optional[str] = None
    unique_identifiers: Dict[str, str] = Field(default_factory=dict)


class SoftwareSignature(BaseModel):
    """Software signature detection result."""
    software_name: str
    version: Optional[str] = None
    confidence: confloat(ge=0.0, le=1.0)
    signature_type: str
    detection_method: str


class TimestampConsistency(BaseModel):
    """Timestamp consistency analysis result."""
    is_consistent: bool
    anomalies: List[str] = Field(default_factory=list)
    chronological_order: bool
    time_gaps: List[Dict[str, Any]] = Field(default_factory=list)


class MetadataAnomaly(BaseModel):
    """Metadata anomaly detection result."""
    anomaly_type: str
    description: str
    severity: RiskLevel
    affected_fields: List[str]
    confidence: confloat(ge=0.0, le=1.0)


class MetadataAnalysis(TimestampedModel):
    """Metadata analysis results."""
    document_id: int
    extracted_metadata: Dict[str, Any]
    timestamp_consistency: Optional[TimestampConsistency] = None
    software_signatures: List[SoftwareSignature] = Field(default_factory=list)
    anomalies: List[MetadataAnomaly] = Field(default_factory=list)
    geo_location: Optional[GeoLocation] = None
    device_fingerprint: Optional[DeviceFingerprint] = None


# Tampering detection models
class PixelInconsistency(BaseModel):
    """Pixel-level inconsistency detection result."""
    region_coordinates: Dict[str, int]  # x, y, width, height
    inconsistency_type: str
    confidence: confloat(ge=0.0, le=1.0)
    analysis_method: str


class TextModification(BaseModel):
    """Text modification detection result."""
    location: Dict[str, Any]
    modification_type: str
    original_text: Optional[str] = None
    modified_text: Optional[str] = None
    confidence: confloat(ge=0.0, le=1.0)


class SignatureBreak(BaseModel):
    """Digital signature break detection result."""
    signature_id: str
    break_type: str
    timestamp: datetime
    affected_content: str
    verification_status: bool


class CompressionAnomaly(BaseModel):
    """Compression anomaly detection result."""
    region: Dict[str, int]
    anomaly_type: str
    expected_compression: float
    actual_compression: float
    confidence: confloat(ge=0.0, le=1.0)


class Modification(BaseModel):
    """General modification detection result."""
    modification_id: str = Field(default_factory=lambda: str(int(datetime.utcnow().timestamp() * 1000000)))
    type: str
    location: Dict[str, Any]
    description: str
    confidence: confloat(ge=0.0, le=1.0)
    evidence_data: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('modification_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string if needed."""
        if v is not None and hasattr(v, '__str__'):
            return str(v)
        return v


class TamperingAnalysis(TimestampedModel, ConfidenceModel):
    """Tampering analysis results."""
    document_id: int
    overall_risk: RiskLevel
    detected_modifications: List[Modification] = Field(default_factory=list)
    pixel_inconsistencies: List[PixelInconsistency] = Field(default_factory=list)
    text_modifications: List[TextModification] = Field(default_factory=list)
    signature_breaks: List[SignatureBreak] = Field(default_factory=list)
    compression_anomalies: List[CompressionAnomaly] = Field(default_factory=list)
    forgery_analysis: Optional[Any] = None  # Will be ForgeryAnalysis, defined later


# Authenticity scoring models
class ComparisonResult(BaseModel):
    """Comparison against reference samples result."""
    reference_id: str
    similarity_score: confloat(ge=0.0, le=1.0)
    matching_features: List[str]
    differing_features: List[str]
    confidence: confloat(ge=0.0, le=1.0)


class StructureValidation(BaseModel):
    """File structure validation result."""
    is_valid: bool
    format_compliance: confloat(ge=0.0, le=1.0)
    violations: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class ObjectAssessment(BaseModel):
    """Embedded object assessment result."""
    object_id: str
    object_type: str
    integrity_score: confloat(ge=0.0, le=1.0)
    authenticity_indicators: List[str]
    anomalies: List[str] = Field(default_factory=list)


class AuthenticityScore(BaseModel):
    """Authenticity scoring result."""
    overall_score: confloat(ge=0.0, le=1.0)
    confidence_level: confloat(ge=0.0, le=1.0)
    contributing_factors: Dict[str, float]
    risk_assessment: RiskLevel


class AuthenticityAnalysis(TimestampedModel):
    """Authenticity analysis results."""
    document_id: int
    authenticity_score: AuthenticityScore
    comparison_results: List[ComparisonResult] = Field(default_factory=list)
    structure_validation: Optional[StructureValidation] = None
    embedded_objects_assessment: List[ObjectAssessment] = Field(default_factory=list)
    forensic_indicators: Dict[str, Any] = Field(default_factory=dict)


# Visual evidence models
class Annotation(BaseModel):
    """Visual annotation for evidence."""
    annotation_id: str = Field(default_factory=lambda: str(int(datetime.utcnow().timestamp() * 1000000)))
    type: str
    coordinates: Dict[str, Union[int, float]]
    description: str
    confidence: confloat(ge=0.0, le=1.0)


class VisualEvidence(BaseModel):
    """Visual evidence model."""
    evidence_id: str = Field(default_factory=lambda: str(int(datetime.utcnow().timestamp() * 1000000)))
    type: EvidenceType
    description: str
    annotations: List[Annotation] = Field(default_factory=list)
    confidence_level: confloat(ge=0.0, le=1.0)
    analysis_method: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Comprehensive analysis results
class AnalysisResults(TimestampedModel, ConfidenceModel):
    """Comprehensive analysis results for a document."""
    document_id: int
    metadata_analysis: Optional[MetadataAnalysis] = None
    tampering_analysis: Optional[TamperingAnalysis] = None
    authenticity_analysis: Optional[AuthenticityAnalysis] = None
    visual_evidence: List[VisualEvidence] = Field(default_factory=list)
    overall_risk_assessment: RiskLevel = RiskLevel.LOW

    @model_validator(mode='after')
    def validate_analysis_completeness(self):
        """Ensure at least one analysis type is present."""
        analyses = [
            self.metadata_analysis,
            self.tampering_analysis,
            self.authenticity_analysis
        ]
        if not any(analyses):
            raise ValueError('At least one analysis result must be provided')
        return self


# Batch processing models
class BatchStatus(BaseModel):
    """Batch processing status."""
    batch_id: str
    status: ProcessingStatus
    total_documents: conint(ge=0)
    processed_documents: conint(ge=0)
    failed_documents: conint(ge=0)
    progress_percentage: confloat(ge=0.0, le=100.0)
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_details: Optional[Dict[str, Any]] = None
    
    @field_validator('batch_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        """Convert UUID to string if needed."""
        if v is not None and hasattr(v, '__str__'):
            return str(v)
        return v

    @field_validator('processed_documents')
    @classmethod
    def validate_processed_count(cls, v, info):
        """Ensure processed count doesn't exceed total."""
        if info.data and 'total_documents' in info.data:
            total = info.data['total_documents']
            if v > total:
                raise ValueError('Processed documents cannot exceed total documents')
        return v

    @field_validator('failed_documents')
    @classmethod
    def validate_failed_count(cls, v, info):
        """Ensure failed count doesn't exceed total."""
        if info.data and 'total_documents' in info.data:
            total = info.data['total_documents']
            if v > total:
                raise ValueError('Failed documents cannot exceed total documents')
        return v


# Audit and security models
class AuditAction(BaseModel):
    """Audit action record."""
    action_id: str = Field(default_factory=lambda: str(int(datetime.utcnow().timestamp() * 1000000)))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    document_id: Optional[int] = None

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v):
        """Basic IP address format validation."""
        if v is None:
            return v
        # Simple validation for IPv4 and IPv6
        parts = v.split('.')
        if len(parts) == 4:
            # IPv4 validation
            try:
                for part in parts:
                    num = int(part)
                    if not 0 <= num <= 255:
                        raise ValueError('Invalid IPv4 address')
            except ValueError:
                raise ValueError('Invalid IPv4 address format')
        elif ':' in v:
            # Basic IPv6 validation (simplified)
            if not all(c in '0123456789abcdefABCDEF:' for c in v):
                raise ValueError('Invalid IPv6 address format')
        else:
            raise ValueError('Invalid IP address format')
        return v


class ValidationResult(BaseModel):
    """File validation result."""
    is_valid: bool
    file_type: Optional[FileType] = None
    detected_format: Optional[str] = None
    size: Optional[int] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# API response models
class DocumentResponse(BaseModel):
    """API response for document operations."""
    document: Document
    message: str
    status: str = "success"


class AnalysisResponse(BaseModel):
    """API response for analysis operations."""
    results: AnalysisResults
    message: str
    status: str = "success"


class BatchResponse(BaseModel):
    """API response for batch operations."""
    batch_status: BatchStatus
    message: str
    status: str = "success"


class ErrorResponse(BaseModel):
    """API error response."""
    error: str
    details: Optional[Dict[str, Any]] = None
    status: str = "error"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Forgery detection models
class ForgeryIndicator(BaseModel):
    """Individual forgery indicator."""
    indicator_id: str = Field(default_factory=lambda: str(int(datetime.utcnow().timestamp() * 1000000)))
    type: ForgeryType
    description: str
    confidence: confloat(ge=0.0, le=1.0)
    severity: RiskLevel
    location: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    detection_method: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ForgeryAnalysis(TimestampedModel, ConfidenceModel):
    """Comprehensive forgery analysis results."""
    document_id: int
    document_type: DocumentType
    overall_risk: RiskLevel
    indicators: List[ForgeryIndicator] = Field(default_factory=list)
    detection_methods_used: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    
    @model_validator(mode='after')
    def calculate_confidence_from_indicators(self):
        """Calculate overall confidence from indicators if not set."""
        if self.indicators and self.confidence_score == 0.0:
            avg_confidence = sum(i.confidence for i in self.indicators) / len(self.indicators)
            self.confidence_score = avg_confidence
        return self