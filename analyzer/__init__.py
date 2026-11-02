"""
analyzer
========
Core database schema and index intelligence package for DbIndex Analyzer.

Provides end-to-end database auditing:
1. `db.py`:
   Multi-engine connection manager supporting PostgreSQL (via psycopg2) and SQLite (via standard library).

2. `schema.py`:
   Deep catalog introspection extracting tables, columns, data types, primary keys, foreign keys,
   and detailed index metadata across PostgreSQL and SQLite.

3. `rules.py`:
   Dual index recommendation engine:
   - Detects missing indexes on unindexed columns (Foreign Keys, lookup keys, timestamps, search filters).
   - Detects redundant, duplicate, and prefix-subsumed indexes that waste storage and write latency.
   - Categorizes existing healthy indexes (Primary Keys, Unique Constraints, Composite Indexes).
   - Computes comprehensive Schema Health Score (0-100) and letter grades.

4. `generator.py`:
   Generates realistic sample databases and schemas on-demand for immediate testing and academic presentations.

5. `report.py`:
   Builds the executive HTML dashboard and production SQL migration rollout and cleanup scripts.
"""

from analyzer.db import connect, connect_postgres, connect_sqlite
from analyzer.schema import scan_schema
from analyzer.rules import recommend, analyze_schema_comprehensive, detect_redundant_indexes
from analyzer.report import write_sql_file, write_html_report
from analyzer.generator import generate_demo_database

__all__ = [
    "connect",
    "connect_postgres",
    "connect_sqlite",
    "scan_schema",
    "recommend",
    "analyze_schema_comprehensive",
    "detect_redundant_indexes",
    "write_sql_file",
    "write_html_report",
    "generate_demo_database",
]
