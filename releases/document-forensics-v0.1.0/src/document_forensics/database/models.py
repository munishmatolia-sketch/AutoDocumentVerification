"""SQLAlchemy database models for document forensics system."""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, LargeBinary, 
    Float, Boolean, ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


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


class Document(Base):
    """Document entity for storing uploaded files and metadata."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(SQLEnum(FileType), nullable=False)
    size = Column(Integer, nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    hash = Column(String(64), nullable=False, unique=True, index=True)
    content = Column(LargeBinary, nullable=False)
    processing_status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING)
    
    # Relationships
    metadata_analysis = relationship("MetadataAnalysis", back_populates="document", uselist=False)
    tampering_analysis = relationship("TamperingAnalysis", back_populates="document", uselist=False)
    authenticity_analysis = relationship("AuthenticityAnalysis", back_populates="document", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="document")


class MetadataAnalysis(Base):
    """Metadata analysis results for documents."""
    
    __tablename__ = "metadata_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    extracted_metadata = Column(JSON, nullable=False)
    timestamp_consistency = Column(JSON)
    software_signatures = Column(JSON)
    anomalies = Column(JSON)
    geo_location = Column(JSON)
    device_fingerprint = Column(JSON)
    processing_time = Column(Float)
    
    # Relationships
    document = relationship("Document", back_populates="metadata_analysis")


class TamperingAnalysis(Base):
    """Tampering analysis results for documents."""
    
    __tablename__ = "tampering_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    overall_risk = Column(SQLEnum(RiskLevel), nullable=False)
    detected_modifications = Column(JSON)
    pixel_inconsistencies = Column(JSON)
    text_modifications = Column(JSON)
    signature_breaks = Column(JSON)
    compression_anomalies = Column(JSON)
    confidence_score = Column(Float, nullable=False)
    processing_time = Column(Float)
    
    # Relationships
    document = relationship("Document", back_populates="tampering_analysis")
    visual_evidence = relationship("VisualEvidence", back_populates="tampering_analysis")


class AuthenticityAnalysis(Base):
    """Authenticity analysis results for documents."""
    
    __tablename__ = "authenticity_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    authenticity_score = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=False)
    comparison_results = Column(JSON)
    structure_validation = Column(JSON)
    embedded_objects_assessment = Column(JSON)
    forensic_indicators = Column(JSON)
    processing_time = Column(Float)
    
    # Relationships
    document = relationship("Document", back_populates="authenticity_analysis")


class VisualEvidence(Base):
    """Visual evidence generated during analysis."""
    
    __tablename__ = "visual_evidence"
    
    id = Column(Integer, primary_key=True, index=True)
    tampering_analysis_id = Column(Integer, ForeignKey("tampering_analysis.id"), nullable=False)
    evidence_type = Column(String(50), nullable=False)
    description = Column(Text)
    image_data = Column(LargeBinary, nullable=False)
    annotations = Column(JSON)
    confidence_level = Column(Float, nullable=False)
    analysis_method = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tampering_analysis = relationship("TamperingAnalysis", back_populates="visual_evidence")


class AuditLog(Base):
    """Audit log for tracking all system activities."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(String(100))
    action = Column(String(100), nullable=False)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Relationships
    document = relationship("Document", back_populates="audit_logs")


class BatchJob(Base):
    """Batch processing job tracking."""
    
    __tablename__ = "batch_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(36), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING)
    total_documents = Column(Integer, nullable=False)
    processed_documents = Column(Integer, default=0)
    failed_documents = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    error_details = Column(JSON)
    user_id = Column(String(100))


class SystemConfiguration(Base):
    """System configuration settings."""
    
    __tablename__ = "system_configuration"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())