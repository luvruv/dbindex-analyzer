"""Index recommendation rules engine and SQL generation module.

This module evaluates database tables and columns against heuristic rules to
recommend missing indexes that can dramatically improve query performance.
It also formats clean, safe PostgreSQL `CREATE INDEX` SQL statements.
"""

# ------------------------------------------------------------------------------
# Package / Library Imports:
# ------------------------------------------------------------------------------
# re:
# Python's built-in Regular Expressions module.
# Used to match column names against common naming conventions and patterns
# (e.g., checking if a column ends with '_id' or contains 'email').
import re

# dataclasses.dataclass:
# A decorator from Python's standard library (introduced in Python 3.7).
# Automatically generates boilerplate special methods (such as __init__, __repr__,
# and __eq__) for classes that primarily store data.
from dataclasses import dataclass


@dataclass
class Suggestion:
    """Represents a single recommended index for a database column.

    Attributes:
    -----------
    table : str
        The name of the table containing the column.
    column : str
        The name of the column to be indexed.
    rule : str
        A short identifier for the matching rule (e.g. 'foreign_key', 'email', 'status').
    reason : str
        A beginner-friendly explanation of why the index is beneficial.
    speedup : str
        An estimated query acceleration factor (e.g. '50-100x', '10-50x').
    sql : str
        The exact PostgreSQL CREATE INDEX command ready for execution.
    """
    table: str
    column: str
    rule: str
    reason: str
    speedup: str
    sql: str


# ------------------------------------------------------------------------------
# Column Name Heuristic Rules
# ------------------------------------------------------------------------------
# Each rule is a tuple: (rule_name, regex_pattern, human_readable_reason, estimated_speedup).
# They are evaluated in order of appearance.
NAME_RULES = [
    # 1. Primary identifier column (e.g. 'id')
    ("id_column", r"^id$", "ID columns are used for lookups and joins", "50-100x"),

    # 2. Email addresses (e.g. 'email', 'user_email') - frequent login / user search
    ("email", r"email", "Email is often used in WHERE clauses (login, search)", "50-100x"),

    # 3. Phone numbers (e.g. 'phone', 'mobile_phone') - user search
    ("phone", r"phone|mobile", "Phone numbers are often searched directly", "20-50x"),

    # 4. Unique or lookup keys (e.g. username, slug, sku, product code)
    ("lookup_key", r"^(username|user_name|login|slug|code|sku)$",
     "Lookup keys are searched by exact value", "20-50x"),

    # 5. Join keys: columns ending in '_id' (common foreign key naming convention)
    ("join_key", r"_id$", "Columns ending in _id are usually used in JOINs", "10-50x"),

    # 6. Status and category flags: commonly used in WHERE filters (e.g., WHERE status = 'active')
    ("status", r"^(status|state|type|category)$",
     "Status/type columns are often filtered in WHERE clauses", "5-20x"),
]


def _ident(name):
    """Safely quote a SQL identifier (table, column, or index name) for PostgreSQL.

    In PostgreSQL, unquoted identifiers are automatically folded to lowercase.
    If an identifier contains uppercase letters, spaces, or special characters,
    it must be enclosed in double quotes (e.g., "Order Details").
    Any internal double quotes are escaped as `""`.

    Parameters:
    -----------
    name : str
        The identifier name to check and quote if necessary.

    Returns:
    --------
    str
        The safely quoted identifier, or the raw name if it is standard lowercase.
    """
    # Regex matches standard unquoted names: starts with lowercase letter/underscore,
    # followed by lowercase letters, numbers, or underscores.
    if re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        return name
    # Otherwise, quote with double quotes and escape any embedded double quotes
    return '"' + name.replace('"', '""') + '"'


def _make_sql(table, column):
    """Build a valid, safe CREATE INDEX IF NOT EXISTS statement for a column.

    PostgreSQL has an identifier limit of 63 bytes (NAMEDATALEN - 1 = 63).
    Index names longer than 63 characters are automatically truncated by PostgreSQL,
    so we slice `[:63]` to ensure clean, predictable naming.

    Parameters:
    -----------
    table : str
        Name of the table.
    column : str
        Name of the column.

    Returns:
    --------
    str
        A formatted SQL query string, e.g.:
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
    """
    # Build standard index name: idx_<table_name>_<column_name>
    name = f"idx_{table}_{column}"[:63]
    return f"CREATE INDEX IF NOT EXISTS {_ident(name)} ON {_ident(table)}({_ident(column)});"


def _match_rule(table, column, dtype, foreign_keys):
    """Match a column against the index recommendation rules in order of priority.

    Evaluation Priority:
    1. Foreign Key Constraints:
       Highest priority because unindexed foreign keys cause slow table locks and joins.
    2. Column Name Patterns:
       Matches common naming conventions (email, phone, status, etc.).
    3. Date & Timestamp Data Types:
       Columns storing dates/timestamps are frequently used for range queries and sorting.

    Parameters:
    -----------
    table : str
        The table name.
    column : str
        The column name.
    dtype : str
        The SQL data type of the column (e.g., 'integer', 'text', 'timestamp without time zone').
    foreign_keys : dict
        Mapping of (table, column) -> referenced_parent_table.

    Returns:
    --------
    tuple or None:
        A (rule_name, reason, speedup) tuple if a rule matched, or None if no rule applied.
    """
    # Priority 1: Check if this column is part of an official Foreign Key constraint
    if (table, column) in foreign_keys:
        ref = foreign_keys[(table, column)]
        return ("foreign_key", f"Foreign key to {ref}; speeds up JOINs and deletes", "10-100x")

    # Priority 2: Check column name against heuristic regular expressions
    for rule, pattern, reason, speedup in NAME_RULES:
        if re.search(pattern, column.lower()):
            return (rule, reason, speedup)

    # Priority 3: Check column data type for dates / timestamps
    if dtype.startswith("timestamp") or dtype == "date":
        return ("date_column", "Date columns are used in range filters and sorting", "5-20x")

    # No rule matched
    return None


def recommend(tables, foreign_keys, indexed):
    """Analyze all tables and return index recommendations for unindexed columns.

    Parameters:
    -----------
    tables : dict
        Mapping of table name -> list of (column_name, data_type) tuples.
    foreign_keys : dict
        Mapping of (table, column) -> referenced_table.
    indexed : set
        Set of (table, column) tuples that already have an index in the database.

    Returns:
    --------
    list[Suggestion]
        A list of Suggestion objects containing recommended indexes and SQL.
    """
    suggestions = []

    # Iterate through every table and its columns
    for table, columns in tables.items():
        for column, dtype in columns:
            # Skip columns that already have an index (avoids duplicate indexes)
            if (table, column) in indexed:
                continue

            # Evaluate whether this column matches any indexing rule
            match = _match_rule(table, column, dtype, foreign_keys)
            if match:
                rule, reason, speedup = match
                sql = _make_sql(table, column)
                suggestions.append(Suggestion(table, column, rule, reason, speedup, sql))

    return suggestions