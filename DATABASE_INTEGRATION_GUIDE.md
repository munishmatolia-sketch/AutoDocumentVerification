# Database Integration Implementation Guide

**Purpose**: Enable full document analysis workflow by implementing database integration  
**Estimated Time**: 4-6 hours  
**Difficulty**: Intermediate

---

## 📋 Overview

Currently, the application:
- ✅ Uploads documents and stores files
- ✅ Returns UUID document IDs
- ✅ Accepts analysis requests
- ❌ Cannot execute actual analysis (no UUID → file path mapping)
- ❌ Cannot track progress
- ❌ Cannot store/retrieve results

After database integration:
- ✅ Maps UUID to file path
- ✅ Executes actual analysis
- ✅ Tracks real-time progress
- ✅ Stores and retrieves results

---

## 🗄️ Step 1: Create Database Schema

### 1.1 Create Migration File

Create a new file: `src/document_forensics/database/migrations/001_initial_schema.sql`

```sql
-- Documents table: stores uploaded document metadata
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    size BIGINT,
    hash VARCHAR(64),
    upload_timestamp TIMESTAMP DEFAULT NOW(),
    processing_status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Analysis progress table: tracks real-time analysis progress
CREATE TABLE IF NOT EXISTS analysis_progress (
    id SERIAL PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    progress_percentage FLOAT DEFAULT 0.0,
    current_step VARCHAR(255),
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP,
    errors JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Analysis results table: stores completed analysis results
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL,
    results JSONB NOT NULL,
    confidence_score FLOAT,
    risk_level VARCHAR(20),
    metadata_analysis JSONB,
    tampering_analysis JSONB,
    authenticity_analysis JSONB,
    forgery_analysis JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_progress_document ON analysis_progress(document_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_document ON analysis_results(document_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_created ON analysis_results(created_at DESC);
```

### 1.2 Run Migration

Add to `init-db.sql` or run manually:

```bash
# Copy migration to container
docker cp src/document_forensics/database/migrations/001_initial_schema.sql autodocumentverification-postgres-1:/tmp/

# Execute migration
docker exec -it autodocumentverification-postgres-1 psql -U postgres -d document_forensics -f /tmp/001_initial_schema.sql
```

Or add to `init-db.sql` file in project root (will run on container creation).

---

## 🔧 Step 2: Create Database Models

### 2.1 Update SQLAlchemy Models

Edit `src/document_forensics/database/models.py`:

```python
"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, BigInteger, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Document(Base):
    """Document model."""
    __tablename__ = "documents"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))
    size = Column(BigInteger)
    hash = Column(String(64))
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(50), default="pending")
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    progress = relationship("AnalysisProgress", back_populates="document", cascade="all, delete-orphan")
    results = relationship("AnalysisResult", back_populates="document", cascade="all, delete-orphan")


class AnalysisProgress(Base):
    """Analysis progress tracking model."""
    __tablename__ = "analysis_progress"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
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


class AnalysisResult(Base):
    """Analysis results model."""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
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
```

### 2.2 Create Database Connection Manager

Edit `src/document_forensics/database/connection.py`:

```python
"""Database connection management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from ..core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=NullPool,
    echo=settings.sql_debug if hasattr(settings, 'sql_debug') else False
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """Dependency for FastAPI endpoints."""
    async with get_db() as session:
        yield session
```

---

## 📝 Step 3: Update Upload Manager

Edit `src/document_forensics/upload/manager.py`:

Find the `upload_document` method and add database save after file storage:

```python
async def upload_document(
    self,
    file_data: bytes,
    filename: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Upload and process a document."""
    try:
        # ... existing validation code ...
        
        # Generate document ID
        document_id = uuid4()
        
        # ... existing file storage code ...
        
        # NEW: Save to database
        from ..database.connection import get_db
        from ..database.models import Document
        
        async with get_db() as db:
            db_document = Document(
                id=document_id,
                filename=filename,
                file_path=str(storage_path),
                file_type=file_type,
                size=len(file_data),
                hash=file_hash,
                upload_timestamp=datetime.now(),
                processing_status="pending",
                metadata=metadata
            )
            db.add(db_document)
            await db.commit()
        
        # ... rest of existing code ...
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise
```

---

## 🔬 Step 4: Update Analysis Endpoint

Edit `src/document_forensics/api/routers/analysis.py`:

Replace the `/start` endpoint with full implementation:

```python
@router.post("/start")
@limiter.limit("10/minute")
async def start_analysis(
    request: Request,
    document_id: str = Body(..., embed=True),
    current_user: Optional[User] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Start analysis for a document."""
    try:
        from ...database.models import Document, AnalysisProgress
        from sqlalchemy import select
        
        # Get document from database
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        # Create progress tracking
        progress = AnalysisProgress(
            document_id=document.id,
            status="processing",
            progress_percentage=0.0,
            current_step="Starting analysis",
            start_time=datetime.now()
        )
        db.add(progress)
        await db.commit()
        
        # Start analysis in background
        from ...workflow.workflow_manager import WorkflowManager
        workflow_manager = WorkflowManager()
        
        # Run analysis asynchronously
        analysis_results = await workflow_manager.analyze_document(
            document_path=document.file_path,
            document_id=str(document.id),
            priority=5
        )
        
        # Update progress
        progress.status = "completed"
        progress.progress_percentage = 100.0
        progress.current_step = "Analysis complete"
        progress.end_time = datetime.now()
        await db.commit()
        
        # Save results
        from ...database.models import AnalysisResult
        
        result_record = AnalysisResult(
            document_id=document.id,
            analysis_type="full",
            results=analysis_results.model_dump(),
            confidence_score=analysis_results.confidence_score,
            risk_level=analysis_results.overall_risk_assessment.value
        )
        db.add(result_record)
        await db.commit()
        
        logger.info(f"Analysis completed for document {document_id}")
        
        return {
            "status": "success",
            "message": "Analysis completed successfully",
            "document_id": str(document_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )
```

---

## 📊 Step 5: Update Status Endpoint

Edit `src/document_forensics/api/routers/analysis.py`:

Replace the status endpoint:

```python
@router.get("/{document_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    document_id: str,
    current_user: Optional[User] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """Get analysis status for a document."""
    try:
        from ...database.models import AnalysisProgress
        from sqlalchemy import select
        
        # Get latest progress
        result = await db.execute(
            select(AnalysisProgress)
            .where(AnalysisProgress.document_id == document_id)
            .order_by(AnalysisProgress.created_at.desc())
            .limit(1)
        )
        progress = result.scalar_one_or_none()
        
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No analysis found for document {document_id}"
            )
        
        return AnalysisStatusResponse(
            document_id=0,  # Can be removed from response model
            status=progress.status,
            progress_percentage=progress.progress_percentage,
            current_step=progress.current_step,
            start_time=progress.start_time.isoformat() if progress.start_time else "",
            errors=progress.errors or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )
```

---

## 📦 Step 6: Install Required Dependencies

Add to `requirements.txt`:

```
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.23
alembic==1.13.1
```

Install:

```bash
docker-compose -f docker-compose.simple.yml exec api pip install asyncpg sqlalchemy[asyncio] alembic
```

Or rebuild containers:

```bash
docker-compose -f docker-compose.simple.yml build --no-cache
docker-compose -f docker-compose.simple.yml up -d
```

---

## 🧪 Step 7: Test the Implementation

### 7.1 Test Database Connection

```python
# test_db.py
import asyncio
from src.document_forensics.database.connection import get_db
from src.document_forensics.database.models import Document

async def test_connection():
    async with get_db() as db:
        # Test query
        from sqlalchemy import select
        result = await db.execute(select(Document).limit(1))
        print("Database connection successful!")

asyncio.run(test_connection())
```

### 7.2 Test Upload with Database

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test.txt"
```

Check database:

```bash
docker exec -it autodocumentverification-postgres-1 psql -U postgres -d document_forensics -c "SELECT id, filename, processing_status FROM documents;"
```

### 7.3 Test Analysis

```bash
# Get UUID from upload response
curl -X POST http://localhost:8000/api/v1/analysis/start \
  -H "Content-Type: application/json" \
  -d '{"document_id": "your-uuid-here"}'
```

### 7.4 Test Status

```bash
curl http://localhost:8000/api/v1/analysis/your-uuid-here/status
```

---

## 📚 Additional Resources

### Documentation Files:
- `ANALYSIS_START_ERROR_FIXED.md` - Explains the UUID issue and why database is needed
- `DOCUMENT_STATUS_ERROR_FIXED.md` - Status endpoint details
- `ALL_ISSUES_RESOLVED.md` - Complete overview of current state

### Code References:
- `src/document_forensics/database/models.py` - Database models (needs creation)
- `src/document_forensics/database/connection.py` - Connection management (needs update)
- `src/document_forensics/upload/manager.py` - Upload logic (needs database save)
- `src/document_forensics/api/routers/analysis.py` - Analysis endpoints (needs database integration)

---

## 🎯 Summary

### What You Need to Do:

1. ✅ Create database schema (SQL migration)
2. ✅ Create/update SQLAlchemy models
3. ✅ Update database connection manager
4. ✅ Update upload manager to save to database
5. ✅ Update analysis endpoint to retrieve from database
6. ✅ Update status endpoint to query database
7. ✅ Install required dependencies
8. ✅ Test the implementation

### Expected Outcome:

After implementation:
- Documents stored in database with UUID → file path mapping
- Analysis actually executes using the file path
- Real-time progress tracking in database
- Results stored and retrievable
- Full workflow operational

### Estimated Time:
- Database schema: 30 minutes
- Models and connection: 1 hour
- Upload manager update: 30 minutes
- Analysis endpoint update: 2 hours
- Status endpoint update: 30 minutes
- Testing and debugging: 1-2 hours

**Total: 4-6 hours**

---

## 🆘 Need Help?

If you encounter issues:
1. Check database connection: `docker logs autodocumentverification-postgres-1`
2. Check API logs: `docker logs autodocumentverification-api-1`
3. Verify schema: `docker exec -it autodocumentverification-postgres-1 psql -U postgres -d document_forensics -c "\dt"`
4. Test queries manually in psql

---

**Created By**: Kiro AI Assistant  
**Date**: January 30, 2026  
**Status**: Ready for Implementation
