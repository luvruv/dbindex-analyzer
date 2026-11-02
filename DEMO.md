# Teacher & Academic Demo Guide (3-5 Minutes)

Use this guide when presenting the project to your teacher or reviewer. It demonstrates real-world database optimization, multi-database support, dual index recommendations, and production-grade reporting.

---

## 1. Introduction: Explain the Problem (30 sec)
**Say to your teacher:**
> *"Most slow applications suffer from poorly indexed databases. But creating too many indexes is just as bad because every index slows down INSERT, UPDATE, and DELETE operations. Our tool performs a 360-degree audit: it identifies missing indexes that queries need, AND finds redundant, duplicate indexes that are wasting write I/O and storage."*

---

## 2. Live Demo: Instant Audit on Any Machine (60 sec)
Even if PostgreSQL is not installed on the teacher's computer, you can run the built-in demo engine:

```bash
python index_analyzer.py --demo
```

**What to point out in the console:**
1. **Database Health Score**: E.g., `51/100 (Grade D)`.
2. **Schema Knowledge**: Tables, columns, and Primary Key coverage percentage.
3. **Missing Indexes (Action: CREATE)**:
   - High-severity unindexed Foreign Keys (critical for table locks during joins and deletes).
   - High-severity search fields (emails, phones, lookup keys).
   - Expected speedup factors (e.g. `10-100x`).
4. **Redundant Indexes (Action: DROP)**:
   - Duplicate indexes on the same table.
   - Redundant prefixes where a composite index already covers queries.
   - Manual indexes on Primary Keys where the database engine already built one.

---

## 3. Walk Through the Executive Dashboard (`report.html`) (60 sec)
Open `report.html` in your web browser:

1. **Executive KPI Header**:
   - Highlight the Schema Health Score ring and Grade.
   - Highlight the Key Coverage and Foreign Key Indexing percentages.
2. **Architectural Observations Box**:
   - Shows human-readable schema diagnosis (e.g. *"2 Foreign Keys lack an index"*, *"1 table lacks a Primary Key"*).
3. **Interactive Tabs**:
   - **Tab 1: Missing Indexes**: Filter by severity (Critical, High, Medium) or search by table name.
   - **Tab 2: Redundant Indexes**: Explains *why* the index is wasteful and provides safe `DROP INDEX` commands.
   - **Tab 3: Existing Healthy Indexes**: Shows Primary Keys, Unique Constraints, and Composite Indexes already doing their job.
   - **Tab 4: Database Schema Knowledge**: A full catalog of every table in the database with column types and constraint mappings.
   - **Tab 5: SQL Migration Scripts**: Instant copyable scripts to apply the rollout.

---

## 4. Show Multi-Database Flexibility (General Database Support) (30 sec)
**Say to your teacher:**
> *"Our architecture is modular. It connects to live PostgreSQL servers over the network using `information_schema` and `pg_catalog`, and it can also analyze any SQLite `.db` file using `PRAGMA` introspection."*

To audit any SQLite database file:
```bash
python index_analyzer.py --sqlite path/to/any_database.db
```

To audit a live PostgreSQL instance:
```bash
python index_analyzer.py --host localhost --port 5432 --db mydatabase --user postgres
```

---

## 5. Run the Automated Test Suite (30 sec)
Demonstrate reliability and code quality:

```bash
python -m pytest tests -v
```

**Expect**: All 9 unit tests pass in under 0.2 seconds.
