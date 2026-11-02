"""Unit tests for the DbIndex Analyzer recommendation rules engine.

This module uses `pytest` to test the recommendation logic in `analyzer.rules`.

Why we use mock data in unit tests:
-----------------------------------
Instead of requiring a live, running PostgreSQL database to execute these tests,
we pass synthetic Python dictionaries (`TABLES`, `FKS`) that mirror the data structures
returned by `analyzer.schema.scan_schema()`. This ensures tests run in milliseconds,
remain completely isolated, and can be verified in any environment (including CI/CD).
"""

# ------------------------------------------------------------------------------
# Package / Module Imports:
# ------------------------------------------------------------------------------
# recommend:
# The core function in analyzer.rules that evaluates columns against heuristics
# and returns index suggestions.
from analyzer.rules import recommend

# ------------------------------------------------------------------------------
# Mock Test Data Fixtures
# ------------------------------------------------------------------------------
# TABLES: Simulates the schema of two relational database tables:
# 1. `users`: Contains columns with various naming patterns (id, email, phone, bio)
#    and a timestamp column (created_at).
# 2. `orders`: Contains an id, a foreign key column (user_id), and a status column.
TABLES = {
    "users": [
        ("id", "integer"),
        ("email", "text"),
        ("phone", "text"),
        ("created_at", "timestamp without time zone"),
        ("bio", "text"),
    ],
    "orders": [
        ("id", "integer"),
        ("user_id", "integer"),
        ("status", "text"),
    ],
}

# FKS: Simulates a foreign key constraint linking orders.user_id -> users table.
FKS = {("orders", "user_id"): "users"}


def test_recommends_expected_columns():
    """Verify that columns matching known patterns are recommended for indexing.

    Expected matches:
    - users.email       -> Matches 'email' rule
    - users.phone       -> Matches 'phone' rule
    - users.created_at  -> Matches 'date_column' rule
    - orders.user_id    -> Matches 'foreign_key' rule
    - orders.status     -> Matches 'status' rule

    Expected non-matches:
    - users.bio         -> General text column that does not match any indexing heuristic
    """
    # Run recommendation with an empty set of existing indexes (set())
    got = {(s.table, s.column) for s in recommend(TABLES, FKS, set())}

    # Assert that high-value columns are recommended
    assert ("users", "email") in got
    assert ("users", "phone") in got
    assert ("users", "created_at") in got
    assert ("orders", "user_id") in got
    assert ("orders", "status") in got

    # Assert that general columns without indexing patterns are skipped
    assert ("users", "bio") not in got


def test_skips_already_indexed():
    """Verify that columns that already have an index are not recommended again.

    Duplicate indexes waste storage and slow down INSERT/UPDATE operations.
    The analyzer should gracefully skip any column present in the `indexed` set.
    """
    # Simulate that `users.email` is already indexed in the database
    already_indexed = {("users", "email")}
    got = {(s.table, s.column) for s in recommend(TABLES, FKS, already_indexed)}

    # Assert that users.email is omitted from recommendations
    assert ("users", "email") not in got


def test_sql_is_correct():
    """Verify that generated CREATE INDEX statements have the correct syntax.

    Checks for valid PostgreSQL DDL syntax, standard index naming conventions (idx_table_column),
    and the idempotent `IF NOT EXISTS` clause.
    """
    sqls = {s.sql for s in recommend(TABLES, FKS, set())}
    expected_sql = "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);"
    assert expected_sql in sqls


def test_at_least_five_rule_types():
    """Verify that recommendations trigger across at least 5 distinct rule types.

    Ensures that our mock data exercises multiple distinct heuristics:
    e.g., 'id_column', 'email', 'phone', 'date_column', 'foreign_key', 'status'.
    """
    rules = {s.rule for s in recommend(TABLES, FKS, set())}
    assert len(rules) >= 5


# ------------------------------------------------------------------------------
# Advanced Unit Tests: Redundant Indexes, Health Scoring, and SQLite Engine
# ------------------------------------------------------------------------------
from analyzer.schema import IndexInfo
from analyzer.rules import (
    detect_redundant_indexes,
    classify_healthy_indexes,
    compute_health_score,
    analyze_schema_comprehensive,
)
from analyzer.generator import generate_demo_database
from analyzer.db import connect_sqlite
from analyzer.schema import scan_sqlite_schema


def test_detects_duplicate_indexes():
    """Verify detection of exact duplicate indexes on identical columns."""
    indexes = [
        IndexInfo(name="idx_orders_user_1", table="orders", columns=["user_id"]),
        IndexInfo(name="idx_orders_user_2", table="orders", columns=["user_id"]),
    ]
    redundant = detect_redundant_indexes(indexes)
    assert len(redundant) == 1
    assert redundant[0].issue_type == "DUPLICATE"
    assert redundant[0].index_name == "idx_orders_user_2"
    assert "DROP INDEX" in redundant[0].sql


def test_detects_redundant_prefix_indexes():
    """Verify that a single-column index is flagged redundant when a composite index already covers it."""
    indexes = [
        IndexInfo(name="idx_orders_composite", table="orders", columns=["user_id", "order_date"]),
        IndexInfo(name="idx_orders_user_single", table="orders", columns=["user_id"]),
    ]
    redundant = detect_redundant_indexes(indexes)
    assert len(redundant) == 1
    assert redundant[0].issue_type == "REDUNDANT_PREFIX"
    assert redundant[0].index_name == "idx_orders_user_single"


def test_detects_redundant_index_on_primary_key():
    """Verify that manual indexes created on primary keys are flagged as redundant."""
    indexes = [
        IndexInfo(name="users_pkey", table="users", columns=["id"], is_primary=True, is_unique=True),
        IndexInfo(name="idx_users_id_manual", table="users", columns=["id"], is_primary=False),
    ]
    redundant = detect_redundant_indexes(indexes)
    assert len(redundant) == 1
    assert redundant[0].issue_type == "REDUNDANT_PK"
    assert redundant[0].index_name == "idx_users_id_manual"


def test_schema_health_score_calculation():
    """Verify schema health scoring and deduction logic."""
    metrics = compute_health_score(
        tables=TABLES,
        foreign_keys=FKS,
        indexed=set(),
        missing=recommend(TABLES, FKS, set()),
        redundant=[],
    )
    assert 0 <= metrics.health_score <= 100
    assert metrics.health_grade in ["A", "B", "C", "D", "F"]
    assert len(metrics.insights) > 0


def test_demo_database_generation_and_sqlite_scan(tmp_path):
    """Verify that the schema generator creates a valid SQLite DB and scan_sqlite_schema analyzes it."""
    db_file = str(tmp_path / "test_demo.db")
    created_path = generate_demo_database(db_file)
    assert created_path == db_file

    conn = connect_sqlite(created_path)
    try:
        scan_res = scan_sqlite_schema(conn.raw_conn, "test_demo")
        tables, fks, indexed = scan_res
        metadata = getattr(scan_res, "metadata", None)
        assert len(tables) >= 5
        assert ("users", "email") in [c for cols in tables.values() for c in cols] or any("email" == c[0] for c in tables.get("users", []))

        # Comprehensive analysis should find both missing and redundant indexes
        analysis = analyze_schema_comprehensive(
            tables, fks, indexed, metadata=metadata, engine_type="sqlite", db_name="test_demo"
        )
        assert len(analysis.missing_indexes) > 0
        assert len(analysis.redundant_indexes) > 0
    finally:
        conn.close()
