import unittest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


class TemplateTests(unittest.TestCase):
    def test_all_required_templates_parse(self):
        directory = Path(__file__).resolve().parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(str(directory)))
        # These filters are registered by Flask when app.py starts.
        for name in ("initials", "datefmt", "money", "safe_url", "as_json", "required", "preferred"):
            env.filters[name] = lambda value: value
        for name in (
            "base.html", "dashboard.html", "companies.html", "jobs.html",
            "applications.html", "contacts.html", "job_match.html", "records.html",
            "record_form.html", "record_detail.html", "error.html", "partials/icons.html",
        ):
            with self.subTest(template=name):
                self.assertIsNotNone(env.get_template(name))


if __name__ == "__main__":
    unittest.main()
