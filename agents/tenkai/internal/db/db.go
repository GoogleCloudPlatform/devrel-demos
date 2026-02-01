package db

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	_ "github.com/jackc/pgx/v5/stdlib"
)

type DB struct {
	conn   *sql.DB
	driver string
}

func Open(driver, dsn string) (*DB, error) {
	// Enforce Postgres
	if driver != "pgx" && driver != "postgres" {
		return nil, fmt.Errorf("unsupported driver: %s (only pgx/postgres is supported)", driver)
	}

	conn, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, fmt.Errorf("failed to open postgres database: %w", err)
	}

	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	// Set connection pool limits to prevent exhaustion
	// These values should ideally be configurable via env vars, but safe defaults help.
	conn.SetMaxOpenConns(25)
	conn.SetMaxIdleConns(5)
	conn.SetConnMaxLifetime(0) // Reuse connections forever (or until closed by server)

	db := &DB{conn: conn, driver: driver}

	return db, nil
}

func (db *DB) Close() error {
	return db.conn.Close()
}

// Rebind converts query style from ? to $n if driver is postgres
func (db *DB) Rebind(query string) string {
	// Postgres: Replace ? with $1, $2, ...
	// Naive implementation: Assumes ? is not used in literals.
	count := 0
	var sb strings.Builder
	for _, char := range query {
		if char == '?' {
			count++
			sb.WriteString(fmt.Sprintf("$%d", count))
		} else {
			sb.WriteRune(char)
		}
	}
	return sb.String()
}

// InsertReturningID handles insertion and ID retrieval compatible with both SQLite and Postgres
func (db *DB) InsertReturningID(ctx context.Context, query string, args ...any) (int64, error) {
	// Postgres: Use QueryRowContext + RETURNING id
	if !strings.Contains(strings.ToUpper(query), "RETURNING") {
		query += " RETURNING id"
	}

	var id int64
	err := db.conn.QueryRowContext(ctx, db.Rebind(query), args...).Scan(&id)
	if err != nil {
		return 0, err
	}
	return id, nil
}

// WithTransaction runs a function within a database transaction.
func (db *DB) WithTransaction(ctx context.Context, fn func(tx *sql.Tx) error) error {
	tx, err := db.conn.BeginTx(ctx, nil)
	if err != nil {
		return err
	}

	defer func() {
		if p := recover(); p != nil {
			_ = tx.Rollback()
			panic(p) // Re-throw panic after rollback
		}
	}()

	if err := fn(tx); err != nil {
		_ = tx.Rollback()
		return err
	}

	return tx.Commit()
}
