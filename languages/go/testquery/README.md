# TestQuery

[![Go](https://github.com/danicat/testquery/actions/workflows/go.yml/badge.svg)](https://github.com/danicat/testquery/actions/workflows/go.yml)

Test Query (tq) is a command line tool to query Go test results with a SQL interface. The idea of using SQL was inspired by a similar tool called OSQuery, which does the same for operating system metrics.

## Demo

https://github.com/user-attachments/assets/b6ed5637-392c-4686-9405-fd174e559582

## History

During Gophercon 2024, specially after my talk on mutation testing, many people came to me to talk about their challenges with testing. One particular thought that stuck with me was that in older codebases it can become hard to keep track of the need for each individual test, and we can potentually end up with dozens - maybe even hundreds - of tests that are obsolete.

This tool was designed to make extracting information from tests easier for the average developer (as long as you know SQL of course - but everyone should learn SQL anyway ^^).

It is currently under development so it doesn't support a lot of information yet, but it is already possible to query basic information about tests, including:

- What tests are passing or not (all_tests, passed_tests, failed_tests)
- What is the overall coverage (all_coverage)
- What is the coverage provided by an individual test (test_coverage)

## Usage

`tq` provides two main modes of operation: in-memory and file-based.

- **In-Memory (Default):** For quick, ephemeral queries, `tq` can run tests and build a database entirely in memory. No files are created on disk.
- **File-Based:** For more persistent analysis, you can first build a database file and then run multiple queries against it.

### Commands

There are three main commands: `build`, `query`, and `shell`.

#### `tq build`

Builds a persistent SQLite database file from a Go package. This is the primary way to create a database for later analysis.

```sh
# Build a database from the testdata package
./bin/tq build --pkg ./testdata/ --output tq.db
```

#### `tq query`

Executes a single, non-interactive query.

```sh
# Run an in-memory query against the testdata package
./bin/tq query --pkg ./testdata/ "SELECT * FROM failed_tests"

# Run a query against a pre-built database file
./bin/tq query --db tq.db "SELECT * FROM failed_tests"
```

#### `tq shell`

Starts an interactive SQL shell.

```sh
# Start an in-memory shell for the testdata package
./bin/tq shell --pkg ./testdata/

# Start a shell using a pre-built database file
./bin/tq shell --db tq.db
```

### Command-Line Help

You can get more information about the available commands and flags by using the `--help` flag.

```sh
% ./bin/tq --help
TestQuery (tq) is a command-line tool that allows you to query Go test results using a SQL interface.
It is designed to help developers understand and analyze tests in their projects,
especially in large and mature codebases.

Usage:
  tq [command]

Available Commands:
  completion  Generate the autocompletion script for the specified shell
  help        Help about any command
  query       Execute a single query.
  shell       Start an interactive SQL shell.

Flags:
  -h, --help   help for tq

Use "tq [command] --help" for more information about a command.
```

### Makefile Targets

The `Makefile` provides several targets to standardize the development and testing workflow:

-   `make build`: Compiles the `tq` binary into the `bin/` directory.
-   `make test`: Runs the unit tests for the project. This is an alias for `make unit-test`.
-   `make unit-test`: Runs the fast, isolated unit tests and generates a `unit.cover` profile.
-   `make integration-test`: Builds a coverage-instrumented binary and runs it against a suite of real-world scenarios, generating an `integration.cover` profile.
-   `make test-cover`: The primary test target. It runs both `unit-test` and `integration-test`, and then merges their coverage profiles to produce an aggregated total coverage report for the project.
-   `make setup`: Installs the necessary Go tools for the project, such as `gopls`.
-   `make clean`: Removes all build and test artifacts.

