# Setup Guide

## 1. Install Requirements

- Python 3.9 or newer
- (Optional for PostgreSQL mode): PostgreSQL server with `psql` and `createdb`

## 2. Get the Code

```bash
git clone <your-repo-url>
cd dbindex-analyzer
```

## 3. Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows (CMD)
venv\Scripts\activate

# Windows (Git Bash)
source venv/Scripts/activate

# Mac / Linux
source venv/bin/activate
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Run the Tool

### Option A: Instant Demo Mode (Zero Setup Required)
Instantly creates a realistic e-commerce database with deliberate missing and redundant index flaws and performs a full audit:
```bash
python index_analyzer.py --demo
```

### Option B: Audit Any SQLite Database File
```bash
python index_analyzer.py --sqlite path/to/database.db
```

### Option C: Audit a Live PostgreSQL Database
```bash
python index_analyzer.py --host localhost --port 5432 --db sampledb --user postgres
```
*(You will be securely prompted for your password).*

## 6. Inspect Results

1. **Terminal Console**: Displays the overall **Schema Health Score**, Grade (A-F), key coverage percentages, list of missing indexes with query speedup estimates, and list of redundant indexes with write-overhead warnings.
2. **Interactive HTML Dashboard**: Open `report.html` in your web browser for an executive dashboard with tabs, filters, and copyable SQL migration scripts.
3. **Executable SQL Migration Script**: Open `recommendations.sql` to review ready-to-run `CREATE INDEX` and `DROP INDEX` commands.

To execute the recommendations against your database:
```bash
# For PostgreSQL:
psql -d sampledb -f recommendations.sql

# For SQLite:
sqlite3 path/to/database.db < recommendations.sql
```

## 7. Run Automated Tests

```bash
python -m pytest tests -v
```

## 8. Run with Docker (Optional)

```bash
docker build -t dbindex-analyzer .
docker run --rm dbindex-analyzer --demo
```
*(To connect to a PostgreSQL database on the host machine from Docker, use `--host host.docker.internal`).*


terminal execution
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python index_analyzer.py --demo
python index_analyzer.py --sqlite sampledb.db
net start postgresql-x64-18
python index_analyzer.py --host localhost --port 5432 --db postgres --user postgres
python -m pytest tests -v


web execution
python index_analyzer.py --host localhost --port 5432 --db postgres --user postgres --open

python index_analyzer.py --demo --open
Start-Process report.html
psql -U postgres -d postgres -f sample/phase1_unindexed_ecommerce.sql
psql -U postgres -d postgres -f sample/phase2_benchmark_queries.sql
psql -U postgres -d postgres -f recommendations.sql

###############################################################################


# 1. Start the PostgreSQL 18 service:
net start postgresql-x64-18

# 2. Go to your project folder:
cd C:\Users\jaind\Projects\dbindex-analyzer

# 3. Activate your virtual environment:
.\venv\Scripts\Activate.ps1
# A. Audit PostgreSQL 18 (Notice port 5433 and no space in flags):
python index_analyzer.py --host 127.0.0.1 --port 5433 --db postgres --user postgres

# B. Audit via SQL file (No server needed, works directly on the sample file):
python index_analyzer.py --sql-file sample/phase1_unindexed_ecommerce.sql

# C. Run Instant Demo:
python index_analyzer.py --demo

# D. Run the 9 automated tests:
python -m pytest tests -v
# A. Audit PostgreSQL 18 and automatically launch the HTML Dashboard in your browser:
python index_analyzer.py --host 127.0.0.1 --port 5433 --db postgres --user postgres --open

# B. Instant Demo with Auto-Open Browser:
python index_analyzer.py --demo --open

# C. Open the generated HTML report manually:
Start-Process report.html

# 1. Load the unindexed e-commerce schema into PostgreSQL 18:
psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -f sample/phase1_unindexed_ecommerce.sql

# 2. Run the Benchmark Queries (Shows slow "Seq Scan" before indexing):
psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -f sample/phase2_benchmark_queries.sql

# 3. Apply the generated index recommendations:
psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -f recommendations.sql

# 4. Re-run the Benchmark (Watch queries switch to fast "Index Scan"):
psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -f sample/phase2_benchmark_queries.sql