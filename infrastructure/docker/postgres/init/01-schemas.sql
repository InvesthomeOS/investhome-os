-- Investhome OS PostgreSQL initialization
-- Creates isolated schemas for platform services

CREATE SCHEMA IF NOT EXISTS n8n;
CREATE SCHEMA IF NOT EXISTS investhome;

GRANT ALL ON SCHEMA n8n TO CURRENT_USER;
GRANT ALL ON SCHEMA investhome TO CURRENT_USER;
