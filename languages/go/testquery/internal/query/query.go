package query

import (
	"database/sql"
	"io"

	"github.com/jedib0t/go-pretty/v6/table"
)

func Execute(w io.Writer, db *sql.DB, query string) error {
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return err
	}

	t := table.NewWriter()
	t.SetOutputMirror(w)

	var header = make(table.Row, len(columns))
	for i := range columns {
		header[i] = columns[i]
	}
	t.AppendHeader(header)

	for rows.Next() {
		var values = make(table.Row, len(columns))
		var valuesPtr = make([]any, len(columns))
		for i := range values {
			valuesPtr[i] = &values[i]
		}

		if err := rows.Scan(valuesPtr...); err != nil {
			return err
		}

		t.AppendRow(values)
	}

	if err = rows.Err(); err != nil {
		return err
	}

	if err = rows.Close(); err != nil {
		return err
	}

	t.Render()
	return nil
}
