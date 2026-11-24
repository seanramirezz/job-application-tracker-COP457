import json
import unittest
from decimal import Decimal

from logic import (
    form_from_record, json_object, rank_jobs, required_skills,
    skill_list, validate_form,
)


class SkillTests(unittest.TestCase):
    def test_normalize_and_deduplicate(self):
        self.assertEqual(skill_list(" Python,SQL, python;  Machine   Learning\nFlask "),
                         ["Python", "SQL", "Machine Learning", "Flask"])

    def test_prior_assignment_json_required_skills(self):
        self.assertEqual(required_skills('{"required_skills":["Python","SQL","Git"]}'),
                         ["Python", "SQL", "Git"])

    def test_legacy_skills_fallback(self):
        self.assertEqual(required_skills({"skills": ["Python", "Flask"]}), ["Python", "Flask"])

    def test_json_bytes(self):
        self.assertEqual(json_object(b'{"x":2}'), {"x": 2})

    def test_ranking_spec_example(self):
        jobs = [
            {"job_id": 1, "job_title": "Data Analyst", "requirements": {"required_skills": ["Python", "SQL", "Tableau"]}},
            {"job_id": 2, "job_title": "Software Developer", "requirements": '{"required_skills":["Python","SQL","Flask"]}'},
        ]
        result = rank_jobs(jobs, "python, SQL, Flask")
        self.assertEqual([r["job_title"] for r in result], ["Software Developer", "Data Analyst"])
        self.assertEqual([r["match_pct"] for r in result], [100, 67])
        self.assertEqual(result[1]["missing_skills"], ["Tableau"])
        self.assertEqual(result[1]["matched_count"], 2)
        self.assertEqual(result[1]["required_count"], 3)

    def test_no_required_skills_not_false_perfect_match(self):
        result = rank_jobs([{"job_title": "Unspecified", "requirements": None}], "Python")
        self.assertEqual(result[0]["match_pct"], 0)
        self.assertFalse(result[0]["scorable"])

    def test_preferred_skills_do_not_reduce_score(self):
        result = rank_jobs([{"job_title": "Dev", "requirements": {"required_skills": ["SQL"], "preferred_skills": ["Docker"]}}], "sql")
        self.assertEqual(result[0]["match_pct"], 100)


class FormTests(unittest.TestCase):
    def test_company_required_name(self):
        _, errors = validate_form("companies", {"company_name": " "})
        self.assertIn("company_name", errors)

    def test_company_valid(self):
        payload, errors = validate_form("companies", {"company_name": "Example", "website": "https://example.com"})
        self.assertFalse(errors)
        self.assertEqual(payload["company_name"], "Example")

    def test_url_rejects_script_scheme(self):
        _, errors = validate_form("companies", {"company_name": "Example", "website": "javascript:alert(1)"})
        self.assertIn("website", errors)

    def test_salary_validation(self):
        _, errors = validate_form("jobs", {"company_id": "1", "job_title": "Dev", "salary_min": "90000", "salary_max": "60000", "requirements_extra": "{}"})
        self.assertIn("salary_max", errors)

    def test_legacy_decimal_salaries_roundtrip_through_edit_form(self):
        record = {"company_id": 1, "job_title": "Dev", "salary_min": Decimal("65000.00"),
                  "salary_max": Decimal("95000.00"), "requirements": None}
        form = form_from_record("jobs", record)
        self.assertEqual(form["salary_min"], "65000")
        self.assertEqual(form["salary_max"], "95000")
        submitted = {key: str(value) for key, value in form.items()}
        payload, errors = validate_form("jobs", submitted)
        self.assertFalse(errors)
        self.assertEqual((payload["salary_min"], payload["salary_max"]), (65000, 95000))

    def test_salary_accepts_integral_decimals_zero_and_int_boundary(self):
        for raw, expected in (("65000.00", 65000), ("0.00", 0), (0, 0),
                              (" 65000.000 ", 65000), ("6.5e4", 65000),
                              ("2147483647.00", 2147483647)):
            with self.subTest(salary=raw):
                payload, errors = validate_form("jobs", {
                    "company_id": "1", "job_title": "Dev", "salary_min": raw})
                self.assertFalse(errors)
                self.assertEqual(payload["salary_min"], expected)
                self.assertIsInstance(payload["salary_min"], int)
        self.assertEqual(form_from_record("jobs", {"salary_min": Decimal("0.00")})["salary_min"], "0")

    def test_salary_rejects_fractional_nonfinite_out_of_range_and_malformed_values(self):
        for raw in ("65000.01", "2147483647.0000000000000000001", "-1.00",
                    "2147483648", "NaN", "sNaN", "Infinity", "-Infinity",
                    "1e999999", "65_000", "65,000", "$65000", "1.2.3", "abc"):
            with self.subTest(salary=raw):
                payload, errors = validate_form("jobs", {
                    "company_id": "1", "job_title": "Dev", "salary_max": raw})
                self.assertIn("salary_max", errors)
                self.assertIsNone(payload["salary_max"])

    def test_fractional_legacy_salary_is_preserved_and_not_rounded(self):
        form = form_from_record("jobs", {"company_id": 1, "job_title": "Dev",
                                         "salary_min": Decimal("65000.50")})
        self.assertEqual(form["salary_min"], "65000.50")
        _, errors = validate_form("jobs", form)
        self.assertIn("salary_min", errors)

    def test_optional_salaries_remain_empty(self):
        for raw in (None, "", "   "):
            with self.subTest(salary=raw):
                payload, errors = validate_form("jobs", {
                    "company_id": "1", "job_title": "Dev", "salary_min": raw})
                self.assertFalse(errors)
                self.assertIsNone(payload["salary_min"])
                self.assertIsNone(payload["salary_max"])

    def test_json_validation(self):
        _, errors = validate_form("applications", {"job_id": "2", "application_date": "2026-11-23", "status": "Applied", "interview_data": "not json"})
        self.assertIn("interview_data", errors)

    def test_enum_validation(self):
        _, errors = validate_form("applications", {"job_id": "2", "application_date": "2026-11-23", "status": "Pending", "interview_data": "{}"})
        self.assertIn("status", errors)

    def test_applications_happy_path(self):
        payload, errors = validate_form("applications", {"job_id": "2", "application_date": "2026-11-23", "status": "Interview", "cover_letter_sent": "on", "interview_data": '{"interview_rounds":2}'})
        self.assertFalse(errors)
        self.assertEqual(payload["cover_letter_sent"], 1)
        self.assertEqual(json.loads(payload["interview_data"])["interview_rounds"], 2)

    def test_job_json_preserves_extra_details(self):
        record = {"requirements": '{"required_skills":["Python"], "preferred_skills":["AWS"],"education":"Bachelor", "remote_option":true}'}
        form = form_from_record("jobs", record)
        payload, errors = validate_form("jobs", {"company_id": "1", "job_title": "Dev", "requirements_extra": form["requirements_extra"], "required_skills": form["required_skills"], "preferred_skills": form["preferred_skills"]})
        self.assertFalse(errors)
        restored = json.loads(payload["requirements"])
        self.assertEqual(restored["education"], "Bachelor")
        self.assertTrue(restored["remote_option"])
        self.assertEqual(restored["required_skills"], ["Python"])

    def test_contact_email_validation(self):
        _, errors = validate_form("contacts", {"company_id": "1", "contact_name": "Alex", "email": "not-a-valid-email"})
        self.assertIn("email", errors)

    def test_invalid_date(self):
        _, errors = validate_form("applications", {"job_id": "3", "application_date": "2026-22-88"})
        self.assertIn("application_date", errors)


if __name__ == "__main__":
    unittest.main()
