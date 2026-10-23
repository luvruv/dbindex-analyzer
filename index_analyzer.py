"""DbIndex Analyzer - Command Line Interface (CLI) Entry Point.

This is the main executable script for the DbIndex Analyzer tool. It scans a
PostgreSQL database, finds columns that are missing indexes, and generates both
an executable SQL script (`recommendations.sql`) and a visual HTML report (`report.html`).

How this application works from start to finish:
-----------------------------------------------
1. User runs this script from the terminal (with optional CLI arguments).
2. Arguments are parsed; if any required connection parameter is missing,
   the user is prompted interactively.
3. Passwords are typed securely without being printed to the screen.
4. The tool connects to PostgreSQL using `analyzer.db.connect()`.
5. The database schema is introspected using `analyzer.schema.scan_schema()`
   to discover all tables, columns, foreign keys, and existing indexes.
6. The database connection is safely closed in a `finally` block.
7. The rule engine `analyzer.rules.recommend()` detects unindexed columns.
8. Recommendations and speedup estimates are printed to the console.
9. SQL statements and an HTML report are saved to disk via `analyzer.report`.
"""

# ------------------------------------------------------------------------------
# Standard Library Imports:
# ------------------------------------------------------------------------------
# argparse:
# Built-in Python module for parsing command-line options and arguments.
# Automatically generates helpful usage messages when the user types --help.
import argparse

# getpass:
# Built-in Python module for securely prompting the user for passwords
# without echoing the typed characters back to the console screen.
import getpass

# sys:
# Built-in Python module providing access to system-specific variables and
# functions, such as sys.exit() which exits the program with a status code.
import sys

# time:
# Built-in Python module for time tracking. Used here to measure how many
# seconds the database analysis took to complete.
import time

# ------------------------------------------------------------------------------
# Internal Project Module Imports (from the `analyzer` package):
# ------------------------------------------------------------------------------
# connect: Establishes a socket connection to PostgreSQL using psycopg2.
from analyzer.db import connect

# scan_schema: Queries PostgreSQL system catalogs to inspect tables, keys, and indexes.
from analyzer.schema import scan_schema

# recommend: Evaluates columns against heuristic rules to suggest new indexes.
from analyzer.rules import recommend

# write_sql_file, write_html_report: Saves recommendations as .sql and .html files.
from analyzer.report import write_sql_file, write_html_report


def parse_args():
    """Parse command-line arguments provided by the user.

    Returns:
    --------
    argparse.Namespace
        An object containing all parsed command-line argument values.
    """
    p = argparse.ArgumentParser(description="Find missing indexes in your PostgreSQL database.")
    p.add_argument("--host", help="database host (default: localhost)")
    p.add_argument("--port", type=int, help="database port (default: 5432)")
    p.add_argument("--db", help="database name")
    p.add_argument("--user", help="database user")
    p.add_argument("--password", help="password (prompted if omitted)")
    p.add_argument("--schema", default="public", help="schema to analyze (default: public)")
    p.add_argument("--sql-out", default="recommendations.sql", help="output SQL file")
    p.add_argument("--html-out", default="report.html", help="output HTML report")
    return p.parse_args()


def ask(value, label, default=None):
    """Return the CLI value if provided; otherwise, prompt the user in the terminal.

    Parameters:
    -----------
    value : any
        The value parsed from command-line arguments (or None if omitted).
    label : str
        The human-friendly prompt label to display (e.g. "Host", "Database name").
    default : any, optional
        A fallback default value if the user presses Enter without typing anything.

    Returns:
    --------
    str
        The user-provided string or the default value.
    """
    # If the user already provided this argument via CLI flags, use it immediately
    if value is not None:
        return value

    # Otherwise, display an interactive prompt showing the optional default in brackets
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def main():
    """Coordinate the end-to-end database index analysis workflow.

    Returns:
    --------
    int
        Exit status code: 0 for successful completion, 1 for errors.
    """
    # Step 1: Collect database connection settings
    args = parse_args()
    host = ask(args.host, "Host", "localhost")
    port = int(ask(args.port, "Port", "5432"))
    db = ask(args.db, "Database name")
    user = ask(args.user, "Username")

    # If password was not passed via CLI flag, prompt securely using getpass
    password = args.password if args.password is not None else getpass.getpass("Password: ")

    start = time.time()

    # Step 2: Establish database connection
    try:
        conn = connect(host, port, db, user, password)
    except ConnectionError as e:
        print(f"ERROR: could not connect.\n{e}")
        return 1

    print(f"Connected to '{db}' on {host}:{port}")

    # Step 3: Scan the database schema
    try:
        tables, fks, indexed = scan_schema(conn, args.schema)
    except Exception as e:
        print(f"ERROR: could not read schema: {e}")
        return 1
    finally:
        # Guarantee that database connection is closed, even if an error occurred during schema scan
        conn.close()

    # Step 4: Calculate schema metrics
    column_count = sum(len(cols) for cols in tables.values())
    print(f"Found {len(tables)} tables, {column_count} columns total")

    # Step 5: Evaluate columns against indexing rules
    suggestions = recommend(tables, fks, indexed)
    for s in suggestions:
        print(f"SUGGESTION: Add index on {s.table}.{s.column} - Why: {s.reason} "
              f"- Expected speedup: {s.speedup} - SQL: {s.sql}")

    # Step 6: Write output report files
    write_sql_file(suggestions, args.sql_out)
    write_html_report(db, len(tables), column_count, suggestions, args.html_out)

    print(f"\n{len(suggestions)} recommendations.")
    print(f"Saved: {args.sql_out}, {args.html_out}  (done in {time.time() - start:.2f}s)")
    return 0


# In Python, __name__ is set to "__main__" when this script is run directly from the terminal
# (e.g. `python index_analyzer.py`), but not when imported as a module in another script.
# This standard guard ensures main() executes only when run as a standalone application.
if __name__ == "__main__":
    sys.exit(main())