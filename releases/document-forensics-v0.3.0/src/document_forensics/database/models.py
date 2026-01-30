"""SQLAlchemy database models for document forensics."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, BigInteger, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Document(Base):
    """Document model for storing uploaded document metadata."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))
    size = Column(BigInteger)
    hash = Column(String(64))
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(50), default="pending")
    document_metadata = Column("metadata", JSON)  # Use different attribute name to avoid SQLAlchemy reserved word
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    progress = relationship("AnalysisProgress", back_populates="document", cascade="all, delete-orphan")
    results = relationship("AnalysisResult", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.processing_status})>"


class AnalysisProgress(Base):
    """Analysis progress tracking model."""
    
    __tablename__ = "analysis_progress"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    status = Column(String(50), nullable=False)
    progress_percentage = Column(Float, default=0.0)
    current_step = Column(String(255))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    errors = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="progress")
    
    def __repr__(self):
        return f"<AnalysisProgress(id={self.id}, document_id={self.document_id}, status={self.status})>"


class AnalysisResult(Base):
    """Analysis results model for storing completed analysis data."""
    
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False)
    results = Column(JSON, nullable=False)
    confidence_score = Column(Float)
    risk_level = Column(String(20))
    metadata_analysis = Column(JSON)
    tampering_analysis = Column(JSON)
    authenticity_analysis = Column(JSON)
    forgery_analysis = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="results")
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, document_id={self.document_id}, risk_level={self.risk_level})>"
