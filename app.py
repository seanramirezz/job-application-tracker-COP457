"""COP4751 full-stack Job Application Tracker (MySQL + Flask + HTML/CSS)."""

import os
import secrets
from urllib.parse import urlsplit
from datetime import date
from hmac import compare_digest

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

from database import execute, fetch_all, fetch_one
from logic import (
    JOB_TYPES, STATUSES, form_from_record, json_object,
    rank_jobs, required_skills, preferred_skills, skill_list, validate_form,
)

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024

# Identifiers used in SQL are chosen only from this constant, trusted whitelist.
ENTITIES = {
    "companies": {
        "label": "Companies", "singular": "Company", "key": "company_id", "display": "company_name",
        "subtitle": "Keep the organizations you're interested in organized.",
    },
    "jobs": {
        "label": "Jobs", "singular": "Job", "key": "job_id", "display": "job_title",
        "subtitle": "All your job opportunities in one place.",
    },
    "applications": {
        "label": "Applications", "singular": "Application", "key": "application_id", "display": "application_date",
        "subtitle": "Track every stage of the hiring process.",
    },
    "contacts": {
        "label": "Contacts", "singular": "Contact", "key": "contact_id", "display": "contact_name",
        "subtitle": "The people behind every opportunity.",
    },
}

FIELDS = {
    "companies": [
        {"name": "company_name", "label": "Company name", "type": "text", "required": True, "maxlength": 100, "placeholder": "e.g. TechCorp"},
        {"name": "industry", "label": "Industry", "type": "text", "maxlength": 50, "placeholder": "e.g. Technology"},
        {"name": "website", "label": "Website", "type": "url", "maxlength": 200, "placeholder": "https://example.com", "wide": True},
        {"name": "city", "label": "City", "type": "text", "maxlength": 50, "placeholder": "e.g. Miami"},
        {"name": "state", "label": "State", "type": "text", "maxlength": 50, "placeholder": "e.g. FL"},
        {"name": "notes", "label": "Notes", "type": "textarea", "rows": 4, "placeholder": "Anything important about this company...", "wide": True},
    ],
    "jobs": [
        {"name": "company_id", "label": "Company", "type": "select", "required": True, "relation": "companies"},
        {"name": "job_title", "label": "Job title", "type": "text", "required": True, "maxlength": 100, "placeholder": "e.g. Software Developer"},
        {"name": "job_type", "label": "Employment type", "type": "select", "options": JOB_TYPES},
        {"name": "date_posted", "label": "Date posted", "type": "date"},
        {"name": "salary_min", "label": "Min. annual salary ($)", "type": "number", "min": 0, "step": 1, "placeholder": "65000"},
        {"name": "salary_max", "label": "Max. annual salary ($)", "type": "number", "min": 0, "step": 1, "placeholder": "95000"},
        {"name": "job_url", "label": "Job posting URL", "type": "url", "maxlength": 300, "wide": True, "placeholder": "https://example.com/careers/..."},
        {"name": "required_skills", "label": "Required skills", "type": "textarea", "wide": True, "rows": 2, "placeholder": "Python, SQL, Flask", "hint": "Separate skills with commas. The Job Match score uses these skills."},
        {"name": "preferred_skills", "label": "Preferred skills", "type": "textarea", "wide": True, "rows": 2, "placeholder": "Docker, AWS", "hint": "Stored in the JSON column, but not counted against the match score."},
        {"name": "requirements_extra", "label": "Other requirements (JSON)", "type": "textarea", "wide": True, "rows": 4, "placeholder": '{"education": "Bachelor\'s degree", "experience_years": 2}', "hint": "Optional. Enter a JSON object, such as {\"education\":\"Bachelor\"}, or leave {}. Skills belong above."},
    ],
    "applications": [
        {"name": "job_id", "label": "Job", "type": "select", "required": True, "relation": "jobs", "wide": True},
        {"name": "application_date", "label": "Application date", "type": "date", "required": True},
        {"name": "status", "label": "Current status", "type": "select", "options": STATUSES},
        {"name": "resume_version", "label": "Resume version", "type": "text", "maxlength": 50, "placeholder": "e.g. Software_Resume_v2"},
        {"name": "cover_letter_sent", "label": "I sent a cover letter", "type": "checkbox", "wide": True},
        {"name": "interview_data", "label": "Interview details (JSON)", "type": "textarea", "wide": True, "rows": 7, "placeholder": '{"interview_rounds": 1, "feedback": "Great conversation"}', "hint": "Flexible MySQL JSON object. You can keep interview rounds, interviewers, feedback, questions, and next steps here."},
    ],
    "contacts": [
        {"name": "company_id", "label": "Company", "type": "select", "required": True, "relation": "companies"},
        {"name": "contact_name", "label": "Contact name", "type": "text", "required": True, "maxlength": 100, "placeholder": "e.g. Alex Morgan"},
        {"name": "title", "label": "Role / Title", "type": "text", "maxlength": 100, "placeholder": "e.g. Talent Acquisition"},
        {"name": "email", "label": "Email", "type": "email", "maxlength": 100, "placeholder": "alex@example.com"},
        {"name": "phone", "label": "Phone", "type": "tel", "maxlength": 20, "placeholder": "+1 (555) 010-0100"},
        {"name": "linkedin_url", "label": "LinkedIn profile URL", "type": "url", "maxlength": 200, "placeholder": "https://linkedin.com/in/...", "wide": True},
        {"name": "notes", "label": "Notes", "type": "textarea", "rows": 4, "wide": True, "placeholder": "How you connected, next follow-up, etc."},
    ],
}


@app.context_processor
def inject_template_helpers():
    def csrf_token():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)
        return session["_csrf_token"]
    return {"csrf_token": csrf_token, "nav_entities": ENTITIES, "today": date.today()}


@app.before_request
def verify_csrf():
    if request.method == "POST":
        submitted = request.form.get("_csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not submitted or not expected or not compare_digest(submitted, expected):
            abort(400, description="Your form session expired. Refresh the page and try again.")


@app.template_filter("datefmt")
def datefmt(value):
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value[:10])
        except ValueError:
            return value
    return value.strftime("%b %d, %Y")


@app.template_filter("money")
def money(value):
    return f"${float(value):,.0f}" if value is not None and value != "" else "—"


@app.template_filter("initials")
def initials(value):
    return "".join(word[:1].upper() for word in str(value or "?").split()[:2]) or "?"


@app.template_filter("as_json")
def as_json(value):
    return json_object(value)


@app.template_filter("safe_url")
def safe_url(value):
    """Reject unsafe schemes from historic/externally created DB records."""
    if not value or not isinstance(value, str):
        return "#"
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() in ("http", "https") and parts.netloc:
            return value
    except ValueError:
        pass
    return "#"


@app.template_filter("required")
def required_filter(value):
    return required_skills(value)


@app.template_filter("preferred")
def preferred_filter(value):
    return preferred_skills(value)


def config_for(entity):
    if entity not in ENTITIES:
        abort(404)
    return ENTITIES[entity]


def record_or_404(entity, record_id):
    config = config_for(entity)
    record = fetch_one(
        f"SELECT * FROM {entity} WHERE {config['key']} = %s", (record_id,)
    )
    if not record:
        abort(404, description=f"This {config['singular'].lower()} could not be found.")
    return record


def relation_options(entity):
    if entity == "jobs" or entity == "contacts":
        return {"companies": fetch_all(
            "SELECT company_id AS value, company_name AS label FROM companies ORDER BY company_name"
        )}
    if entity == "applications":
        return {"jobs": fetch_all(
            """SELECT j.job_id AS value, CONCAT(j.job_title, ' — ', c.company_name) AS label
               FROM jobs j JOIN companies c ON c.company_id = j.company_id
               ORDER BY c.company_name, j.job_title"""
        )}
    return {}


def find_records(entity, search, status_filter):
    pattern = f"%{search}%"
    params = []
    where = []
    if entity == "companies":
        sql = """SELECT c.*, (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id) AS job_count,
                 (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.company_id) AS contact_count
                 FROM companies c"""
        if search:
            where.append("(c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s)")
            params.extend([pattern] * 3)
        order = " ORDER BY c.company_name"
    elif entity == "jobs":
        sql = """SELECT j.*, c.company_name FROM jobs j
                 JOIN companies c ON c.company_id = j.company_id"""
        if search:
            where.append("(j.job_title LIKE %s OR c.company_name LIKE %s OR j.job_type LIKE %s)")
            params.extend([pattern] * 3)
        order = " ORDER BY j.job_id DESC"
    elif entity == "applications":
        sql = """SELECT a.*, j.job_title, c.company_name FROM applications a
                 JOIN jobs j ON j.job_id = a.job_id
                 JOIN companies c ON c.company_id = j.company_id"""
        if search:
            where.append("(j.job_title LIKE %s OR c.company_name LIKE %s OR a.resume_version LIKE %s)")
            params.extend([pattern] * 3)
        if status_filter in STATUSES:
            where.append("a.status = %s")
            params.append(status_filter)
        order = " ORDER BY a.application_date DESC, a.application_id DESC"
    else:
        sql = """SELECT ct.*, c.company_name FROM contacts ct
                 JOIN companies c ON c.company_id = ct.company_id"""
        if search:
            where.append("(ct.contact_name LIKE %s OR ct.title LIKE %s OR c.company_name LIKE %s)")
            params.extend([pattern] * 3)
        order = " ORDER BY ct.contact_name"
    if where:
        sql += " WHERE " + " AND ".join(where)
    return fetch_all(sql + order, params)


@app.route("/")
def dashboard():
    stats = {
        entity: fetch_one(f"SELECT COUNT(*) AS total FROM {entity}")["total"]
        for entity in ENTITIES
    }
    statuses = {status: 0 for status in STATUSES}
    for item in fetch_all("SELECT status, COUNT(*) AS amount FROM applications GROUP BY status"):
        statuses[item["status"]] = item["amount"]
    recent = fetch_all("""SELECT a.application_id, a.application_date, a.status,
                            j.job_title, c.company_name
                            FROM applications a
                            JOIN jobs j ON j.job_id = a.job_id
                            JOIN companies c ON c.company_id = j.company_id
                            ORDER BY a.application_date DESC, a.application_id DESC LIMIT 6""")
    return render_template("dashboard.html", page="dashboard", page_title="Dashboard",
                           stats=stats, statuses=statuses, recent=recent)


@app.route("/<entity>")
def list_records(entity):
    cfg = config_for(entity)
    q = request.args.get("q", "").strip()[:100]
    filter_status = request.args.get("status", "") if entity == "applications" else ""
    rows = find_records(entity, q, filter_status)
    # Per-entity templates required by the specification (all inherit records.html).
    return render_template(f"{entity}.html", page=entity, page_title=cfg["label"],
                           cfg=cfg, entity=entity, rows=rows, q=q,
                           filter_status=filter_status, statuses=STATUSES)


def validate_related_id(entity, payload, errors):
    if entity in ("jobs", "contacts"):
        key, table, pk = "company_id", "companies", "company_id"
    elif entity == "applications":
        key, table, pk = "job_id", "jobs", "job_id"
    else:
        return
    if payload.get(key) and not fetch_one(f"SELECT {pk} FROM {table} WHERE {pk}=%s", (payload[key],)):
        errors[key] = "That linked record no longer exists. Choose another."


def render_record_form(entity, *, record=None, user_form=None, errors=None):
    cfg = config_for(entity)
    editing = record is not None
    values = user_form if user_form is not None else (
        form_from_record(entity, record) if editing else {
            "job_type": "Full-time", "status": "Applied",
            "application_date": date.today().isoformat(),
            "requirements_extra": "{}", "interview_data": "{}",
        }
    )
    options = relation_options(entity)
    return render_template("record_form.html", page=entity,
        page_title=("Edit " if editing else "Add ") + cfg["singular"],
        cfg=cfg, entity=entity, editing=editing, record=record, values=values,
        errors=errors or {}, fields=FIELDS[entity], relations=options)


@app.route("/<entity>/new", methods=["GET", "POST"])
def new_record(entity):
    cfg = config_for(entity)
    if request.method == "GET":
        return render_record_form(entity)
    payload, errors = validate_form(entity, request.form)
    validate_related_id(entity, payload, errors)
    if errors:
        return render_record_form(entity, user_form=request.form, errors=errors), 422
    columns = tuple(payload.keys())  # Comes exclusively from a fixed trusted validator.
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {entity} ({', '.join(columns)}) VALUES ({placeholders})"
    new_id, _ = execute(sql, tuple(payload.values()))
    flash(f"{cfg['singular']} created successfully.", "success")
    return redirect(url_for("detail_record", entity=entity, record_id=new_id))


@app.route("/<entity>/<int:record_id>")
def detail_record(entity, record_id):
    cfg = config_for(entity)
    record = record_or_404(entity, record_id)
    details = {}
    if entity == "companies":
        details["jobs"] = fetch_all("SELECT job_id, job_title, job_type FROM jobs WHERE company_id=%s ORDER BY job_id DESC", (record_id,))
        details["contacts"] = fetch_all("SELECT contact_id, contact_name, title FROM contacts WHERE company_id=%s ORDER BY contact_name", (record_id,))
    elif entity == "jobs":
        details["company"] = fetch_one("SELECT company_name FROM companies WHERE company_id=%s", (record["company_id"],))
        details["applications"] = fetch_all("SELECT application_id, application_date, status FROM applications WHERE job_id=%s ORDER BY application_date DESC", (record_id,))
    elif entity == "applications":
        details["job"] = fetch_one("""SELECT j.job_title, j.company_id, c.company_name FROM jobs j
                                     JOIN companies c ON c.company_id=j.company_id WHERE j.job_id=%s""", (record["job_id"],))
    else:
        details["company"] = fetch_one("SELECT company_name FROM companies WHERE company_id=%s", (record["company_id"],))
    return render_template("record_detail.html", page=entity, page_title=cfg["singular"],
                           cfg=cfg, entity=entity, record=record, details=details)


@app.route("/<entity>/<int:record_id>/edit", methods=["GET", "POST"])
def edit_record(entity, record_id):
    cfg = config_for(entity)
    record = record_or_404(entity, record_id)
    if request.method == "GET":
        return render_record_form(entity, record=record)
    payload, errors = validate_form(entity, request.form)
    validate_related_id(entity, payload, errors)
    if errors:
        return render_record_form(entity, record=record, user_form=request.form, errors=errors), 422
    columns = tuple(payload.keys())
    assignments = ", ".join(f"{key}=%s" for key in columns)
    execute(f"UPDATE {entity} SET {assignments} WHERE {cfg['key']}=%s",
            (*payload.values(), record_id))
    flash(f"{cfg['singular']} updated successfully.", "success")
    return redirect(url_for("detail_record", entity=entity, record_id=record_id))


@app.route("/<entity>/<int:record_id>/delete", methods=["POST"])
def delete_record(entity, record_id):
    cfg = config_for(entity)
    record_or_404(entity, record_id)
    try:
        execute(f"DELETE FROM {entity} WHERE {cfg['key']}=%s", (record_id,))
    except mysql.connector.IntegrityError:
        flash("This record has linked jobs, applications, or contacts. Remove those dependent records first; no data was deleted.", "error")
        return redirect(url_for("detail_record", entity=entity, record_id=record_id))
    flash(f"{cfg['singular']} deleted.", "success")
    return redirect(url_for("list_records", entity=entity))


@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    raw_skills = (request.form.get("skills", "") if request.method == "POST" else request.args.get("skills", ""))[:2000]
    skills = skill_list(raw_skills)
    results = []
    if skills:
        jobs = fetch_all("""SELECT j.job_id, j.job_title, j.job_type, j.requirements,
                           j.salary_min, j.salary_max, c.company_name FROM jobs j
                           JOIN companies c ON c.company_id=j.company_id""")
        results = rank_jobs(jobs, skills)
    return render_template("job_match.html", page="job-match", page_title="Job Match",
                           skills=skills, raw_skills=raw_skills, results=results)


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(413)
def handle_http_error(error):
    return render_template("error.html", page="", page_title="Something went wrong",
                           message=getattr(error, "description", "Please try again."),
                           code=getattr(error, "code", 400)), getattr(error, "code", 400)


@app.errorhandler(mysql.connector.Error)
def handle_database_error(error):
    app.logger.exception("MySQL operation failed")
    msg = ("MySQL could not complete the request. Check that MySQL is running, your .env "
           "credentials are correct, and the database has been initialized. If you used "
           "the earlier COP4751 assignments, run migrate_existing.sql in Workbench.")
    return render_template("error.html", page="", page_title="Database unavailable",
                           message=msg, code=503), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.getenv("FLASK_DEBUG") == "1")
