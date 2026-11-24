"""Regression checks for legacy-schema false positives, using MySQL metadata fixtures."""

import unittest

from check_database import check_schema


def column(table, name, column_type, *, nullable=True, primary=False, extra="", default=None):
    data_type = column_type.split("(", 1)[0].split(" ", 1)[0]
    length = int(column_type[8:-1]) if data_type == "varchar" else None
    return {
        "TABLE_NAME": table, "COLUMN_NAME": name, "DATA_TYPE": data_type,
        "COLUMN_TYPE": column_type, "CHARACTER_MAXIMUM_LENGTH": length,
        "IS_NULLABLE": "YES" if nullable else "NO", "COLUMN_DEFAULT": default,
        "COLUMN_KEY": "PRI" if primary else "", "EXTRA": extra,
    }


def ready_metadata():
    """Representative information_schema output from the final schema, independently specified."""
    declarations = {
        "companies": [
            ("company_id", "int", False), ("company_name", "varchar(100)", False),
            ("industry", "varchar(50)", True), ("website", "varchar(200)", True),
            ("city", "varchar(50)", True), ("state", "varchar(50)", True), ("notes", "text", True),
        ],
        "jobs": [
            ("job_id", "int", False), ("company_id", "int", False), ("job_title", "varchar(100)", False),
            ("job_type", "enum('Full-time','Part-time','Contract','Internship')", True),
            ("salary_min", "int", True), ("salary_max", "int", True), ("job_url", "varchar(300)", True),
            ("date_posted", "date", True), ("requirements", "json", True),
        ],
        "applications": [
            ("application_id", "int", False), ("job_id", "int", False), ("application_date", "date", False),
            ("status", "enum('Applied','Screening','Interview','Offer','Rejected','Withdrawn')", False),
            ("resume_version", "varchar(50)", True), ("cover_letter_sent", "tinyint(1)", False),
            ("interview_data", "json", True),
        ],
        "contacts": [
            ("contact_id", "int", False), ("company_id", "int", False), ("contact_name", "varchar(100)", False),
            ("title", "varchar(100)", True), ("email", "varchar(100)", True), ("phone", "varchar(20)", True),
            ("linkedin_url", "varchar(200)", True), ("notes", "text", True),
        ],
    }
    columns = []
    for table, fields in declarations.items():
        for index, (name, sql_type, nullable) in enumerate(fields):
            columns.append(column(table, name, sql_type, nullable=nullable,
                                  primary=index == 0, extra="auto_increment" if index == 0 else ""))
    foreign_keys = [
        {"TABLE_NAME": table, "COLUMN_NAME": name, "REFERENCED_TABLE_SCHEMA": "job_tracker",
         "REFERENCED_TABLE_NAME": parent, "REFERENCED_COLUMN_NAME": parent_key}
        for table, name, parent, parent_key in (
            ("jobs", "company_id", "companies", "company_id"),
            ("applications", "job_id", "jobs", "job_id"),
            ("contacts", "company_id", "companies", "company_id"),
        )
    ]
    return columns, foreign_keys


class DatabaseCheckTests(unittest.TestCase):
    def assert_ready(self, columns, keys):
        checks = check_schema(columns, keys, database_name="job_tracker")
        self.assertTrue(all(passed for passed, _ in checks), checks)

    def assert_failure_mentions(self, columns, keys, phrase):
        failures = [message for passed, message in check_schema(columns, keys, database_name="job_tracker") if not passed]
        self.assertTrue(any(phrase in message for message in failures), failures)

    def test_corrected_schema_with_safe_preserved_legacy_fields_passes(self):
        columns, keys = ready_metadata()
        columns.extend([
            column("contacts", "first_name", "varchar(50)"),
            column("contacts", "last_name", "varchar(50)"),
            column("contacts", "job_title", "varchar(100)"),
            column("contacts", "created_at", "timestamp", nullable=False,
                   default="CURRENT_TIMESTAMP", extra="DEFAULT_GENERATED"),
        ])
        self.assert_ready(columns, keys)

    def test_old_salary_and_enum_types_do_not_falsely_pass(self):
        for table, name, old_type in (
            ("jobs", "salary_min", "decimal(10,2)"), ("jobs", "salary_max", "decimal(10,2)"),
            ("jobs", "job_type", "varchar(20)"), ("applications", "status", "varchar(30)"),
        ):
            with self.subTest(field=f"{table}.{name}"):
                columns, keys = ready_metadata()
                existing = next(row for row in columns if row["TABLE_NAME"] == table and row["COLUMN_NAME"] == name)
                existing.update(column(table, name, old_type, nullable=existing["IS_NULLABLE"] == "YES"))
                self.assert_failure_mentions(columns, keys, f"{name} must be")

    def test_required_legacy_contact_names_block_inserts_until_relaxed(self):
        columns, keys = ready_metadata()
        legacy_names = [column("contacts", name, "varchar(50)", nullable=False)
                        for name in ("first_name", "last_name")]
        columns.extend(legacy_names)
        self.assert_failure_mentions(columns, keys, "first_name, last_name")
        for row in legacy_names:
            row["IS_NULLABLE"] = "YES"
        self.assert_ready(columns, keys)

    def test_primary_key_auto_increment_and_not_null_are_checked(self):
        for table, name, field, value, expected_message in (
            ("jobs", "job_id", "COLUMN_KEY", "", "PRIMARY KEY"),
            ("contacts", "contact_id", "EXTRA", "", "AUTO_INCREMENT"),
            ("companies", "company_name", "IS_NULLABLE", "YES", "company_name must be NOT NULL"),
            ("applications", "job_id", "IS_NULLABLE", "YES", "job_id must be NOT NULL"),
            ("applications", "application_date", "IS_NULLABLE", "YES", "application_date must be NOT NULL"),
            ("contacts", "contact_name", "IS_NULLABLE", "YES", "contact_name must be NOT NULL"),
        ):
            with self.subTest(field=f"{table}.{name}.{field}"):
                columns, keys = ready_metadata()
                row = next(row for row in columns if row["TABLE_NAME"] == table and row["COLUMN_NAME"] == name)
                row[field] = value
                self.assert_failure_mentions(columns, keys, expected_message)

    def test_wrong_lengths_and_enum_labels_are_rejected(self):
        columns, keys = ready_metadata()
        url = next(row for row in columns if row["COLUMN_NAME"] == "job_url")
        url.update(column("jobs", "job_url", "varchar(500)"))
        status = next(row for row in columns if row["COLUMN_NAME"] == "status")
        status["COLUMN_TYPE"] = "enum('Applied','Interview','Offer','Rejected')"
        self.assert_failure_mentions(columns, keys, "job_url must be varchar(300)")
        self.assert_failure_mentions(columns, keys, "status must be enum(")

    def test_fk_must_point_to_exact_column_in_the_same_database(self):
        for field, value in (("REFERENCED_COLUMN_NAME", "industry"),
                             ("REFERENCED_TABLE_SCHEMA", "another_database")):
            with self.subTest(metadata=field):
                columns, keys = ready_metadata()
                keys[0][field] = value
                self.assert_failure_mentions(columns, keys, "FK: jobs.company_id -> companies.company_id")

    def test_old_int_display_width_is_compatible(self):
        columns, keys = ready_metadata()
        for row in columns:
            if row["DATA_TYPE"] == "int":
                row["COLUMN_TYPE"] = "int(11)"
        self.assert_ready(columns, keys)


if __name__ == "__main__":
    unittest.main()
