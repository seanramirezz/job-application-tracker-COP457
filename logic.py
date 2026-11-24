"""Pure logic for JSON data, form validation and job matching (easy to test)."""

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

JOB_TYPES = ("Full-time", "Part-time", "Contract", "Internship")
STATUSES = ("Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn")
ENTITY_NAMES = {
    "companies": ("company", "company_id", "company_name"),
    "jobs": ("job", "job_id", "job_title"),
    "applications": ("application", "application_id", "application_date"),
    "contacts": ("contact", "contact_id", "contact_name"),
}


def json_object(value):
    """MySQL connector may return JSON text/bytes/dicts; reject other shapes."""
    if value is None or value == "":
        return {}
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return {}
    return value if isinstance(value, dict) else {}


def skill_list(value):
    """Split skills on comma/newline, strip extra spaces, dedupe case-insensitively."""
    if isinstance(value, (list, tuple)):
        parts = value
    elif isinstance(value, str):
        parts = re.split(r"[,;\n]", value)
    else:
        parts = []
    result, seen = [], set()
    for part in parts:
        if not isinstance(part, str):
            continue
        skill = " ".join(part.strip().split())
        key = skill.casefold()
        if skill and key not in seen:
            seen.add(key)
            result.append(skill)
    return result


def required_skills(value):
    """Support both Assignment 7 `required_skills` and older `skills` JSON."""
    data = json_object(value)
    primary = data.get("required_skills")
    if primary is None:
        primary = data.get("skills", [])
    return skill_list(primary)


def preferred_skills(value):
    return skill_list(json_object(value).get("preferred_skills", []))


def rank_jobs(jobs, user_skills):
    """Score matched required skills / total required skills; never count preferred."""
    known = {s.casefold() for s in skill_list(user_skills)}
    ranked = []
    for job in jobs:
        needs = required_skills(job.get("requirements"))
        matches = [skill for skill in needs if skill.casefold() in known]
        missing = [skill for skill in needs if skill.casefold() not in known]
        score = round(len(matches) * 100 / len(needs)) if needs else 0
        ranked.append({
            **job,
            "required_skills": needs,
            "preferred_skills": preferred_skills(job.get("requirements")),
            "matched_skills": matches,
            "missing_skills": missing,
            "matched_count": len(matches),
            "required_count": len(needs),
            "match_pct": score,
            "scorable": bool(needs),
        })
    return sorted(ranked, key=lambda j: (-j["match_pct"], -j["matched_count"], j["job_title"].casefold()))


def _valid_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme.lower() in ("http", "https") and bool(parsed.netloc) and not any(c.isspace() for c in value)
    except ValueError:
        return False


def _check_text(form, field, label, errors, required=False, max_length=None, url=False):
    value = (form.get(field) or "").strip()
    if required and not value:
        errors[field] = f"{label} is required."
    elif max_length and len(value) > max_length:
        errors[field] = f"{label} must be {max_length} characters or fewer."
    elif value and url and not _valid_url(value):
        errors[field] = f"Enter a full http:// or https:// URL for {label.lower()}."
    return value or None


def _date(form, field, errors, required=False):
    text = (form.get(field) or "").strip()
    if not text:
        if required:
            errors[field] = "Application date is required."
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        errors[field] = "Enter a valid date (YYYY-MM-DD)."
        return None


def _json_text(form, field, errors):
    text = (form.get(field) or "{}").strip() or "{}"
    try:
        output = json.loads(text)
        if not isinstance(output, dict):
            raise ValueError("Expected object")
        return output
    except (ValueError, TypeError):
        errors[field] = 'Enter a valid JSON object, such as {"notes": "Phone interview"}.'
        return {}


def _id(form, field, errors):
    raw = str(form.get(field) or "").strip()
    try:
        num = int(raw)
        if num > 0:
            return num
    except ValueError:
        pass
    errors[field] = "Select a valid record from the list."
    return None


def _salary_amount(value):
    """Read whole dollars exactly, including MySQL DECIMAL values such as 65000.00."""
    text = str(value).strip()
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", text):
        raise ValueError("Invalid salary")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Invalid salary") from exc
    if (not amount.is_finite() or amount < 0 or amount > 2147483647
            or amount != amount.to_integral_value()):
        raise ValueError("Salary must be non-negative whole dollars within the INT range")
    return int(amount)


def validate_form(entity, form):
    """Return (validated DB payload, errors by field); no database calls here."""
    errors = {}
    payload = {}
    if entity == "companies":
        for name, label, limit, req, is_url in (
            ("company_name", "Company name", 100, True, False),
            ("industry", "Industry", 50, False, False),
            ("website", "Website", 200, False, True),
            ("city", "City", 50, False, False),
            ("state", "State", 50, False, False),
            ("notes", "Notes", None, False, False),
        ):
            payload[name] = _check_text(form, name, label, errors, req, limit, is_url)
    elif entity == "jobs":
        payload["company_id"] = _id(form, "company_id", errors)
        payload["job_title"] = _check_text(form, "job_title", "Job title", errors, True, 100)
        job_type = (form.get("job_type") or "Full-time").strip()
        if job_type not in JOB_TYPES:
            errors["job_type"] = "Choose a valid job type."
        payload["job_type"] = job_type
        for field in ("salary_min", "salary_max"):
            value = form.get(field)
            raw = "" if value is None else str(value).strip()
            if not raw:
                payload[field] = None
            else:
                try:
                    payload[field] = _salary_amount(raw)
                except ValueError:
                    errors[field] = "Enter a non-negative whole dollar amount up to 2,147,483,647."
                    payload[field] = None
        minimum, maximum = payload["salary_min"], payload["salary_max"]
        if minimum is not None and maximum is not None and minimum > maximum:
            errors["salary_max"] = "Maximum salary must be greater than or equal to minimum."
        payload["job_url"] = _check_text(form, "job_url", "Job URL", errors, max_length=300, url=True)
        payload["date_posted"] = _date(form, "date_posted", errors)
        more = _json_text(form, "requirements_extra", errors)
        for key in ("required_skills", "preferred_skills", "skills"):
            if key in more:
                errors["requirements_extra"] = "Put skills in the skills fields, not the additional JSON box."
        more = {k: v for k, v in more.items() if k not in {"required_skills", "preferred_skills", "skills"}}
        more["required_skills"] = skill_list(form.get("required_skills", ""))
        more["preferred_skills"] = skill_list(form.get("preferred_skills", ""))
        payload["requirements"] = json.dumps(more, ensure_ascii=False)
    elif entity == "applications":
        payload["job_id"] = _id(form, "job_id", errors)
        payload["application_date"] = _date(form, "application_date", errors, required=True)
        status = (form.get("status") or "Applied").strip()
        if status not in STATUSES:
            errors["status"] = "Choose a valid application status."
        payload["status"] = status
        payload["resume_version"] = _check_text(form, "resume_version", "Resume version", errors, max_length=50)
        payload["cover_letter_sent"] = 1 if form.get("cover_letter_sent") in ("on", "1", "true", True) else 0
        interview = _json_text(form, "interview_data", errors)
        payload["interview_data"] = json.dumps(interview, ensure_ascii=False)
    elif entity == "contacts":
        payload["company_id"] = _id(form, "company_id", errors)
        for name, label, limit, req, is_url in (
            ("contact_name", "Contact name", 100, True, False),
            ("title", "Job title", 100, False, False),
            ("email", "Email", 100, False, False),
            ("phone", "Phone", 20, False, False),
            ("linkedin_url", "LinkedIn URL", 200, False, True),
            ("notes", "Notes", None, False, False),
        ):
            payload[name] = _check_text(form, name, label, errors, req, limit, is_url)
        email = payload["email"]
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            errors["email"] = "Enter a valid email address."
    else:
        raise ValueError("Unknown entity")
    return payload, errors


def form_from_record(entity, record):
    """Pre-fill edit forms without discarding flexible Assignment 7 JSON metadata."""
    result = {}
    for key, value in record.items():
        if isinstance(value, (date,)):
            result[key] = value.isoformat()
        else:
            result[key] = value if value is not None else ""
    if entity == "jobs":
        for field in ("salary_min", "salary_max"):
            if field in record and record[field] is not None:
                try:
                    # Keep zero visible and normalize equivalent legacy DECIMALs.
                    result[field] = str(_salary_amount(record[field]))
                except ValueError:
                    # Preserve fractional legacy values for explicit correction; never round.
                    result[field] = str(record[field])
        raw = json_object(record.get("requirements"))
        result["required_skills"] = ", ".join(required_skills(raw))
        result["preferred_skills"] = ", ".join(preferred_skills(raw))
        other = {key: val for key, val in raw.items() if key not in ("required_skills", "skills", "preferred_skills")}
        result["requirements_extra"] = json.dumps(other, indent=2, ensure_ascii=False)
    if entity == "applications":
        result["interview_data"] = json.dumps(json_object(record.get("interview_data")), indent=2, ensure_ascii=False)
        result["cover_letter_sent"] = "on" if record.get("cover_letter_sent") else ""
    return result
