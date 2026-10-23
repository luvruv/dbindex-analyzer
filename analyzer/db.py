"""Database connection helper module for DbIndex Analyzer.

This module provides a reliable way to establish a connection to a PostgreSQL
database instance using the `psycopg2` driver library.
"""

# ------------------------------------------------------------------------------
# Package / Library Imports:
# ------------------------------------------------------------------------------
# psycopg2:
# The most popular PostgreSQL adapter for the Python programming language.
# It implements the Python DB-API 2.0 specification, allowing Python scripts
# to send SQL commands, fetch query results, manage transactions, and handle
# connection lifecycles with a PostgreSQL database server.
import psycopg2


def connect(host, port, dbname, user, password):
    """Connect to a PostgreSQL database instance.

    Attempts to establish a network connection to PostgreSQL using the provided
    host, port, database name, and user credentials. If the connection fails
    (e.g., server offline, incorrect credentials, database does not exist),
    it catches the database-specific error and raises a user-friendly ConnectionError.

    Parameters:
    -----------
    host : str
        The hostname or IP address of the PostgreSQL server (e.g., "localhost" or "127.0.0.1").
    port : int
        The network port number PostgreSQL is listening on (standard default is 5432).
    dbname : str
        The name of the database to connect to.
    user : str
        The database user account name.
    password : str
        The authentication password for the database user.

    Returns:
    --------
    psycopg2.extensions.connection
        An active database connection object ready for creating cursors and running queries.

    Raises:
    -------
    ConnectionError
        If the connection cannot be established within the timeout period or if
        authentication fails, containing a clean, descriptive error message.
    """
    try:
        # psycopg2.connect() establishes the socket connection and authenticates.
        # - connect_timeout=5: Maximum wait time in seconds for connection establishment.
        #   This prevents the application from freezing indefinitely if the host is down.
        return psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=5,
        )
    except psycopg2.OperationalError as e:
        # OperationalError is raised by psycopg2 for connection issues such as:
        # host unreachable, wrong port, invalid password, or non-existent database.
        # We catch it and raise Python's built-in ConnectionError with the stripped error text
        # so the caller receives a clean, readable message without raw internal tracebacks.
        raise ConnectionError(str(e).strip())