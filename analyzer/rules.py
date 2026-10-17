"""Rules that decide which columns need indexes, and the SQL for them."""
import re
from dataclasses import dataclass


@dataclass
class Suggestion:
    table: str
    column: str
    rule: str
    reason: str
    speedup: str
    sql: str


# (rule name, column-name regex, reason, estimated speedup) - checked in order
NAME_RULES = [
    ("id_column", r"^id$", "ID columns are used for lookups and joins", "50-100x"),
    ("email", r"email", "Email is often used in WHERE clauses (login, search)", "50-100x"),
    ("phone", r"phone|mobile", "Phone numbers are often searched directly", "20-50x"),
    ("lookup_key", r"^(username|user_name|login|slug|code|sku)$",
     "Lookup keys are searched by exact value", "20-50x"),
    ("join_key", r"_id$", "Columns ending in _id are usually used in JOINs", "10-50x"),
    ("status", r"^(status|state|type|category)$",
     "Status/type columns are often filtered in WHERE clauses", "5-20x"),
]


def _ident(name):
    """Quote an identifier only if it is not a plain lowercase name."""
    return name if re.fullmatch(r"[a-z_][a-z0-9_]*", name) else '"' + name.replace('"', '""') + '"'


def _make_sql(table, column):
    """Build a valid CREATE INDEX statement (index name limited to 63 chars)."""
    name = f"idx_{table}_{column}"[:63]
    return f"CREATE INDEX IF NOT EXISTS {_ident(name)} ON {_ident(table)}({_ident(column)});"


def _match_rule(table, column, dtype, foreign_keys):
    """Return (rule, reason, speedup) for the first matching rule, or None."""
    if (table, column) in foreign_keys:
        ref = foreign_keys[(table, column)]
        return ("foreign_key", f"Foreign key to {ref}; speeds up JOINs and deletes", "10-100x")
    for rule, pattern, reason, speedup in NAME_RULES:
        if re.search(pattern, column.lower()):
            return (rule, reason, speedup)
    if dtype.startswith("timestamp") or dtype == "date":
        return ("date_column", "Date columns are used in range filters and sorting", "5-20x")
    return None


def recommend(tables, foreign_keys, indexed):
    """Return a list of Suggestion for columns that are not yet indexed."""
    suggestions = []
    for table, columns in tables.items():
        for column, dtype in columns:
            if (table, column) in indexed:
                continue
            match = _match_rule(table, column, dtype, foreign_keys)
            if match:
                rule, reason, speedup = match
                suggestions.append(Suggestion(table, column, rule, reason, speedup,
                                              _make_sql(table, column)))
    return suggestions