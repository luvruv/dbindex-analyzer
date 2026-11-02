"""Database schema introspection module for DbIndex Analyzer.

Inspects database metadata from PostgreSQL system catalogs or SQLite PRAGMAs.
Extracts:
1. Tables, columns, and data types.
2. Primary key definitions.
3. Foreign key constraints.
4. Complete index definitions (including multi-column indexes, unique flags, and primary key indexes).
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional


@dataclass
class ColumnInfo:
    """Detailed information about a database column."""
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary: bool = False


@dataclass
class ForeignKeyInfo:
    """Detailed information about a foreign key relationship."""
    table: str
    column: str
    ref_table: str
    ref_column: str = "id"
    constraint_name: str = ""


@dataclass
class IndexInfo:
    """Detailed information about an existing database index."""
    name: str
    table: str
    columns: List[str]
    is_unique: bool = False
    is_primary: bool = False
    method: str = "btree"
    is_partial: bool = False
    sql_def: str = ""


@dataclass
class TableSchema:
    """Schema overview for a single database table."""
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_key: List[str] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)


@dataclass
class SchemaMetadata:
    """Comprehensive database schema metadata."""
    engine_type: str
    db_name: str
    tables: Dict[str, TableSchema]
    foreign_keys_map: Dict[Tuple[str, str], str]
    indexed_columns: Set[Tuple[str, str]]
    all_indexes: List[IndexInfo]


class SchemaResult(tuple):
    """Custom tuple returning (tables_dict, foreign_keys_map, indexed_set) for backward compatibility,
    while attaching full SchemaMetadata via the .metadata attribute.
    """
    def __new__(cls, tables_dict, foreign_keys_map, indexed_set, metadata: Optional[SchemaMetadata] = None):
        instance = super().__new__(cls, (tables_dict, foreign_keys_map, indexed_set))
        instance.metadata = metadata
        return instance


# ------------------------------------------------------------------------------
# PostgreSQL Queries
# ------------------------------------------------------------------------------

PG_COLUMNS_SQL = """
SELECT 
    c.table_name, 
    c.column_name, 
    c.data_type,
    c.is_nullable
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = %s AND t.table_type = 'BASE TABLE'
ORDER BY c.table_name, c.ordinal_position;
"""

PG_PK_SQL = """
SELECT
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = %s
ORDER BY tc.table_name, kcu.ordinal_position;
"""

PG_FK_SQL = """
SELECT 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS ref_table,
    ccu.column_name AS ref_column,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = %s
ORDER BY tc.table_name, kcu.ordinal_position;
"""

PG_INDEXES_SQL = """
SELECT
    t.relname AS table_name,
    i.relname AS index_name,
    idx.indisunique AS is_unique,
    idx.indisprimary AS is_primary,
    am.amname AS index_type,
    pg_get_indexdef(idx.indexrelid) AS index_def
FROM pg_index idx
JOIN pg_class t ON t.oid = idx.indrelid
JOIN pg_class i ON i.oid = idx.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
JOIN pg_am am ON am.oid = i.relam
WHERE n.nspname = %s AND t.relkind = 'r'
ORDER BY t.relname, i.relname;
"""


def _parse_pg_index_columns(index_def: str) -> List[str]:
    """Parse column names from PostgreSQL pg_get_indexdef output."""
    # Example: CREATE INDEX idx_users ON public.users USING btree (email, created_at)
    # or CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id)
    match = re.search(r"USING \w+\s*\((.+?)\)(?:\s+WHERE\s+(.+))?$", index_def, re.IGNORECASE)
    if not match:
        return []
    cols_part = match.group(1)
    # Split columns by comma (handling basic expressions or quotes)
    cols = []
    for c in cols_part.split(","):
        clean_col = c.strip().strip('"').split()[0]
        # remove parentheses if expression like (lower(email))
        clean_col = clean_col.strip("()")
        if clean_col:
            cols.append(clean_col)
    return cols


def scan_postgres_schema(conn, schema: str = "public", db_name: str = "postgresql") -> SchemaResult:
    """Scan PostgreSQL database catalogs and return full schema metadata."""
    cur = conn.cursor()
    try:
        # 1. Fetch Columns
        cur.execute(PG_COLUMNS_SQL, (schema,))
        tables_dict: Dict[str, List[Tuple[str, str]]] = {}
        table_schemas: Dict[str, TableSchema] = {}

        for table, column, dtype, is_null in cur.fetchall():
            tables_dict.setdefault(table, []).append((column, dtype))
            if table not in table_schemas:
                table_schemas[table] = TableSchema(name=table)
            table_schemas[table].columns.append(
                ColumnInfo(name=column, data_type=dtype, is_nullable=(is_null == "YES"))
            )

        # 2. Fetch Primary Keys
        cur.execute(PG_PK_SQL, (schema,))
        for table, column in cur.fetchall():
            if table in table_schemas:
                table_schemas[table].primary_key.append(column)
                for col in table_schemas[table].columns:
                    if col.name == column:
                        col.is_primary = True

        # 3. Fetch Foreign Keys
        cur.execute(PG_FK_SQL, (schema,))
        fk_map: Dict[Tuple[str, str], str] = {}
        for table, column, ref_table, ref_col, cname in cur.fetchall():
            fk_map[(table, column)] = ref_table
            if table in table_schemas:
                table_schemas[table].foreign_keys.append(
                    ForeignKeyInfo(
                        table=table,
                        column=column,
                        ref_table=ref_table,
                        ref_column=ref_col or "id",
                        constraint_name=cname or f"fk_{table}_{column}",
                    )
                )

        # 4. Fetch Indexes
        cur.execute(PG_INDEXES_SQL, (schema,))
        all_indexes: List[IndexInfo] = []
        indexed_columns: Set[Tuple[str, str]] = set()

        for table, index_name, is_unique, is_primary, itype, idef in cur.fetchall():
            cols = _parse_pg_index_columns(idef)
            is_partial = " WHERE " in (idef.upper() if idef else "")
            idx_obj = IndexInfo(
                name=index_name,
                table=table,
                columns=cols,
                is_unique=bool(is_unique),
                is_primary=bool(is_primary),
                method=itype or "btree",
                is_partial=is_partial,
                sql_def=idef or "",
            )
            all_indexes.append(idx_obj)
            if table in table_schemas:
                table_schemas[table].indexes.append(idx_obj)
            # Leading column is covered
            if cols:
                indexed_columns.add((table, cols[0]))

        metadata = SchemaMetadata(
            engine_type="postgresql",
            db_name=db_name,
            tables=table_schemas,
            foreign_keys_map=fk_map,
            indexed_columns=indexed_columns,
            all_indexes=all_indexes,
        )

        return SchemaResult(tables_dict, fk_map, indexed_columns, metadata)
    finally:
        cur.close()


def scan_sqlite_schema(conn, db_name: str = "sqlite") -> SchemaResult:
    """Scan SQLite schema using PRAGMAs and return full schema metadata."""
    cur = conn.cursor()
    try:
        # 1. Fetch tables
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        table_names = [row[0] for row in cur.fetchall()]

        tables_dict: Dict[str, List[Tuple[str, str]]] = {}
        table_schemas: Dict[str, TableSchema] = {}
        fk_map: Dict[Tuple[str, str], str] = {}
        all_indexes: List[IndexInfo] = []
        indexed_columns: Set[Tuple[str, str]] = set()

        for tname in table_names:
            tschema = TableSchema(name=tname)
            table_schemas[tname] = tschema
            tables_dict[tname] = []

            # Read columns
            cur.execute(f"PRAGMA table_info('{tname}');")
            # cid, name, type, notnull, dflt_value, pk
            for _, col_name, dtype, notnull, _, pk in cur.fetchall():
                dtype_str = dtype.lower() if dtype else "text"
                tables_dict[tname].append((col_name, dtype_str))
                is_pk = pk > 0
                if is_pk:
                    tschema.primary_key.append(col_name)
                    # Primary key in SQLite is automatically indexed
                    indexed_columns.add((tname, col_name))
                tschema.columns.append(
                    ColumnInfo(name=col_name, data_type=dtype_str, is_nullable=(notnull == 0), is_primary=is_pk)
                )

            # If PK exists, record virtual/implicit PK index
            if tschema.primary_key:
                all_indexes.append(
                    IndexInfo(
                        name=f"sqlite_autoindex_{tname}_pk",
                        table=tname,
                        columns=list(tschema.primary_key),
                        is_unique=True,
                        is_primary=True,
                        method="btree",
                        is_partial=False,
                        sql_def=f"PRIMARY KEY ({', '.join(tschema.primary_key)})",
                    )
                )

            # Read foreign keys
            cur.execute(f"PRAGMA foreign_key_list('{tname}');")
            # id, seq, table, from, to, on_update, on_delete, match
            for _, _, ref_table, col_from, col_to, _, _, _ in cur.fetchall():
                if col_from:
                    fk_map[(tname, col_from)] = ref_table
                    tschema.foreign_keys.append(
                        ForeignKeyInfo(
                            table=tname,
                            column=col_from,
                            ref_table=ref_table,
                            ref_column=col_to or "id",
                            constraint_name=f"fk_{tname}_{col_from}",
                        )
                    )

            # Read indexes
            cur.execute(f"PRAGMA index_list('{tname}');")
            # seq, name, unique, origin, partial
            for _, iname, is_uniq, origin, is_part in cur.fetchall():
                # Inspect indexed columns
                cur.execute(f"PRAGMA index_info('{iname}');")
                # seqno, cid, name
                idx_cols = [r[2] for r in sorted(cur.fetchall(), key=lambda x: x[0])]
                is_pk = (origin == "pk")
                idx_obj = IndexInfo(
                    name=iname,
                    table=tname,
                    columns=idx_cols,
                    is_unique=bool(is_uniq),
                    is_primary=is_pk,
                    method="btree",
                    is_partial=bool(is_part),
                    sql_def=f"INDEX {iname} ON {tname}({', '.join(idx_cols)})",
                )
                all_indexes.append(idx_obj)
                tschema.indexes.append(idx_obj)
                if idx_cols:
                    indexed_columns.add((tname, idx_cols[0]))

        metadata = SchemaMetadata(
            engine_type="sqlite",
            db_name=db_name,
            tables=table_schemas,
            foreign_keys_map=fk_map,
            indexed_columns=indexed_columns,
            all_indexes=all_indexes,
        )

        return SchemaResult(tables_dict, fk_map, indexed_columns, metadata)
    finally:
        cur.close()


def scan_schema(conn, schema: str = "public") -> SchemaResult:
    """Unified schema scanner. Dispatches to PostgreSQL or SQLite based on connection type."""
    # Check if connection is a DatabaseConnection wrapper
    engine = getattr(conn, "engine_type", None)
    db_name = getattr(conn, "db_name", "database")
    raw_conn = getattr(conn, "raw_conn", conn)

    if engine == "sqlite" or "sqlite3" in str(type(raw_conn)).lower():
        return scan_sqlite_schema(raw_conn, db_name)
    return scan_postgres_schema(raw_conn, schema, db_name)
