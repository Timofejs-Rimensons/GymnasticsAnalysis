-- PostgreSQL Schema for Gymnastics Analysis System
-- Version: 1.0
-- PostgreSQL 16+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- SESSIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ANALYSES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Video metadata
    file_name VARCHAR(500) NOT NULL,
    exercise_type VARCHAR(100) NOT NULL,
    
    -- Video storage (BYTEA = binary data)
    input_video BYTEA,
    input_video_size INTEGER,
    input_video_mime_type VARCHAR(100) DEFAULT 'video/mp4',
    
    output_video BYTEA,
    output_video_size INTEGER,
    output_video_mime_type VARCHAR(100) DEFAULT 'video/mp4',
    
    -- Processing status
    status VARCHAR(50) DEFAULT 'pending',
    progress DECIMAL(3,2) DEFAULT 0.00,
    error_message TEXT,
    
    -- Analysis results
    overall_score DECIMAL(5,2),
    max_score DECIMAL(5,2),
    percentage DECIMAL(5,2),
    results_json JSONB,
    
    -- Reports
    pdf_report BYTEA,
    pdf_report_size INTEGER,
    json_report JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Analyses table indexes
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_exercise_type ON analyses(exercise_type);

-- Sessions table indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================
-- TRIGGERS FOR AUTO-UPDATE TIMESTAMPS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for analyses table
DROP TRIGGER IF EXISTS update_analyses_updated_at ON analyses;
CREATE TRIGGER update_analyses_updated_at 
    BEFORE UPDATE ON analyses
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- GRANT PERMISSIONS
-- ============================================
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gymnastics;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gymnastics;
