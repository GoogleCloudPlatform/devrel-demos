-- Script to drop all Tenkai tables and views with CASCADE
-- Use with caution!

DROP VIEW IF EXISTS tool_usage CASCADE;
DROP VIEW IF EXISTS messages CASCADE;

DROP TABLE IF EXISTS run_events CASCADE;
DROP TABLE IF EXISTS run_files CASCADE;
DROP TABLE IF EXISTS test_results CASCADE;
DROP TABLE IF EXISTS lint_results CASCADE;
DROP TABLE IF EXISTS run_results CASCADE;
DROP TABLE IF EXISTS experiments CASCADE;
DROP TABLE IF EXISTS config_blocks CASCADE;

-- Cleanup any legacy tables if they exist
DROP TABLE IF EXISTS test_table CASCADE;
DROP TABLE IF EXISTS experiment_summaries CASCADE;
DROP TABLE IF EXISTS experiment_progress_view CASCADE;
