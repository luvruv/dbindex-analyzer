"""Database connection helper."""
import psycopg2


def connect(host, port, dbname, user, password):
    """Connect to PostgreSQL. Raises ConnectionError with a clear message on failure."""
    try:
        return psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password, connect_timeout=5,
        )
    except psycopg2.OperationalError as e:
        raise ConnectionError(str(e).strip())