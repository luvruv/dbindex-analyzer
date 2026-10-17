# DbIndex Analyzer

A command line tool that scans a PostgreSQL database and finds columns that are missing indexes.

## Features

- Connects to a PostgreSQL database and shows a clear error if it fails
- Scans all tables, columns and data types
- Skips columns that already have an index
- Recommends indexes using 8 rule types
- Estimates how much faster queries will be
- Saves all `CREATE INDEX` commands to `recommendations.sql`
- Creates an HTML report (`report.html`) with a copy button for the SQL

## Usage

```bash
python index_analyzer.py --host localhost --port 5432 --db sampledb --user postgres
```

If you leave out an option, the tool asks for it. The password is always asked privately.

| Option | Meaning | Default |
|---|---|---|
| `--host` | Database host | localhost |
| `--port` | Database port | 5432 |
| `--db` | Database name | asked |
| `--user` | Database user | asked |
| `--password` | Password | asked |
| `--schema` | Schema to analyze | public |
| `--sql-out` | SQL output file | recommendations.sql |
| `--html-out` | HTML report file | report.html |

## Example Output

```text
PASTE YOUR REAL CONSOLE OUTPUT HERE
```

## HTML Report

![HTML report](docs/report.png)

## Index Rules

| Rule | Matches | Why | Expected speedup |
|---|---|---|---|
| ID column | `id` | Used for lookups and joins | 50-100x |
| Email | name contains `email` | Used in login and search | 50-100x |
| Phone | name contains `phone` or `mobile` | Searched directly | 20-50x |
| Lookup key | `username`, `login`, `slug`, `code`, `sku` | Searched by exact value | 20-50x |
| Join key | name ends with `_id` | Used in JOINs | 10-50x |
| Foreign key | real foreign key constraint | Speeds up JOINs and deletes | 10-100x |
| Status | `status`, `state`, `type`, `category` | Often used in filters | 5-20x |
| Date | timestamp or date columns | Used in range filters and sorting | 5-20x |

The speedup numbers are rough estimates, not measured results.

## Tested On

| Database | Tables | Result |
|---|---|---|
| sampledb | 4 | FILL IN |
| pagila | FILL IN | FILL IN |
| SECOND DATABASE | FILL IN | FILL IN |

## Tests

```bash
python -m pytest tests -v
```

## Demo Video

LINK HERE

## Team

| Name | Role |
|---|---|
| NAME 1 | Database connection and schema scan |
| NAME 2 | Index recommendation rules and SQL |
| NAME 3 | Reports, documentation and demo |

## Project Structure

```text
dbindex-analyzer/
├── index_analyzer.py     # command line entry point
├── analyzer/
│   ├── db.py             # database connection
│   ├── schema.py         # reads tables, columns, keys, indexes
│   ├── rules.py          # index rules and SQL generation
│   └── report.py         # SQL file and HTML report
├── tests/test_rules.py   # unit tests
├── sample/sample_db.sql  # sample database
└── requirements.txt
```