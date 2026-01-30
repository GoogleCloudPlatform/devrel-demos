package db

import "database/sql"

func (db *DB) GetRunStdout(runID int64) (string, error) {
	var stdout sql.NullString
	err := db.conn.QueryRow(db.Rebind("SELECT stdout FROM run_results WHERE id = ?"), runID).Scan(&stdout)
	if err != nil {
		return "", err
	}
	return stdout.String, nil
}
