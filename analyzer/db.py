"""Database connection helper module for DbIndex Analyzer.

Supports both PostgreSQL (via psycopg2) and SQLite (via standard library sqlite3).
Provides safe connection handling, timeout management, and clear user-facing error messages.
"""

import os
import re
import sqlite3

# Try importing psycopg2 (optional if running in SQLite-only mode)
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class DatabaseConnection:
    """Unified wrapper around PostgreSQL and SQLite database connections."""

    def __init__(self, raw_conn, engine_type, db_name):
        self.raw_conn = raw_conn
        self.engine_type = engine_type  # 'postgresql' or 'sqlite'
        self.db_name = db_name

    def cursor(self):
        return self.raw_conn.cursor()

    def close(self):
        if self.raw_conn:
            self.raw_conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def connect_postgres(host, port, dbname, user, password):
    """Connect to a PostgreSQL database instance.

    Parameters:
    -----------
    host : str
        Hostname or IP address.
    port : int
        Port number (default 5432).
    dbname : str
        Database name.
    user : str
        Username.
    password : str
        Password.

    Returns:
    --------
    DatabaseConnection
        Unified database connection wrapper.
    """
    if not HAS_PSYCOPG2:
        raise ConnectionError("psycopg2 is not installed. Run 'pip install psycopg2-binary' to connect to PostgreSQL.")

    try:
        raw = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5,
        )
        return DatabaseConnection(raw, "postgresql", dbname)
    except psycopg2.OperationalError as e:
        # On Windows, 'localhost' resolves to IPv6 ::1 where pg_hba.conf IPv4 rules (127.0.0.1) don't apply.
        # Automatically retry connecting via IPv4 127.0.0.1 if host was 'localhost':
        if host and host.lower() == "localhost":
            try:
                raw = psycopg2.connect(
                    host="127.0.0.1",
                    port=port,
                    dbname=dbname,
                    user=user,
                    password=password,
                    connect_timeout=5,
                )
                return DatabaseConnection(raw, "postgresql", dbname)
            except psycopg2.OperationalError:
                pass
        raise ConnectionError(str(e).strip())


def connect_sqlite(db_path):
    """Connect to a SQLite database file.

    Parameters:
    -----------
    db_path : str
        Path to SQLite .db or .sqlite file.

    Returns:
    --------
    DatabaseConnection
        Unified database connection wrapper.
    """
    if not os.path.exists(db_path):
        raise ConnectionError(f"SQLite database file not found: '{db_path}'")

    try:
        raw = sqlite3.connect(db_path)
        # Enable foreign key constraint checking in SQLite
        raw.execute("PRAGMA foreign_keys = ON;")
        db_name = os.path.basename(db_path)
        return DatabaseConnection(raw, "sqlite", db_name)
    except Exception as e:
        raise ConnectionError(f"Failed to open SQLite database: {e}")


def connect_sql_file(sql_file_path):
    """Load an arbitrary SQL DDL schema file (MySQL, PostgreSQL, SQLite, SQL Server) into an in-memory database."""
    if not os.path.exists(sql_file_path):
        raise ConnectionError(f"SQL file not found: '{sql_file_path}'")

    try:
        with open(sql_file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        raw = sqlite3.connect(":memory:")
        raw.execute("PRAGMA foreign_keys = ON;")

        # Normalize common multi-engine SQL dialect differences for compatibility:
        # 1. PostgreSQL SERIAL -> INTEGER
        cleaned = re.sub(r"\bSERIAL\b", "INTEGER", content, flags=re.IGNORECASE)
        # 2. MySQL AUTO_INCREMENT -> AUTOINCREMENT
        cleaned = re.sub(r"\bAUTO_INCREMENT\b", "AUTOINCREMENT", cleaned, flags=re.IGNORECASE)
        # 3. Strip MySQL engine clauses like ENGINE=InnoDB DEFAULT CHARSET=...
        cleaned = re.sub(r"\)\s*ENGINE\s*=[^;]+;", ");", cleaned, flags=re.IGNORECASE)
        # 4. Strip PostgreSQL specific sequences or comments
        cleaned = re.sub(r"CREATE SEQUENCE[^;]+;", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"ALTER SEQUENCE[^;]+;", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"SELECT pg_catalog[^;]+;", "", cleaned, flags=re.IGNORECASE)

        # Remove line comments and block comments
        cleaned = re.sub(r"--[^\n]*", "", cleaned)
        cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)

        # Execute DDL statements
        statements = cleaned.split(";")
        for stmt in statements:
            s = stmt.strip()
            if s and re.match(r"^(CREATE|DROP|ALTER)\s+", s, re.IGNORECASE):
                try:
                    raw.execute(s + ";")
                except Exception:
                    pass

        raw.commit()
        db_name = os.path.basename(sql_file_path)
        return DatabaseConnection(raw, "sqlite", f"Schema: {db_name}")
    except Exception as e:
        raise ConnectionError(f"Failed to process SQL file: {e}")


def connect(host="localhost", port=5432, dbname=None, user=None, password=None, sqlite_path=None, sql_file_path=None):
    """Smart database connection dispatcher.

    If sql_file_path is specified, parses any SQL schema file in memory.
    If sqlite_path is specified, connects via SQLite.
    Otherwise connects via PostgreSQL.
    """
    if sql_file_path:
        return connect_sql_file(sql_file_path)
    if sqlite_path:
        return connect_sqlite(sqlite_path)
    return connect_postgres(host, port, dbname, user, password)
