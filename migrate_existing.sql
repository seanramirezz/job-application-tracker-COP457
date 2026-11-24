-- COP4751 | Upgrade an existing Assignment 2 database to the final schema.
-- Revision 2: supports first_name/last_name/job_title and exact final types.
-- FIRST export job_tracker using Workbench Server > Data Export.
-- Run this ENTIRE file in MySQL Workbench while the Flask app is stopped.
-- Existing IDs, rows, legacy columns and unrelated coursework objects remain.
-- Preflight stops on values needing a decision; nothing is truncated or rounded.
-- MySQL DDL commits independently: this is NOT a rollbackable transaction.
-- Rerunning fills only missing canonical values. Old contact fields are retained
-- as historical fields; the final app edits contact_name and title going forward.

USE job_tracker;

-- A routine captures its SQL mode when created. Use strict conversions here,
-- then restore the caller's mode BEFORE calling the routine.
SET @jt_final_saved_sql_mode = @@SESSION.sql_mode;
SET SESSION sql_mode = CONCAT_WS(',', NULLIF(@jt_final_saved_sql_mode, ''), 'STRICT_ALL_TABLES');

DROP PROCEDURE IF EXISTS jt_upgrade_final_20261123_v2;
DELIMITER $$
CREATE PROCEDURE jt_upgrade_final_20261123_v2()
BEGIN
    DECLARE v_safe_updates INT DEFAULT 1;
    DECLARE v_has_name INT DEFAULT 0;
    DECLARE v_has_title INT DEFAULT 0;
    DECLARE v_has_first INT DEFAULT 0;
    DECLARE v_has_last INT DEFAULT 0;
    DECLARE v_has_legacy_title INT DEFAULT 0;
    DECLARE v_has_url INT DEFAULT 0;
    DECLARE v_has_legacy_url INT DEFAULT 0;
    DECLARE v_companies BIGINT DEFAULT 0;
    DECLARE v_jobs BIGINT DEFAULT 0;
    DECLARE v_applications BIGINT DEFAULT 0;
    DECLARE v_contacts BIGINT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET SESSION sql_safe_updates = v_safe_updates;
        RESIGNAL;
    END;

    SET v_safe_updates = @@SESSION.sql_safe_updates;

    -- PHASE 1: all data checks run before changing any application table.
    IF (SELECT COUNT(*) FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
          AND TABLE_NAME IN ('companies','jobs','applications','contacts')) <> 4 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: four existing project tables are required.';
    END IF;

    SELECT COUNT(*) INTO v_companies FROM companies;
    SELECT COUNT(*) INTO v_jobs FROM jobs;
    SELECT COUNT(*) INTO v_applications FROM applications;
    SELECT COUNT(*) INTO v_contacts FROM contacts;

    SELECT COUNT(*) INTO v_has_name FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='contacts' AND COLUMN_NAME='contact_name';
    SELECT COUNT(*) INTO v_has_title FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='contacts' AND COLUMN_NAME='title';
    SELECT COUNT(*) INTO v_has_first FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='contacts' AND COLUMN_NAME='first_name';
    SELECT COUNT(*) INTO v_has_last FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='contacts' AND COLUMN_NAME='last_name';
    SELECT COUNT(*) INTO v_has_legacy_title FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='contacts' AND COLUMN_NAME='job_title';
    SELECT COUNT(*) INTO v_has_url FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='jobs' AND COLUMN_NAME='job_url';
    SELECT COUNT(*) INTO v_has_legacy_url FROM information_schema.COLUMNS
      WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='jobs' AND COLUMN_NAME='posting_url';

    IF EXISTS (SELECT 1 FROM jobs
        WHERE (salary_min IS NOT NULL AND
              (salary_min < 0 OR salary_min > 2147483647 OR salary_min <> TRUNCATE(salary_min,0)))
           OR (salary_max IS NOT NULL AND
              (salary_max < 0 OR salary_max > 2147483647 OR salary_max <> TRUNCATE(salary_max,0)))
           OR (salary_min IS NOT NULL AND salary_max IS NOT NULL AND salary_min > salary_max)) THEN
        SELECT job_id, salary_min, salary_max FROM jobs
          WHERE (salary_min IS NOT NULL AND
                (salary_min < 0 OR salary_min > 2147483647 OR salary_min <> TRUNCATE(salary_min,0)))
             OR (salary_max IS NOT NULL AND
                (salary_max < 0 OR salary_max > 2147483647 OR salary_max <> TRUNCATE(salary_max,0)))
             OR (salary_min IS NOT NULL AND salary_max IS NOT NULL AND salary_min > salary_max);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: review the listed salary values; no values were rounded.';
    END IF;

    IF EXISTS (SELECT 1 FROM jobs WHERE job_type IS NOT NULL AND
        CAST(job_type AS BINARY) NOT IN ('Full-time','Part-time','Contract','Internship')) THEN
        SELECT job_id, job_type FROM jobs WHERE job_type IS NOT NULL AND
          CAST(job_type AS BINARY) NOT IN ('Full-time','Part-time','Contract','Internship');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: review the listed job types before converting to ENUM.';
    END IF;

    IF EXISTS (SELECT 1 FROM applications WHERE status IS NULL OR
        CAST(status AS BINARY) NOT IN ('Applied','Screening','Interview','Offer','Rejected','Withdrawn')) THEN
        SELECT application_id, status FROM applications WHERE status IS NULL OR
          CAST(status AS BINARY) NOT IN ('Applied','Screening','Interview','Offer','Rejected','Withdrawn');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: review the listed application statuses before converting to ENUM.';
    END IF;

    IF EXISTS (SELECT 1 FROM applications WHERE cover_letter_sent IS NULL OR cover_letter_sent NOT IN (0,1)) THEN
        SELECT application_id, cover_letter_sent FROM applications
          WHERE cover_letter_sent IS NULL OR cover_letter_sent NOT IN (0,1);
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: review the listed cover-letter flags; each must be 0 or 1.';
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND DATA_TYPE <> 'json'
          AND ((TABLE_NAME='jobs' AND COLUMN_NAME='requirements')
            OR (TABLE_NAME='applications' AND COLUMN_NAME='interview_data'))) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: an existing requirements/interview_data column is not JSON.';
    END IF;

    -- Existing canonical names win. Only missing names use the old name fields.
    IF v_has_name = 1 THEN
        IF EXISTS (SELECT 1 FROM contacts WHERE CHAR_LENGTH(contact_name) > 100) THEN
            SELECT contact_id, contact_name FROM contacts WHERE CHAR_LENGTH(contact_name) > 100;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a contact name exceeds the final 100-character limit.';
        END IF;
    END IF;

    IF v_has_first = 1 AND v_has_last = 1 THEN
        IF v_has_name = 0 THEN
            IF EXISTS (SELECT 1 FROM contacts WHERE
                CHAR_LENGTH(CONCAT_WS(' ',NULLIF(TRIM(first_name),''),NULLIF(TRIM(last_name),''))) NOT BETWEEN 1 AND 100) THEN
                SELECT contact_id, first_name, last_name FROM contacts WHERE
                  CHAR_LENGTH(CONCAT_WS(' ',NULLIF(TRIM(first_name),''),NULLIF(TRIM(last_name),''))) NOT BETWEEN 1 AND 100;
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a combined contact name is empty or longer than 100 characters.';
            END IF;
        ELSE
            IF EXISTS (SELECT 1 FROM contacts WHERE (contact_name IS NULL OR TRIM(contact_name)='') AND
                CHAR_LENGTH(CONCAT_WS(' ',NULLIF(TRIM(first_name),''),NULLIF(TRIM(last_name),''))) NOT BETWEEN 1 AND 100) THEN
                SELECT contact_id, first_name, last_name FROM contacts WHERE (contact_name IS NULL OR TRIM(contact_name)='') AND
                  CHAR_LENGTH(CONCAT_WS(' ',NULLIF(TRIM(first_name),''),NULLIF(TRIM(last_name),''))) NOT BETWEEN 1 AND 100;
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a missing contact name cannot be filled from the legacy fields.';
            END IF;
        END IF;
    ELSEIF v_has_name = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: contacts need contact_name or both legacy name columns.';
    ELSE
        IF EXISTS (SELECT 1 FROM contacts WHERE contact_name IS NULL OR TRIM(contact_name)='') THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: fill missing contact_name values before upgrading.';
        END IF;
    END IF;

    -- The supplied legacy columns are VARCHAR(50). Do not shrink unexpected data.
    IF v_has_first = 1 THEN
        IF EXISTS (SELECT 1 FROM contacts WHERE CHAR_LENGTH(first_name)>50) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a legacy first_name exceeds 50 characters; review its definition.';
        END IF;
    END IF;
    IF v_has_last = 1 THEN
        IF EXISTS (SELECT 1 FROM contacts WHERE CHAR_LENGTH(last_name)>50) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a legacy last_name exceeds 50 characters; review its definition.';
        END IF;
    END IF;

    IF v_has_title = 1 THEN
        IF EXISTS (SELECT 1 FROM contacts WHERE CHAR_LENGTH(title)>100) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: an existing contact title exceeds 100 characters.';
        END IF;
    END IF;
    IF v_has_legacy_title = 1 THEN
        IF v_has_title = 0 THEN
            IF EXISTS (SELECT 1 FROM contacts WHERE CHAR_LENGTH(job_title)>100) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a legacy contact job_title exceeds 100 characters.';
            END IF;
        ELSE
            IF EXISTS (SELECT 1 FROM contacts WHERE (title IS NULL OR title='') AND CHAR_LENGTH(job_title)>100) THEN
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a legacy contact job_title is too long to copy.';
            END IF;
        END IF;
    END IF;

    IF v_has_url = 1 THEN
        IF EXISTS (SELECT 1 FROM jobs WHERE CHAR_LENGTH(job_url)>300) THEN
            SELECT job_id, job_url FROM jobs WHERE CHAR_LENGTH(job_url)>300;
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a current job_url exceeds 300 characters; no URL was shortened.';
        END IF;
    END IF;
    IF v_has_legacy_url = 1 THEN
        IF v_has_url = 0 THEN
            IF EXISTS (SELECT 1 FROM jobs WHERE CHAR_LENGTH(posting_url)>300) THEN
                SELECT job_id, posting_url FROM jobs WHERE CHAR_LENGTH(posting_url)>300;
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a posting URL exceeds 300 characters; review it before upgrading.';
            END IF;
        ELSE
            IF EXISTS (SELECT 1 FROM jobs WHERE (job_url IS NULL OR job_url='') AND CHAR_LENGTH(posting_url)>300) THEN
                SELECT job_id, posting_url FROM jobs WHERE (job_url IS NULL OR job_url='') AND CHAR_LENGTH(posting_url)>300;
                SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a legacy URL is too long to copy; no URL was shortened.';
            END IF;
        END IF;
    END IF;

    -- PHASE 2: all preflight checks passed. Create and populate canonical fields.
    SET SESSION sql_safe_updates = 0;

    IF v_has_url = 0 THEN
        ALTER TABLE jobs ADD COLUMN job_url VARCHAR(300) NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='jobs' AND COLUMN_NAME='requirements') THEN
        ALTER TABLE jobs ADD COLUMN requirements JSON NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='applications' AND COLUMN_NAME='interview_data') THEN
        ALTER TABLE applications ADD COLUMN interview_data JSON NULL;
    END IF;
    IF v_has_name = 0 THEN
        ALTER TABLE contacts ADD COLUMN contact_name VARCHAR(100) NULL;
    END IF;
    IF v_has_title = 0 THEN
        ALTER TABLE contacts ADD COLUMN title VARCHAR(100) NULL;
    END IF;

    IF v_has_legacy_url = 1 THEN
        UPDATE jobs SET job_url=posting_url
          WHERE (job_url IS NULL OR job_url='') AND posting_url IS NOT NULL;
    END IF;
    IF v_has_first = 1 AND v_has_last = 1 THEN
        UPDATE contacts
          SET contact_name=CONCAT_WS(' ',NULLIF(TRIM(first_name),''),NULLIF(TRIM(last_name),''))
          WHERE contact_name IS NULL OR TRIM(contact_name)='';
    END IF;
    IF v_has_legacy_title = 1 THEN
        UPDATE contacts SET title=job_title
          WHERE (title IS NULL OR title='') AND job_title IS NOT NULL;
    END IF;

    -- Retain old names, but make the historical fields optional so final-app
    -- INSERTs containing only contact_name can succeed.
    IF v_has_first = 1 THEN
        ALTER TABLE contacts MODIFY COLUMN first_name VARCHAR(50) NULL DEFAULT NULL;
    END IF;
    IF v_has_last = 1 THEN
        ALTER TABLE contacts MODIFY COLUMN last_name VARCHAR(50) NULL DEFAULT NULL;
    END IF;

    ALTER TABLE contacts
        MODIFY COLUMN contact_name VARCHAR(100) NOT NULL,
        MODIFY COLUMN title VARCHAR(100) NULL;
    ALTER TABLE jobs
        MODIFY COLUMN salary_min INT NULL,
        MODIFY COLUMN salary_max INT NULL,
        MODIFY COLUMN job_type ENUM('Full-time','Part-time','Contract','Internship') NULL DEFAULT 'Full-time',
        MODIFY COLUMN job_url VARCHAR(300) NULL;
    ALTER TABLE applications
        MODIFY COLUMN status ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn') NOT NULL DEFAULT 'Applied',
        MODIFY COLUMN cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE;

    -- Verify all original record counts before reporting success.
    IF (SELECT COUNT(*) FROM companies) <> v_companies
       OR (SELECT COUNT(*) FROM jobs) <> v_jobs
       OR (SELECT COUNT(*) FROM applications) <> v_applications
       OR (SELECT COUNT(*) FROM contacts) <> v_contacts THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: record counts changed; inspect the database and your backup.';
    END IF;
    IF EXISTS (SELECT 1 FROM contacts WHERE contact_name IS NULL OR TRIM(contact_name)='') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'STOP: a contact name is still missing; inspect contacts.';
    END IF;

    SET SESSION sql_safe_updates = v_safe_updates;

    SELECT 'UPGRADE COMPLETE' AS result,
           v_companies AS companies, v_jobs AS jobs,
           v_applications AS applications, v_contacts AS contacts;
END$$
DELIMITER ;

SET SESSION sql_mode = @jt_final_saved_sql_mode;
CALL jt_upgrade_final_20261123_v2();
DROP PROCEDURE IF EXISTS jt_upgrade_final_20261123_v2;

-- Success is reported ONLY inside the procedure. A STOP/error means review
-- the preceding result grid and error message before proceeding to the app.
-- Next: run python check_database.py with the configured project environment.
