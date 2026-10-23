"""PostgreSQL schema introspection module for DbIndex Analyzer.

This module reads database metadata from PostgreSQL system catalogs and
`information_schema` views to identify:
1. All user tables, their columns, and their data types.
2. All foreign key constraints between tables.
3. All columns that are already covered by existing indexes (including primary keys).
"""

# ------------------------------------------------------------------------------
# SQL Queries for Schema Introspection
# ------------------------------------------------------------------------------

# COLUMNS_SQL:
# Retrieves table names, column names, and data types for all real user tables.
#
# - information_schema.columns:
#   An ANSI standard system view listing all columns in all tables and views.
# - information_schema.tables:
#   System view containing table-level metadata. We JOIN on table_name and table_schema.
# - t.table_type = 'BASE TABLE':
#   Filters out views, temporary tables, and system views, focusing only on permanent data tables.
# - c.table_schema = %s:
#   Parameterized placeholder for the target schema name (e.g. 'public') to prevent SQL injection.
# - ORDER BY c.table_name, c.ordinal_position:
#   Ensures results are ordered logically by table name and the natural position of columns.
COLUMNS_SQL = """
SELECT c.table_name, c.column_name, c.data_type
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = %s AND t.table_type = 'BASE TABLE'
ORDER BY c.table_name, c.ordinal_position
"""

# FK_SQL:
# Discovers foreign key constraints in the database.
#
# Why foreign keys matter for indexing:
# PostgreSQL automatically builds unique indexes for Primary Keys, but does NOT
# automatically create indexes on Foreign Key columns! Without an index, performing
# JOIN operations or deleting rows from parent tables can trigger slow full-table scans.
#
# - information_schema.table_constraints (tc):
#   Identifies constraint names and types (filtered to 'FOREIGN KEY').
# - information_schema.key_column_usage (kcu):
#   Identifies the table and column name on the child/referencing side.
# - information_schema.constraint_column_usage (ccu):
#   Identifies the referenced table name on the parent side.
FK_SQL = """
SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s
"""

# INDEX_SQL:
# Queries PostgreSQL's internal catalog tables to find already-indexed columns.
#
# We inspect the first column of each existing index (including Primary Keys):
# - pg_index (i):
#   Low-level catalog recording every index. `i.indrelid` is the table's object ID (OID).
#   `i.indkey` is an array of column attribute numbers; `i.indkey[0]` is the first column.
# - pg_class (t):
#   Represents database entities (tables, indexes, sequences).
# - pg_namespace (n):
#   Represents schemas/namespaces (e.g. 'public').
# - pg_attribute (a):
#   Represents columns in tables. We match `a.attnum = i.indkey[0]` to get the column name.
INDEX_SQL = """
SELECT t.relname, a.attname
FROM pg_index i
JOIN pg_class t ON t.oid = i.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = i.indkey[0]
WHERE n.nspname = %s
"""


def scan_schema(conn, schema="public"):
    """Scan the database schema and extract tables, foreign keys, and existing indexes.

    Parameters:
    -----------
    conn : psycopg2.extensions.connection
        An active PostgreSQL database connection.
    schema : str, default="public"
        The name of the database schema to analyze. Defaults to the standard "public" schema.

    Returns:
    --------
    tuple:
        A 3-element tuple containing:
        1. tables (dict):
           Mapping of table name (str) to a list of tuples containing
           (column_name, data_type).
           Example: {"users": [("id", "integer"), ("email", "text")]}
        2. foreign_keys (dict):
           Mapping of (table_name, column_name) to referenced_table_name.
           Example: {("orders", "user_id"): "users"}
        3. indexed (set):
           Set of (table_name, column_name) pairs that already have an index.
           Example: {("users", "id"), ("users", "email")}
    """
    # Use a database cursor with a context manager (with-statement)
    # to guarantee the cursor is properly closed when queries finish.
    with conn.cursor() as cur:
        # Step 1: Query all tables and columns
        cur.execute(COLUMNS_SQL, (schema,))
        tables = {}
        for table, column, dtype in cur.fetchall():
            # setdefault ensures a list exists for the table before appending
            tables.setdefault(table, []).append((column, dtype))

        # Step 2: Query all foreign key relationships
        cur.execute(FK_SQL, (schema,))
        # Map (child_table, child_column) -> referenced_parent_table
        foreign_keys = {(t, c): ref for t, c, ref in cur.fetchall()}

        # Step 3: Query all columns that already have indexes
        cur.execute(INDEX_SQL, (schema,))
        # Storing in a set enables O(1) constant time membership checks in recommend()
        indexed = {(t, c) for t, c in cur.fetchall()}

    return tables, foreign_keys, indexed