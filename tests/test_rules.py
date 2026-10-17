from analyzer.rules import recommend

TABLES = {
    "users": [("id", "integer"), ("email", "text"), ("phone", "text"),
              ("created_at", "timestamp without time zone"), ("bio", "text")],
    "orders": [("id", "integer"), ("user_id", "integer"), ("status", "text")],
}
FKS = {("orders", "user_id"): "users"}


def test_recommends_expected_columns():
    got = {(s.table, s.column) for s in recommend(TABLES, FKS, set())}
    assert ("users", "email") in got
    assert ("users", "phone") in got
    assert ("users", "created_at") in got
    assert ("orders", "user_id") in got
    assert ("orders", "status") in got
    assert ("users", "bio") not in got


def test_skips_already_indexed():
    got = {(s.table, s.column) for s in recommend(TABLES, FKS, {("users", "email")})}
    assert ("users", "email") not in got


def test_sql_is_correct():
    sqls = {s.sql for s in recommend(TABLES, FKS, set())}
    assert "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);" in sqls


def test_at_least_five_rule_types():
    rules = {s.rule for s in recommend(TABLES, FKS, set())}
    assert len(rules) >= 5