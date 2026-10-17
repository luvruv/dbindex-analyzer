"""Reads tables, columns, foreign keys and existing indexes from PostgreSQL."""

COLUMNS_SQL = """
SELECT c.table_name, c.column_name, c.data_type
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = %s AND t.table_type = 'BASE TABLE'
ORDER BY c.table_name, c.ordinal_position
"""

FK_SQL = """
SELECT tc.table_name, kcu.column_name, ccu.table_name AS ref_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s
"""

# First column of every existing index (includes primary keys)
INDEX_SQL = """
SELECT t.relname, a.attname
FROM pg_index i
JOIN pg_class t ON t.oid = i.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = i.indkey[0]
WHERE n.nspname = %s
"""


def scan_schema(conn, schema="public"):
    """Return (tables, foreign_keys, indexed).

    tables:       {table: [(column, data_type), ...]}
    foreign_keys: {(table, column): referenced_table}
    indexed:      {(table, column), ...} columns that already have an index
    """
    with conn.cursor() as cur:
        cur.execute(COLUMNS_SQL, (schema,))
        tables = {}
        for table, column, dtype in cur.fetchall():
            tables.setdefault(table, []).append((column, dtype))

        cur.execute(FK_SQL, (schema,))
        foreign_keys = {(t, c): ref for t, c, ref in cur.fetchall()}

        cur.execute(INDEX_SQL, (schema,))
        indexed = {(t, c) for t, c in cur.fetchall()}

    return tables, foreign_keys, indexed