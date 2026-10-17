# Setup Guide

## 1. Install requirements

- Python 3.9 or newer
- PostgreSQL (with `psql` and `createdb` available in your terminal)

## 2. Get the code

```bash
git clone <your-repo-url>
cd dbindex-analyzer
```

## 3. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows (Git Bash)
source venv/Scripts/activate

# Windows (CMD)
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

## 4. Install dependencies

```bash
pip install -r requirements.txt
```

## 5. Load the sample database

```bash
createdb sampledb
psql -d sampledb -f sample/sample_db.sql
```

## 6. Run the tool

```bash
python index_analyzer.py --host localhost --port 5432 --db sampledb --user postgres
```

Enter your password when asked.

## 7. Open the report

Open `report.html` in your browser. The SQL commands are also saved in `recommendations.sql`.

To apply the indexes:

```bash
psql -d sampledb -f recommendations.sql
```

## 8. Run the tests

```bash
python -m pytest tests -v
```

## Run with Docker (optional)

```bash
docker build -t dbindex-analyzer .
docker run --rm dbindex-analyzer --help
```

To reach a database running on your own computer, use `--host host.docker.internal`.

## Common problems

| Problem | Fix |
|---|---|
| `No module named psycopg2` | Activate the venv and run `pip install -r requirements.txt` |
| `could not connect` | Check host, port, and that PostgreSQL is running |
| `password authentication failed` | Check the username and password |
| `database does not exist` | Check the database name with `psql -l` |