# Demo Guide (3-5 minutes)

## 1. Show the help (20 sec)

```bash
python index_analyzer.py --help
```

Expect: the list of options.

## 2. Run the tool on the sample database (60 sec)

```bash
python index_analyzer.py --host localhost --port 5432 --db sampledb --user postgres
```

Expect: "Connected", the table and column count, then one SUGGESTION line per recommended index, and the saved file names.

## 3. Show the HTML report (60 sec)

Open `report.html` in the browser.

Expect: database name, three summary cards, the recommendations table, and the SQL box with a Copy button.

## 4. Run the generated SQL (45 sec)

```bash
psql -d sampledb -f recommendations.sql
```

Expect: a line saying `CREATE INDEX` for each recommendation.

## 5. Run the tool again (30 sec)

```bash
python index_analyzer.py --host localhost --port 5432 --db sampledb --user postgres
```

Expect: far fewer recommendations, because the new indexes already exist.

## 6. Show an error case (30 sec)

```bash
python index_analyzer.py --host wronghost --db sampledb --user postgres
```

Expect: a clean error message, no crash.

## 7. Run the tests (30 sec)

```bash
python -m pytest tests -v
```

Expect: all tests pass.