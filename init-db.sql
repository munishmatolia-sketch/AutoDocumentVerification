-- Document Forensics Database Initialization Script
-- This script creates the database schema for the Document Forensics application
-- It will be automatically executed when the PostgreSQL container starts

-- Documents table: stores uploaded document metadata
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
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
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
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
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash);
CREATE INDEX IF NOT EXISTS idx_analysis_progress_document ON analysis_progress(document_id);
CREATE INDEX IF NOT EXISTS idx_analysis_progress_status ON analysis_progress(status);
CREATE INDEX IF NOT EXISTS idx_analysis_results_document ON analysis_results(document_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_created ON analysis_results(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_results_risk ON analysis_results(risk_level);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers to automatically update updated_at columns
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_progress_updated_at BEFORE UPDATE ON analysis_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions (if needed for specific users)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Insert sample data for testing (optional - comment out for production)
-- INSERT INTO documents (id, filename, file_path, file_type, size, hash, processing_status)
-- VALUES (
--     uuid_generate_v4(),
--     'sample_document.pdf',
--     '/app/uploads/documents/sample_document.pdf',
--     'pdf',
--     1024000,
--     'abc123def456',
--     'pending'
-- );

-- Display table information
\echo 'Database schema created successfully!'
\echo ''
\echo 'Tables created:'
\dt

\echo ''
\echo 'Indexes created:'
\di
