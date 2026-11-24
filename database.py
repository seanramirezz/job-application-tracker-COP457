"""Simple, parameterized MySQL access layer; no credentials are hard-coded."""

import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Return a new connection to the configured job_tracker database."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "job_tracker"),
        connection_timeout=6,
        charset="utf8mb4",
    )


@contextmanager
def cursor_for(write=False):
    """Close cursor/connection reliably; commit writes or roll them back."""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
        if write:
            connection.commit()
    except Exception:
        if write:
            connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def fetch_all(query, params=()):
    with cursor_for() as cursor:
        cursor.execute(query, tuple(params))
        return cursor.fetchall()


def fetch_one(query, params=()):
    with cursor_for() as cursor:
        cursor.execute(query, tuple(params))
        return cursor.fetchone()


def execute(query, params=()):
    with cursor_for(write=True) as cursor:
        cursor.execute(query, tuple(params))
        return cursor.lastrowid, cursor.rowcount
