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