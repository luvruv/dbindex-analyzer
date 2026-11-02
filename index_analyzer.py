"""DbIndex Analyzer - Command Line Interface (CLI) Entry Point.

Scans any database (PostgreSQL or SQLite), detects missing indexes, identifies redundant
or duplicate indexes, analyzes schema health, and generates both an executable SQL migration
script (`recommendations.sql`) and a production-grade HTML dashboard (`report.html`).
"""

import argparse
import getpass
import os
import sys
import time
import webbrowser

# Ensure Windows terminal doesn't crash on UTF-8 characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from analyzer.db import connect
from analyzer.schema import scan_schema
from analyzer.rules import analyze_schema_comprehensive
from analyzer.report import write_sql_file, write_html_report
from analyzer.generator import generate_demo_database


def parse_args():
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(
        description="DbIndex Analyzer - Production Database Schema & Index Optimization Engine."
    )
    # Mode selection
    p.add_argument("--demo", action="store_true", help="generate a sample database and run full instant audit")
    p.add_argument("--sqlite", help="path to SQLite database file to analyze")
    p.add_argument("--sql-file", help="path to any SQL DDL file (.sql) to analyze (MySQL, PostgreSQL, SQLite, etc.)")

    # PostgreSQL connection options
    p.add_argument("--host", help="PostgreSQL host (default: localhost)")
    p.add_argument("--port", type=int, help="PostgreSQL port (default: 5432)")
    p.add_argument("--db", help="PostgreSQL database name")
    p.add_argument("--user", help="PostgreSQL username")
    p.add_argument("--password", help="PostgreSQL password (prompted securely if omitted)")
    p.add_argument("--schema", default="public", help="PostgreSQL schema to analyze (default: public)")

    # Output options
    p.add_argument("--sql-out", default="recommendations.sql", help="output SQL migration file")
    p.add_argument("--html-out", default="report.html", help="output HTML dashboard file")
    p.add_argument("--open", action="store_true", help="automatically open HTML dashboard in web browser")
    return p.parse_args()


def ask(value, label, default=None):
    """Prompt user if value is not supplied via CLI."""
    if value is not None:
        return value
    suffix = f" [{default}]" if default else ""
    answer = input(f"{label}{suffix}: ").strip()
    return answer or default


def main():
    """Coordinate the end-to-end database analysis workflow."""
    args = parse_args()
    start = time.time()

    sqlite_path = args.sqlite
    sql_file = args.sql_file
    db_name = None
    engine_type = "postgresql"

    # Step 1: Determine target database
    if args.demo:
        print("\n[+] Generating realistic sample database with intentional index flaws...")
        sqlite_path = generate_demo_database("demo_store.db")
        print(f"    Demo database created at: {sqlite_path}")
        db_name = "demo_store.db"
        engine_type = "sqlite"

    elif sql_file:
        db_name = os.path.basename(sql_file)
        engine_type = "sql_file"

    elif sqlite_path:
        db_name = os.path.basename(sqlite_path)
        engine_type = "sqlite"

    elif any([args.host, args.db, args.user]):
        # PostgreSQL CLI flags supplied
        engine_type = "postgresql"
        host = ask(args.host, "Host", "127.0.0.1")
        port = int(ask(args.port, "Port", "5432"))
        db = ask(args.db, "Database name")
        user = ask(args.user, "Username")
        password = args.password if args.password is not None else getpass.getpass("Password: ")
        db_name = db

    else:
        # Interactive mode: let user choose between PostgreSQL, SQLite, SQL Schema File, or Instant Demo
        print("\n" + "=" * 60)
        print("          DbIndex Analyzer - Database Optimizer")
        print("=" * 60)
        print("Select analysis target:")
        print("  [1] PostgreSQL database (live server)")
        print("  [2] SQLite database file (local .db file)")
        print("  [3] Any SQL schema file (.sql DDL from MySQL, PostgreSQL, etc.)")
        print("  [4] Instant Demo (generate synthetic database & audit)")
        choice = input("Enter choice [1/2/3/4] (default 4): ").strip() or "4"

        if choice == "4":
            print("\n[+] Generating realistic sample database with intentional index flaws...")
            sqlite_path = generate_demo_database("demo_store.db")
            db_name = "demo_store.db"
            engine_type = "sqlite"
        elif choice == "3":
            sql_file = input("Enter path to .sql schema file: ").strip()
            db_name = os.path.basename(sql_file)
            engine_type = "sql_file"
        elif choice == "2":
            sqlite_path = input("Enter path to SQLite .db file: ").strip()
            db_name = os.path.basename(sqlite_path)
            engine_type = "sqlite"
        else:
            engine_type = "postgresql"
            host = ask(args.host, "Host", "127.0.0.1")
            port = int(ask(args.port, "Port", "5432"))
            db = ask(args.db, "Database name")
            user = ask(args.user, "Username")
            password = args.password if args.password is not None else getpass.getpass("Password: ")
            db_name = db

    # Step 2: Establish database connection
    try:
        if engine_type == "sql_file":
            conn = connect(sql_file_path=sql_file)
        elif engine_type == "sqlite":
            conn = connect(sqlite_path=sqlite_path)
        else:
            conn = connect(host=host, port=port, dbname=db, user=user, password=password)
    except ConnectionError as e:
        print(f"\n[ERROR] Connection failed:\n{e}")
        return 1

    print(f"\n[OK] Connected to {engine_type.upper()} database '{db_name}'")

    # Step 3: Scan schema
    try:
        scan_res = scan_schema(conn, schema=args.schema)
        tables, fks, indexed = scan_res
        metadata = getattr(scan_res, "metadata", None)
    except Exception as e:
        print(f"\n[ERROR] Failed to introspect schema: {e}")
        return 1
    finally:
        conn.close()

    column_count = sum(len(cols) for cols in tables.values())
    print(f"[OK] Introspected {len(tables)} tables, {column_count} columns total")

    # Step 4: Run comprehensive analysis (Missing + Redundant + Health)
    analysis = analyze_schema_comprehensive(
        tables=tables,
        foreign_keys=fks,
        indexed=indexed,
        metadata=metadata,
        engine_type=engine_type,
        db_name=db_name,
    )

    metrics = analysis.metrics

    # Print Executive Summary to Console
    print("\n" + "-" * 60)
    print(f"DATABASE HEALTH SCORE: {metrics.health_score}/100 (Grade {metrics.health_grade})")
    print(f"  * Primary Key Coverage:     {metrics.pk_coverage_pct}%")
    print(f"  * Foreign Key Indexing:     {metrics.fk_coverage_pct}%")
    print(f"  * Missing Indexes to Add:   {len(analysis.missing_indexes)}")
    print(f"  * Redundant Indexes to Drop:{len(analysis.redundant_indexes)}")
    print("-" * 60)

    # Print Missing Indexes
    if analysis.missing_indexes:
        print("\n[*] MISSING INDEXES (Action: CREATE):")
        for s in analysis.missing_indexes:
            print(f"  [{s.severity}] {s.table}.{s.column}")
            print(f"    Reason:   {s.reason}")
            print(f"    Speedup:  {s.speedup}")
            print(f"    Command:  {s.sql}\n")
    else:
        print("\n[OK] No missing indexes detected. All key columns appear to be indexed.")

    # Print Redundant Indexes
    if analysis.redundant_indexes:
        print("[*] REDUNDANT / UNNECESSARY INDEXES (Action: DROP):")
        for r in analysis.redundant_indexes:
            print(f"  [{r.issue_type}] Table '{r.table}' -> Index '{r.index_name}' ({', '.join(r.columns)})")
            print(f"    Why:     {r.reason}")
            print(f"    Impact:  {r.impact}")
            print(f"    Command: {r.sql}\n")
    else:
        print("[OK] Zero redundant or duplicate indexes detected.")

    # Step 5: Save deliverables
    write_sql_file(analysis.missing_indexes, args.sql_out, analysis.redundant_indexes)
    write_html_report(
        db_name=db_name,
        table_count=len(tables),
        column_count=column_count,
        suggestions=analysis.missing_indexes,
        path=args.html_out,
        redundant=analysis.redundant_indexes,
        healthy=analysis.healthy_indexes,
        metrics=metrics,
        metadata=metadata,
        engine_type=engine_type,
    )

    elapsed = time.time() - start
    print("=" * 60)
    print(f"[OK] Analysis complete in {elapsed:.2f}s")
    print(f"[OK] SQL Migration Script:  {os.path.abspath(args.sql_out)}")
    print(f"[OK] Production Dashboard:  {os.path.abspath(args.html_out)}")
    print("=" * 60)

    if args.open:
        print("[+] Opening report.html in default web browser...")
        webbrowser.open(f"file://{os.path.abspath(args.html_out)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
