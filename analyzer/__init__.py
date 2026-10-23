"""
analyzer
========
Core analysis package for DbIndex Analyzer.

In Python, an `__init__.py` file indicates that this directory should be treated
as a Python package. This enables other modules (such as `index_analyzer.py` and
`tests/test_rules.py`) to import functionality from this folder using syntax like:
    from analyzer.db import connect
    from analyzer.schema import scan_schema
    from analyzer.rules import recommend
    from analyzer.report import write_sql_file, write_html_report

How the modules in this package work together:
---------------------------------------------
1. `db.py`:
   Handles opening a connection to the PostgreSQL database using psycopg2,
   with proper timeouts and friendly error handling.

2. `schema.py`:
   Runs SQL queries against PostgreSQL system catalogs (`information_schema`
   and `pg_catalog`) to extract information about all tables, columns, foreign
   key constraints, and already-existing indexes.

3. `rules.py`:
   Inspects the extracted schema details against heuristic indexing rules
   (e.g., foreign keys, email columns, phone numbers, timestamps, status flags).
   Identifies unindexed columns that will benefit from an index and builds the
   corresponding `CREATE INDEX IF NOT EXISTS` SQL statements.

4. `report.py`:
   Takes the recommendations produced by `rules.py` and outputs them in two formats:
   - A clean `.sql` script ready to run directly against PostgreSQL (`recommendations.sql`).
   - A modern, styled `.html` visual report with summary cards and one-click copy (`report.html`).
"""
