# Gemini Code Assistant Context

This document provides context for the Gemini Code Assistant to understand the `testquery` project.

## Project Overview

`testquery` (or `tq`) is a command-line tool written in Go that allows developers to query Go test results using a SQL interface. It works by running `go test` on a specified package, collecting the results and coverage data, and storing it in a SQLite database. This database can then be queried to get insights into the test suite.

The project is structured as a standard Go command-line application:

*   **`main.go`**: The entry point for the application.
*   **`cmd/`**: Contains the command-line interface logic, built using the `cobra` library. It defines the `query`, `shell`, and `version` commands.
*   **`internal/`**: Contains the core application logic:
    *   **`collector/`**: Gathers test and coverage data.
    *   **`database/`**: Manages the SQLite database, including schema creation and data population.
    *   **`query/`**: Executes the SQL queries and formats the output using `go-pretty`.
    *   **`shell/`**: Implements the interactive shell.
*   **`sql/`**: Contains the SQL schema and sample queries.
*   **`Makefile`**: Defines common development tasks like building, testing, and cleaning.

## Building and Running

### Building

To build the `tq` binary, use the `Makefile`:

```sh
make build
```

This will create the `bin/tq` executable.

### Running

There are two main ways to use `tq`:

1.  **Single Query:** Execute a single, non-interactive query.

    ```sh
    ./bin/tq query --pkg <package> "<SQL_QUERY>"
    ```

2.  **Interactive Shell:** Start an interactive SQL shell.

    ```sh
    ./bin/tq shell --pkg <package>
    ```

Replace `<package>` with the Go package you want to analyze (e.g., `./...` for all packages).

## Development Conventions

### Testing

The project has both unit and integration tests. To run all tests and see the coverage report, use:

```sh
make test-cover
```

### Database

The database schema is defined in `internal/database/sql/schema.sql`. The database is created and populated by the `internal/database` package. The default database file is `testquery.db`.

### Dependencies

The project uses the following key Go libraries:

*   **`github.com/spf13/cobra`**: For creating the command-line interface.
*   **`github.com/mattn/go-sqlite3`**: As the driver for the SQLite database.
*   **`github.com/jedib0t/go-pretty`**: For formatting the query output into tables.
