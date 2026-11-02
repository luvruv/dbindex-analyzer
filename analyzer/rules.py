"""Index recommendation rules engine and SQL generation module.

Evaluates database schema, columns, and existing indexes to:
1. Identify columns MISSING indexes (where indexes are needed).
2. Identify existing indexes that are NOT NEEDED (redundant, duplicate, or prefix-subsumed).
3. Classify existing healthy indexes.
4. Calculate comprehensive Database Schema Health Scores & Architectural Insights.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set, Optional, Any


@dataclass
class Suggestion:
    """Represents a recommended index to CREATE for an unindexed column."""
    table: str
    column: str
    rule: str
    reason: str
    speedup: str
    sql: str
    severity: str = "MEDIUM"  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    action: str = "CREATE"


@dataclass
class RedundantIndex:
    """Represents an existing index that is NOT NEEDED and should be DROPPED."""
    table: str
    index_name: str
    columns: List[str]
    issue_type: str  # "DUPLICATE", "REDUNDANT_PREFIX", "REDUNDANT_PK", "REDUNDANT_UNIQUE"
    reason: str
    impact: str
    sql: str
    severity: str = "HIGH_OVERHEAD"
    action: str = "DROP"


@dataclass
class HealthyIndex:
    """Represents an existing, well-designed index performing its intended job."""
    table: str
    index_name: str
    columns: List[str]
    category: str  # "PRIMARY_KEY", "UNIQUE_CONSTRAINT", "FOREIGN_KEY", "LOOKUP_SEARCH"
    is_unique: bool
    is_primary: bool
    description: str


@dataclass
class SchemaHealthMetrics:
    """Quantitative health metrics for the database schema."""
    total_tables: int
    total_columns: int
    total_existing_indexes: int
    tables_without_pk: List[str]
    pk_coverage_pct: float
    total_fks: int
    indexed_fks_count: int
    fk_coverage_pct: float
    missing_indexes_count: int
    redundant_indexes_count: int
    health_score: int  # 0 to 100
    health_grade: str  # 'A', 'B', 'C', 'D', 'F'
    insights: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Full comprehensive database schema and index analysis package."""
    db_name: str
    engine_type: str
    metrics: SchemaHealthMetrics
    missing_indexes: List[Suggestion]
    redundant_indexes: List[RedundantIndex]
    healthy_indexes: List[HealthyIndex]
    all_suggestions: List[Suggestion]  # alias for backward compatibility


# ------------------------------------------------------------------------------
# Heuristic Column Matching Rules (Ordered by Priority)
# ------------------------------------------------------------------------------
NAME_RULES = [
    # 1. Primary identifier column (e.g. 'id')
    ("id_column", r"^id$", "ID columns are used for lookups and joins", "50-100x", "HIGH"),

    # 2. Email addresses (e.g. 'email', 'user_email') - frequent login / user search
    ("email", r"email", "Email is often used in WHERE clauses (login, search)", "50-100x", "HIGH"),

    # 3. Phone numbers (e.g. 'phone', 'mobile_phone') - user search
    ("phone", r"phone|mobile", "Phone numbers are often searched directly", "20-50x", "HIGH"),

    # 4. Unique or lookup keys (e.g. username, slug, sku, product code, uuid)
    ("lookup_key", r"^(username|user_name|login|slug|code|sku|uuid|token)$",
     "Lookup keys are searched by exact value in APIs and queries", "20-50x", "HIGH"),

    # 5. Join keys: columns ending in '_id' (common foreign key naming convention)
    ("join_key", r"_id$", "Columns ending in _id are usually used in table JOINs", "10-50x", "HIGH"),

    # 6. Status and category flags: commonly used in WHERE filters
    ("status", r"^(status|state|type|category|role|priority)$",
     "Status/type columns are often filtered in WHERE clauses", "5-20x", "MEDIUM"),
]


def _ident(name: str, engine_type: str = "postgresql") -> str:
    """Safely quote a SQL identifier for PostgreSQL or SQLite."""
    if re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        return name
    return '"' + name.replace('"', '""') + '"'


def _make_create_sql(table: str, column: str, engine_type: str = "postgresql") -> str:
    """Build a valid, safe CREATE INDEX IF NOT EXISTS statement."""
    clean_name = f"idx_{table}_{column}"[:63]
    quoted_idx = _ident(clean_name, engine_type)
    quoted_table = _ident(table, engine_type)
    quoted_col = _ident(column, engine_type)
    return f"CREATE INDEX IF NOT EXISTS {quoted_idx} ON {quoted_table}({quoted_col});"


def _make_drop_sql(table: str, index_name: str, engine_type: str = "postgresql") -> str:
    """Build a safe DROP INDEX statement."""
    quoted_idx = _ident(index_name, engine_type)
    if engine_type == "postgresql":
        # In PostgreSQL, CONCURRENTLY drops index without locking concurrent reads/writes
        return f"DROP INDEX CONCURRENTLY IF EXISTS {quoted_idx};"
    return f"DROP INDEX IF EXISTS {quoted_idx};"


def _match_rule(table: str, column: str, dtype: str, foreign_keys: Dict[Tuple[str, str], str]):
    """Match a column against missing index heuristics."""
    # Priority 1: Official Foreign Key constraint
    if (table, column) in foreign_keys:
        ref = foreign_keys[(table, column)]
        return ("foreign_key", f"Foreign key referencing '{ref}'; speeds up JOINs and prevents lock escalations on parent deletes", "10-100x", "CRITICAL")

    # Priority 2: Column name heuristics
    for rule, pattern, reason, speedup, severity in NAME_RULES:
        if re.search(pattern, column.lower()):
            return (rule, reason, speedup, severity)

    # Priority 3: Date & Timestamp columns
    if dtype.startswith("timestamp") or dtype.startswith("date") or dtype == "datetime":
        return ("date_column", "Date/time columns are heavily used in range filters (BETWEEN) and ORDER BY sorting", "5-20x", "MEDIUM")

    return None


def detect_redundant_indexes(all_indexes: List[Any], engine_type: str = "postgresql") -> List[RedundantIndex]:
    """Inspect existing indexes to detect duplicates, redundant prefixes, and unnecessary PK indexes.

    Rules applied:
    1. Exact Duplicate: Two indexes on the exact same table with the exact same ordered columns.
    2. Redundant Prefix: Index A on (X) when Index B already exists on (X, Y).
    3. Redundant on Primary Key: A secondary index created on a primary key column.
    """
    redundancies: List[RedundantIndex] = []

    # Group indexes by table
    by_table: Dict[str, List[Any]] = {}
    for idx in all_indexes:
        # Ignore indexes without columns (e.g. specialized expressions)
        if getattr(idx, "columns", None):
            by_table.setdefault(idx.table, []).append(idx)

    for table, indexes in by_table.items():
        # Find Primary Key columns
        pk_cols: Set[str] = set()
        for idx in indexes:
            if getattr(idx, "is_primary", False) and len(idx.columns) == 1:
                pk_cols.add(idx.columns[0])

        seen_signatures: Dict[str, Any] = {}

        for idx in indexes:
            # Skip SQLite internal autoindexes or PG primary keys from being dropped
            if getattr(idx, "is_primary", False) or idx.name.startswith("sqlite_autoindex"):
                continue

            col_tuple = tuple(idx.columns)
            col_sig = ",".join(col_tuple)

            # Check 1: Redundant Index on Primary Key
            if len(idx.columns) == 1 and idx.columns[0] in pk_cols and not idx.is_unique:
                redundancies.append(
                    RedundantIndex(
                        table=table,
                        index_name=idx.name,
                        columns=idx.columns,
                        issue_type="REDUNDANT_PK",
                        reason=f"Column '{idx.columns[0]}' is already the Primary Key. Primary Keys are automatically indexed with a unique B-Tree index by the database.",
                        impact="Consumes unnecessary RAM and disk space, and slows down every INSERT and UPDATE on this table.",
                        sql=_make_drop_sql(table, idx.name, engine_type),
                        severity="HIGH_OVERHEAD",
                    )
                )
                continue

            # Check 2: Exact Duplicate Index
            if col_sig in seen_signatures:
                existing = seen_signatures[col_sig]
                redundancies.append(
                    RedundantIndex(
                        table=table,
                        index_name=idx.name,
                        columns=idx.columns,
                        issue_type="DUPLICATE",
                        reason=f"Exact duplicate of index '{existing.name}' on ({col_sig}). Both indexes maintain the exact same B-Tree structure.",
                        impact="Doubles write amplification on INSERT/UPDATE/DELETE operations with 0% query performance benefit.",
                        sql=_make_drop_sql(table, idx.name, engine_type),
                        severity="CRITICAL_OVERHEAD",
                    )
                )
                continue
            else:
                seen_signatures[col_sig] = idx

        # Check 3: Redundant Prefix Index (Composite Subsumption)
        # If idx1 has columns [A] and idx2 has columns [A, B], idx1 is redundant because idx2 handles queries on A.
        for idx in indexes:
            if idx.is_primary or idx.is_unique or len(idx.columns) != 1:
                continue

            single_col = idx.columns[0]
            for other in indexes:
                if other.name == idx.name or other.is_partial:
                    continue
                # If 'other' has multi-columns and begins with 'single_col'
                if len(other.columns) > 1 and other.columns[0] == single_col:
                    redundancies.append(
                        RedundantIndex(
                            table=table,
                            index_name=idx.name,
                            columns=idx.columns,
                            issue_type="REDUNDANT_PREFIX",
                            reason=f"Redundant leading prefix of composite index '{other.name}' on ({', '.join(other.columns)}). The composite index satisfies any filter on '{single_col}'.",
                            impact=f"Redundant index maintenance during writes. Safe to drop because the composite index covers queries on '{single_col}'.",
                            sql=_make_drop_sql(table, idx.name, engine_type),
                            severity="HIGH_OVERHEAD",
                        )
                    )
                    break

    return redundancies


def classify_healthy_indexes(all_indexes: List[Any], redundant_indexes: List[RedundantIndex]) -> List[HealthyIndex]:
    """Identify and catalog existing healthy indexes that provide genuine value."""
    redundant_names = {r.index_name for r in redundant_indexes}
    healthy: List[HealthyIndex] = []

    for idx in all_indexes:
        if idx.name in redundant_names:
            continue

        if getattr(idx, "is_primary", False):
            category = "PRIMARY_KEY"
            desc = "Enforces row uniqueness and provides instant O(1) single-row lookups."
        elif getattr(idx, "is_unique", False):
            category = "UNIQUE_CONSTRAINT"
            desc = "Guarantees uniqueness of values and provides rapid exact-match lookups."
        elif len(idx.columns) > 1:
            category = "COMPOSITE_INDEX"
            desc = f"Accelerates multi-column queries filtering or sorting on ({', '.join(idx.columns)})."
        else:
            category = "LOOKUP_SEARCH"
            desc = f"Accelerates point queries and joins on '{idx.columns[0] if idx.columns else 'column'}'."

        healthy.append(
            HealthyIndex(
                table=idx.table,
                index_name=idx.name,
                columns=idx.columns,
                category=category,
                is_unique=getattr(idx, "is_unique", False),
                is_primary=getattr(idx, "is_primary", False),
                description=desc,
            )
        )

    return healthy


def compute_health_score(
    tables: Dict[str, Any],
    foreign_keys: Dict[Tuple[str, str], str],
    indexed: Set[Tuple[str, str]],
    missing: List[Suggestion],
    redundant: List[RedundantIndex],
    metadata: Optional[Any] = None,
) -> SchemaHealthMetrics:
    """Compute overall schema and indexing health score (0-100) and qualitative insights."""
    total_tables = len(tables)
    total_columns = sum(len(cols) for cols in tables.values())
    total_fks = len(foreign_keys)

    # Tables without primary keys
    tables_without_pk = []
    if metadata and hasattr(metadata, "tables"):
        for tname, tschema in metadata.tables.items():
            if not tschema.primary_key:
                tables_without_pk.append(tname)
    else:
        # Fallback heuristic: check if any column is named 'id' and in indexed
        for tname, cols in tables.items():
            col_names = [c[0].lower() for c in cols]
            if "id" not in col_names and f"{tname}_id" not in col_names:
                tables_without_pk.append(tname)

    pk_coverage_pct = (
        round(((total_tables - len(tables_without_pk)) / total_tables) * 100, 1) if total_tables > 0 else 100.0
    )

    # FK index coverage
    indexed_fks = sum(1 for fk in foreign_keys if fk in indexed)
    fk_coverage_pct = round((indexed_fks / total_fks) * 100, 1) if total_fks > 0 else 100.0

    # Start from base 100 and apply deductions
    score = 100

    # Critical penalty: unindexed foreign keys (-6 points per unindexed FK, up to -30)
    unindexed_fks = total_fks - indexed_fks
    score -= min(30, unindexed_fks * 6)

    # Penalty for missing PKs (-10 points per missing PK, up to -25)
    score -= min(25, len(tables_without_pk) * 10)

    # Penalty for redundant / duplicate indexes (-4 points each, up to -20)
    score -= min(20, len(redundant) * 4)

    # Penalty for missing high priority search/email/lookup indexes (-3 points each, up to -15)
    high_missing = sum(1 for s in missing if s.severity in ("CRITICAL", "HIGH"))
    score -= min(15, high_missing * 3)

    score = max(10, min(100, score))

    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 45:
        grade = "D"
    else:
        grade = "F"

    # Generate human insights
    insights = []
    if unindexed_fks > 0:
        insights.append(f"⚠️ {unindexed_fks} Foreign Key(s) lack an index. Unindexed FKs cause lock contention and full-table scans during JOINs.")
    else:
        insights.append("✅ Excellent: 100% of defined Foreign Keys have backing indexes.")

    if tables_without_pk:
        insights.append(f"⚠️ {len(tables_without_pk)} table(s) lack a Primary Key ({', '.join(tables_without_pk[:3])}). Relational tables should always define a Primary Key.")
    else:
        insights.append("✅ All tables properly define a Primary Key.")

    if redundant:
        insights.append(f"⚠️ Found {len(redundant)} redundant or duplicate index(es). Dropping them will reclaim disk space and reduce write latency.")
    else:
        insights.append("✅ Zero duplicate or redundant indexes detected.")

    if missing:
        insights.append(f"💡 Identified {len(missing)} missing index recommendation(s) to optimize query read performance.")

    total_existing = len(metadata.all_indexes) if metadata and hasattr(metadata, "all_indexes") else len(indexed)

    return SchemaHealthMetrics(
        total_tables=total_tables,
        total_columns=total_columns,
        total_existing_indexes=total_existing,
        tables_without_pk=tables_without_pk,
        pk_coverage_pct=pk_coverage_pct,
        total_fks=total_fks,
        indexed_fks_count=indexed_fks,
        fk_coverage_pct=fk_coverage_pct,
        missing_indexes_count=len(missing),
        redundant_indexes_count=len(redundant),
        health_score=score,
        health_grade=grade,
        insights=insights,
    )


def recommend(tables, foreign_keys, indexed, metadata: Optional[Any] = None, engine_type: str = "postgresql") -> List[Suggestion]:
    """Analyze all tables and return missing index recommendations.

    Maintains 100% backward compatibility with older callers, while accepting optional metadata.
    """
    suggestions: List[Suggestion] = []

    for table, columns in tables.items():
        for column, dtype in columns:
            # Skip columns that already have an index
            if (table, column) in indexed:
                continue

            match = _match_rule(table, column, dtype, foreign_keys)
            if match:
                rule, reason, speedup, severity = match
                sql = _make_create_sql(table, column, engine_type)
                suggestions.append(
                    Suggestion(
                        table=table,
                        column=column,
                        rule=rule,
                        reason=reason,
                        speedup=speedup,
                        sql=sql,
                        severity=severity,
                        action="CREATE",
                    )
                )

    # Sort suggestions by severity priority: CRITICAL -> HIGH -> MEDIUM -> LOW
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    suggestions.sort(key=lambda s: priority_order.get(s.severity, 99))
    return suggestions


def analyze_schema_comprehensive(
    tables: Dict[str, Any],
    foreign_keys: Dict[Tuple[str, str], str],
    indexed: Set[Tuple[str, str]],
    metadata: Optional[Any] = None,
    engine_type: str = "postgresql",
    db_name: str = "database",
) -> AnalysisResult:
    """Full-spectrum database schema and index analysis.

    Evaluates both MISSING indexes and REDUNDANT indexes, classifies healthy indexes,
    and calculates complete schema health metrics.
    """
    # 1. Missing Indexes
    missing = recommend(tables, foreign_keys, indexed, metadata, engine_type)

    # 2. Redundant Indexes
    all_indexes = metadata.all_indexes if metadata and hasattr(metadata, "all_indexes") else []
    redundant = detect_redundant_indexes(all_indexes, engine_type)

    # 3. Healthy Indexes
    healthy = classify_healthy_indexes(all_indexes, redundant)

    # 4. Health Metrics
    metrics = compute_health_score(tables, foreign_keys, indexed, missing, redundant, metadata)

    return AnalysisResult(
        db_name=db_name,
        engine_type=engine_type,
        metrics=metrics,
        missing_indexes=missing,
        redundant_indexes=redundant,
        healthy_indexes=healthy,
        all_suggestions=missing,
    )
