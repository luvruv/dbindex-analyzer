# DbIndex Analyzer 🚀

> **Production Database Schema & Index Optimization Engine**  
> Analyzes PostgreSQL and SQLite databases, discovers missing indexes, flags redundant and duplicate indexes, calculates schema health scores, and generates ready-to-deploy SQL migration scripts alongside an interactive HTML executive dashboard.

---

## 🌟 Key Capabilities

- **Multi-Database Support (General Project)**: Audits both live **PostgreSQL** instances and standalone **SQLite** database files. Works on any database without external servers required.
- **Dual Index Recommendation Engine**:
  - **Missing Indexes (CREATE)**: Identifies unindexed Foreign Keys, unique lookup keys, search columns, and timestamp range filters with estimated query speedups (10x–100x).
  - **Redundant Indexes (DROP)**: Flags exact duplicates, redundant composite prefix indexes, and unnecessary secondary indexes on Primary Keys to reclaim storage and eliminate write amplification.
- **Database Schema Knowledge & Health Score**:
  - Calculates an overall Schema Health Score (0–100) and letter grade (A–F).
  - Audits Primary Key coverage and Foreign Key index coverage.
  - Generates clear, non-technical architectural explanations suitable for engineering reviews and academic presentations.
- **Interactive Production Dashboard (`report.html`)**:
  - Executive KPI metric cards, health score ring, and architectural observation insights.
  - Searchable, filterable tables for Missing Indexes, Redundant Indexes, Healthy Indexes, and Table Schema Catalog.
  - Built-in SQL Workbench with one-click clipboard copy for migration scripts.
- **Executable Migration Scripts (`recommendations.sql`)**:
  - Fully commented, production-safe `CREATE INDEX IF NOT EXISTS` and `DROP INDEX [CONCURRENTLY]` statements.
- **Built-in Instant Demo (`--demo`)**:
  - Instantly generates a realistic e-commerce database with intentional schema flaws and runs a full live audit in under a second with zero setup.

---

## 🚀 Quick Start & Usage

### 1. Instant Demo (Zero Setup Required)
Run a full audit on an automatically generated sample database:
```bash
python index_analyzer.py --demo
```

### 2. Audit Any SQLite Database File
```bash
python index_analyzer.py --sqlite path/to/database.db
```

### 3. Audit a Live PostgreSQL Database
```bash
python index_analyzer.py --host localhost --port 5432 --db mydatabase --user postgres
```
*(If connection parameters are omitted, the CLI interactively prompts for them, with password input masked for security).*

### Command Line Options

| Option | Description | Default |
|---|---|---|
| `--demo` | Generate synthetic database and run instant audit | `False` |
| `--sqlite` | Path to SQLite `.db` file | `None` |
| `--host` | PostgreSQL host address | `localhost` |
| `--port` | PostgreSQL port | `5432` |
| `--db` | PostgreSQL database name | Prompted |
| `--user` | PostgreSQL username | Prompted |
| `--password` | PostgreSQL password | Prompted (masked) |
| `--schema` | PostgreSQL schema name | `public` |
| `--sql-out` | Path for generated SQL migration script | `recommendations.sql` |
| `--html-out` | Path for interactive HTML dashboard | `report.html` |

---

## 📊 Real Console Output

```text
[+] Generating realistic sample database with intentional index flaws...
    Demo database created at: C:\Users\jaind\Projects\dbindex-analyzer\demo_store.db

[OK] Connected to SQLITE database 'demo_store.db'
[OK] Introspected 6 tables, 31 columns total

------------------------------------------------------------
DATABASE HEALTH SCORE: 51/100 (Grade D)
  * Primary Key Coverage:     83.3%
  * Foreign Key Indexing:     60.0%
  * Missing Indexes to Add:   11
  * Redundant Indexes to Drop:3
------------------------------------------------------------

[*] MISSING INDEXES (Action: CREATE):
  [CRITICAL] orders.user_id
    Reason:   Foreign key referencing 'users'; speeds up JOINs and prevents lock escalations
    Speedup:  10-100x
    Command:  CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);

  [HIGH] users.email
    Reason:   Email is often used in WHERE clauses (login, search)
    Speedup:  50-100x
    Command:  CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

[*] REDUNDANT / UNNECESSARY INDEXES (Action: DROP):
  [DUPLICATE] Table 'order_items' -> Index 'idx_order_items_order' (order_id)
    Why:     Exact duplicate of index 'idx_order_items_order_duplicate' on (order_id).
    Impact:  Doubles write amplification on INSERT/UPDATE/DELETE with 0% query benefit.
    Command: DROP INDEX IF EXISTS idx_order_items_order;

  [REDUNDANT_PREFIX] Table 'products' -> Index 'idx_products_category_redundant' (category_id)
    Why:     Redundant leading prefix of composite index 'idx_products_cat_price' on (category_id, price).
    Impact:  Redundant index maintenance during writes.
    Command: DROP INDEX IF EXISTS idx_products_category_redundant;

[OK] SQL Migration Script:  recommendations.sql
[OK] Production Dashboard:  report.html
```

---

## 🧠 Index Evaluation Rules

### Missing Indexes (Where Indexes are Needed)

| Rule | Match Criteria | Architectural Rationale | Estimated Speedup | Priority |
|---|---|---|---|---|
| **Foreign Key** | Constraint in catalog | PostgreSQL does not auto-index FKs; unindexed FKs trigger full table scans and lock parent rows on delete | **10–100x** | `CRITICAL` |
| **ID Column** | Name is `id` | Direct point lookups and manual joins | **50–100x** | `HIGH` |
| **Email** | Contains `email` | User authentication, account search, profile lookup | **50–100x** | `HIGH` |
| **Phone** | Contains `phone` / `mobile` | Customer lookups, SMS delivery routing | **20–50x** | `HIGH` |
| **Lookup Key** | `username`, `slug`, `sku`, `code`, `uuid` | Exact match searches in API routes and business logic | **20–50x** | `HIGH` |
| **Join Key** | Suffix `_id` | Implicit relational foreign keys | **10–50x** | `HIGH` |
| **Status / State** | `status`, `state`, `type`, `category` | Common filter criteria in `WHERE` clauses | **5–20x** | `MEDIUM` |
| **Date / Time** | `timestamp`, `date`, `datetime` | Range queries (`BETWEEN`), event streams, `ORDER BY` sorting | **5–20x** | `MEDIUM` |

### Redundant Indexes (Where Indexes Should be Dropped)

| Issue Type | Definition | Negative Impact | Recommended Action |
|---|---|---|---|
| **Exact Duplicate** | Two indexes covering the identical columns in identical order | Doubles write amplification and memory consumption with 0% query benefit | Drop redundant index |
| **Redundant Prefix** | Index on `(A)` when composite index exists on `(A, B)` | B-Trees traverse leading columns automatically; single-column index is obsolete | Drop single-column prefix |
| **Redundant PK** | Secondary index created manually on a Primary Key | Database engines already create unique B-Trees for Primary Keys | Drop manual secondary index |

---

## 🧪 Automated Testing

Run the test suite using pytest:
```bash
python -m pytest tests -v
```

Expected output:
```text
tests/test_rules.py::test_recommends_expected_columns PASSED             [ 11%]
tests/test_rules.py::test_skips_already_indexed PASSED                   [ 22%]
tests/test_rules.py::test_sql_is_correct PASSED                          [ 33%]
tests/test_rules.py::test_at_least_five_rule_types PASSED                [ 44%]
tests/test_rules.py::test_detects_duplicate_indexes PASSED               [ 55%]
tests/test_rules.py::test_detects_redundant_prefix_indexes PASSED        [ 66%]
tests/test_rules.py::test_detects_redundant_index_on_primary_key PASSED  [ 77%]
tests/test_rules.py::test_schema_health_score_calculation PASSED         [ 88%]
tests/test_rules.py::test_demo_database_generation_and_sqlite_scan PASSED [100%]

============================== 9 passed in 0.13s ==============================
```

---

## 📁 Project Architecture

```text
dbindex-analyzer/
├── index_analyzer.py          # Unified CLI orchestrator (interactive & flag-driven)
├── analyzer/
│   ├── __init__.py            # Package interface and top-level exports
│   ├── db.py                  # Dual-engine connection manager (PostgreSQL + SQLite)
│   ├── schema.py              # Catalog introspection (tables, columns, PKs, FKs, indexes)
│   ├── rules.py               # Dual recommendation heuristics & Schema Health Score
│   ├── generator.py           # On-demand realistic database schema generator
│   └── report.py              # HTML Executive Dashboard & SQL migration file writer
├── tests/
│   └── test_rules.py          # 9 automated unit tests covering all rules and engines
├── sample/
│   ├── sample_db.sql          # PostgreSQL e-commerce sample database
│   ├── pagila-schema.sql      # Pagila sample database schema
│   └── pagila-data.sql        # Pagila sample database data
├── Dockerfile                 # Isolated container environment
└── requirements.txt           # Python dependencies (psycopg2-binary, pytest)
```
