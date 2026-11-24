-- OPTIONAL: Fictional example records for a clean demo / screen recording.
-- Do not run on a real tracker unless you want these fictional records included.
-- Idempotent: re-running should not duplicate the example records.
USE job_tracker;

INSERT INTO companies (company_name, industry, website, city, state, notes)
SELECT 'TechCorp', 'Software', 'https://example.com', 'Miami', 'FL', 'Fictional sample for classroom demo'
WHERE NOT EXISTS (SELECT 1 FROM companies WHERE company_name = 'TechCorp');
INSERT INTO companies (company_name, industry, website, city, state, notes)
SELECT 'DataCo', 'Analytics', 'https://example.com', 'Austin', 'TX', 'Fictional sample for classroom demo'
WHERE NOT EXISTS (SELECT 1 FROM companies WHERE company_name = 'DataCo');
INSERT INTO companies (company_name, industry, website, city, state, notes)
SELECT 'CloudNine Labs', 'Cloud Computing', 'https://example.com', 'Seattle', 'WA', 'Fictional sample for classroom demo'
WHERE NOT EXISTS (SELECT 1 FROM companies WHERE company_name = 'CloudNine Labs');

SET @techcorp = (SELECT company_id FROM companies WHERE company_name = 'TechCorp' LIMIT 1);
SET @dataco = (SELECT company_id FROM companies WHERE company_name = 'DataCo' LIMIT 1);
SET @cloudnine = (SELECT company_id FROM companies WHERE company_name = 'CloudNine Labs' LIMIT 1);

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements)
SELECT @techcorp, 'Software Developer', 'Full-time', 85000, 115000, 'https://example.com', '2026-11-04',
 JSON_OBJECT('required_skills', JSON_ARRAY('Python', 'SQL', 'Flask'), 'preferred_skills', JSON_ARRAY('Docker', 'Git'), 'education', 'Bachelors degree')
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE company_id = @techcorp AND job_title = 'Software Developer');
INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements)
SELECT @dataco, 'Data Analyst', 'Full-time', 65000, 90000, 'https://example.com', '2026-11-05',
 JSON_OBJECT('required_skills', JSON_ARRAY('Python', 'SQL', 'Tableau'), 'preferred_skills', JSON_ARRAY('Power BI'))
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE company_id = @dataco AND job_title = 'Data Analyst');
INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements)
SELECT @cloudnine, 'Cloud Engineer', 'Internship', 50000, 70000, 'https://example.com', '2026-11-06',
 JSON_OBJECT('required_skills', JSON_ARRAY('AWS', 'Linux', 'Python'), 'preferred_skills', JSON_ARRAY('Terraform', 'Docker'))
WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE company_id = @cloudnine AND job_title = 'Cloud Engineer');

SET @dev_job = (SELECT job_id FROM jobs WHERE company_id=@techcorp AND job_title='Software Developer' LIMIT 1);
SET @analyst_job = (SELECT job_id FROM jobs WHERE company_id=@dataco AND job_title='Data Analyst' LIMIT 1);
SET @cloud_job = (SELECT job_id FROM jobs WHERE company_id=@cloudnine AND job_title='Cloud Engineer' LIMIT 1);

INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data)
SELECT @dev_job, '2026-11-12', 'Interview', 'Software_v2', 1,
 JSON_OBJECT('interview_rounds', 1, 'feedback', 'Scheduled technical interview')
WHERE NOT EXISTS (SELECT 1 FROM applications WHERE job_id=@dev_job AND application_date='2026-11-12');
INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data)
SELECT @analyst_job, '2026-11-14', 'Screening', 'Data_Analyst_v1', 0, JSON_OBJECT('interview_rounds', 0)
WHERE NOT EXISTS (SELECT 1 FROM applications WHERE job_id=@analyst_job AND application_date='2026-11-14');
INSERT INTO applications (job_id, application_date, status, resume_version, cover_letter_sent, interview_data)
SELECT @cloud_job, '2026-11-17', 'Applied', 'Cloud_v1', 1, JSON_OBJECT()
WHERE NOT EXISTS (SELECT 1 FROM applications WHERE job_id=@cloud_job AND application_date='2026-11-17');

INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
SELECT @techcorp, 'Jordan Taylor', 'Recruiting Lead', 'jordan@example.com', '555-010-0100', NULL, 'Fictional sample contact'
WHERE NOT EXISTS (SELECT 1 FROM contacts WHERE company_id=@techcorp AND contact_name='Jordan Taylor');
INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
SELECT @dataco, 'Morgan Lee', 'People Operations', 'morgan@example.com', '555-010-0200', NULL, 'Fictional sample contact'
WHERE NOT EXISTS (SELECT 1 FROM contacts WHERE company_id=@dataco AND contact_name='Morgan Lee');

SELECT 'Sample data added (where missing)' AS result;
