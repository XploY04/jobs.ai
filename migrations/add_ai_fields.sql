-- Migration: Add AI enrichment fields to jobs table
-- Run with: docker compose exec postgres psql -U jobuser -d jobs_db -f /path/to/this/file.sql

-- Add AI enrichment columns
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills TEXT[];
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_category VARCHAR(50);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_quality_score INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_urgency VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_extracted_deadline TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_deadline_confidence VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_seniority VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_work_arrangement VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_visa_sponsorship VARCHAR(20);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS ai_required_years INTEGER;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_ai_category ON jobs(ai_category);
CREATE INDEX IF NOT EXISTS idx_skills_gin ON jobs USING gin(skills);

-- Verify migration
SELECT 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_name = 'jobs' 
    AND column_name LIKE 'ai_%' OR column_name = 'skills'
ORDER BY ordinal_position;
