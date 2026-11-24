"""Read-only verification that the local MySQL schema is ready for the final app."""

import os
import re
import sys


# These declarations follow schema.sql. MySQL reports BOOLEAN as tinyint(1).
EXPECTED = {
    "companies": {
        "company_id": "int", "company_name": "varchar(100)", "industry": "varchar(50)",
        "website": "varchar(200)", "city": "varchar(50)", "state": "varchar(50)", "notes": "text",
    },
    "jobs": {
        "job_id": "int", "company_id": "int", "job_title": "varchar(100)",
        "job_type": "enum('Full-time','Part-time','Contract','Internship')",
        "salary_min": "int", "salary_max": "int", "job_url": "varchar(300)",
        "date_posted": "date", "requirements": "json",
    },
    "applications": {
        "application_id": "int", "job_id": "int", "application_date": "date",
        "status": "enum('Applied','Screening','Interview','Offer','Rejected','Withdrawn')",
        "resume_version": "varchar(50)", "cover_letter_sent": "tinyint(1)", "interview_data": "json",
    },
    "contacts": {
        "contact_id": "int", "company_id": "int", "contact_name": "varchar(100)",
        "title": "varchar(100)", "email": "varchar(100)", "phone": "varchar(20)",
        "linkedin_url": "varchar(200)", "notes": "text",
    },
}
PRIMARY_KEYS = {
    "companies": "company_id", "jobs": "job_id",
    "applications": "application_id", "contacts": "contact_id",
}
NOT_NULL = {
    "companies": {"company_id", "company_name"},
    "jobs": {"job_id", "company_id", "job_title"},
    "applications": {"application_id", "job_id", "application_date", "status", "cover_letter_sent"},
    "contacts": {"contact_id", "company_id", "contact_name"},
}
FOREIGN_KEYS = {
    ("jobs", "company_id", "companies", "company_id"),
    ("applications", "job_id", "jobs", "job_id"),
    ("contacts", "company_id", "companies", "company_id"),
}


def _matches_type(column, expected):
    """Compare SQL types without treating an old INT display width as a mismatch."""
    data_type = str(column.get("DATA_TYPE", "")).lower()
    column_type = str(column.get("COLUMN_TYPE", ""))
    if expected == "int":
        # Reject unsigned/DECIMAL/BIGINT; int(11) is the same signed INT storage type.
        return data_type == "int" and re.fullmatch(r"int(?:\([0-9]+\))?", column_type.lower()) is not None
    if expected.startswith("varchar("):
        length = int(expected[8:-1])
        return data_type == "varchar" and column.get("CHARACTER_MAXIMUM_LENGTH") == length
    if expected.startswith("enum("):
        # Enum label spelling, case and order must match the final schema.
        return data_type == "enum" and column_type == expected
    if expected == "tinyint(1)":
        return data_type == "tinyint" and column_type.lower() == expected
    return data_type == expected


def check_schema(column_rows, foreign_key_rows, database_name=None):
    """Return (passed, message) checks from MySQL metadata, without DB access or writes.

    Extra assignment columns may remain when inserts can omit them. Required
    extra columns without a default would break the final app's INSERTs.
    """
    columns = {}
    for column in column_rows:
        columns.setdefault(column["TABLE_NAME"], {})[column["COLUMN_NAME"]] = column

    checks = []
    for table, expected_columns in EXPECTED.items():
        actual_columns = columns.get(table, {})
        problems = []
        missing = sorted(set(expected_columns) - set(actual_columns))
        if missing:
            problems.append("missing " + ", ".join(missing))
        for name, expected_type in expected_columns.items():
            column = actual_columns.get(name)
            if column is None:
                continue
            if not _matches_type(column, expected_type):
                actual_type = column.get("COLUMN_TYPE") or column.get("DATA_TYPE") or "unknown"
                problems.append(f"{name} must be {expected_type}; found {actual_type}")
            if name in NOT_NULL[table] and column.get("IS_NULLABLE") != "NO":
                problems.append(f"{name} must be NOT NULL")

        key = PRIMARY_KEYS[table]
        found_keys = {name for name, column in actual_columns.items() if column.get("COLUMN_KEY") == "PRI"}
        if found_keys != {key}:
            problems.append(f"PRIMARY KEY must contain only {key}")
        if key in actual_columns and "auto_increment" not in str(actual_columns[key].get("EXTRA", "")).lower():
            problems.append(f"{key} must AUTO_INCREMENT")

        blocking = []
        for name, column in actual_columns.items():
            if name in expected_columns:
                continue
            extra = str(column.get("EXTRA", "")).lower()
            database_supplies_value = any(marker in extra for marker in (
                "auto_increment", "virtual generated", "stored generated"))
            if (column.get("IS_NULLABLE") == "NO" and column.get("COLUMN_DEFAULT") is None
                    and not database_supplies_value):
                blocking.append(name)
        if blocking:
            problems.append("extra required columns without defaults block new records: " + ", ".join(sorted(blocking)))

        summary = "; ".join(problems) if problems else "required fields, types, primary key and insert compatibility verified"
        checks.append((not problems, f"{table}: {summary}"))

    found_foreign_keys = {
        (row.get("TABLE_NAME"), row.get("COLUMN_NAME"), row.get("REFERENCED_TABLE_NAME"), row.get("REFERENCED_COLUMN_NAME"))
        for row in foreign_key_rows
        if database_name is None or row.get("REFERENCED_TABLE_SCHEMA") == database_name
    }
    for table, column, parent, parent_key in sorted(FOREIGN_KEYS):
        relationship = (table, column, parent, parent_key)
        passed = relationship in found_foreign_keys
        label = f"FK: {table}.{column} -> {parent}.{parent_key}"
        checks.append((passed, label if passed else label + " is missing or points elsewhere"))
    return checks


def main():
    # Lazy imports let the metadata checker and its tests run without MySQL packages.
    try:
        import mysql.connector
        from dotenv import load_dotenv
        from database import get_connection
    except ImportError:
        print("[FAIL] Python dependencies are missing. Run: python -m pip install -r requirements.txt")
        return 1

    load_dotenv()
    try:
        connection = get_connection()
    except (mysql.connector.Error, ValueError) as exc:
        print(f"[FAIL] Could not connect to MySQL: {exc}")
        print("Check MySQL service, .env credentials, DB_PORT, and DB_NAME=job_tracker.")
        return 1

    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        db = os.getenv("DB_NAME", "job_tracker")
        cursor.execute("""SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE,
                                  CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT,
                                  COLUMN_KEY, EXTRA
                           FROM information_schema.COLUMNS
                           WHERE TABLE_SCHEMA = %s""", (db,))
        column_rows = cursor.fetchall()
        cursor.execute("""SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_SCHEMA,
                                  REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                           FROM information_schema.KEY_COLUMN_USAGE
                           WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL""", (db,))
        checks = check_schema(column_rows, cursor.fetchall(), database_name=db)
        for passed, message in checks:
            print(f"[{'OK' if passed else 'FAIL'}] {message}")
        if all(passed for passed, _ in checks):
            print("\nPASS: Schema checks passed. Run: python app.py")
            print("Next verify create, view, edit and delete in the browser; this check does not test live app behavior.")
            return 0
        print("\nFAIL: Schema is not ready. Review the failures above.")
        print("Use schema.sql for a fresh database or migrate_existing.sql for the earlier-assignment database.")
        return 1
    except mysql.connector.Error as exc:
        print(f"[FAIL] Schema check failed: {exc}")
        return 1
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
