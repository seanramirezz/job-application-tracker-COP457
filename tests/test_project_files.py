"""Static rubric checks that run even before MySQL is available."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RubricStructureTests(unittest.TestCase):
    def test_required_source_files_exist(self):
        for filename in (
            "app.py", "database.py", "schema.sql", "AI_USAGE.md", "README.md",
            "requirements.txt", "templates/dashboard.html", "templates/companies.html",
            "templates/jobs.html", "templates/applications.html", "templates/contacts.html",
            "templates/job_match.html", "static/style.css",
        ):
            with self.subTest(filename=filename):
                self.assertTrue((ROOT / filename).is_file())

    def test_schema_four_tables_and_json_columns(self):
        sql = (ROOT / "schema.sql").read_text(encoding="utf-8").lower()
        for table in ("companies", "jobs", "applications", "contacts"):
            self.assertIn("create table if not exists " + table, sql)
        self.assertRegex(sql, r"requirements\s+json")
        self.assertRegex(sql, r"interview_data\s+json")
        self.assertIn("references companies(company_id)", sql)
        self.assertIn("references jobs(job_id)", sql)

    def test_parameterized_sql_and_csrf_present(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        db = (ROOT / "database.py").read_text(encoding="utf-8")
        self.assertIn("compare_digest(", app)
        self.assertIn("request.form.get(\"_csrf_token\"", app)
        self.assertIn("cursor.execute(query, tuple(params))", db)
        self.assertIn("ON DELETE RESTRICT", (ROOT / "schema.sql").read_text())

    def test_environment_file_is_gitignored(self):
        self.assertIn(".env\n", (ROOT / ".gitignore").read_text())


if __name__ == "__main__":
    unittest.main()
