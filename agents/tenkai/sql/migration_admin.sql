-- Create a user with REPLICATION privilege to allow setting session_replication_role
DROP USER migration_admin;
CREATE USER migration_admin WITH PASSWORD 'TenkaiMigration2026!' CREATEDB CREATEROLE REPLICATION IN GROUP cloudsqlsuperuser;