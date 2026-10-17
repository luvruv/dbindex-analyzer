"""DbIndex Analyzer - finds missing indexes in a PostgreSQL database."""
import argparse
import getpass
import sys
import time

from analyzer.db import connect
from analyzer.schema import scan_schema
from analyzer.rules import recommend
from analyzer.report import write_sql_file, write_html_report


def parse_args():
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
    """Use the CLI value, otherwise ask the user."""
    if value is not None:
        return value
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def main():
    args = parse_args()
    host = ask(args.host, "Host", "localhost")
    port = int(ask(args.port, "Port", "5432"))
    db = ask(args.db, "Database name")
    user = ask(args.user, "Username")
    password = args.password if args.password is not None else getpass.getpass("Password: ")

    start = time.time()
    try:
        conn = connect(host, port, db, user, password)
    except ConnectionError as e:
        print(f"ERROR: could not connect.\n{e}")
        return 1
    print(f"Connected to '{db}' on {host}:{port}")
    
    try:
        tables, fks, indexed = scan_schema(conn, args.schema)
    except Exception as e:
        print(f"ERROR: could not read schema: {e}")
        return 1
    finally:
        conn.close()

    column_count = sum(len(cols) for cols in tables.values())
    print(f"Found {len(tables)} tables, {column_count} columns total")

    suggestions = recommend(tables, fks, indexed)
    for s in suggestions:
        print(f"SUGGESTION: Add index on {s.table}.{s.column} - Why: {s.reason} "
              f"- Expected speedup: {s.speedup} - SQL: {s.sql}")

    write_sql_file(suggestions, args.sql_out)
    write_html_report(db, len(tables), column_count, suggestions, args.html_out)
    print(f"\n{len(suggestions)} recommendations.")
    print(f"Saved: {args.sql_out}, {args.html_out}  (done in {time.time() - start:.2f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())