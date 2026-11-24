-- COP4751 | Job Application Tracker
-- Fresh installations only. Non-destructive CREATE IF NOT EXISTS statements.
-- Existing COP4751 Assignment 1-7 databases should instead run migrate_existing.sql.
CREATE DATABASE IF NOT EXISTS job_tracker
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE job_tracker;

CREATE TABLE IF NOT EXISTS companies (
    company_id INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry VARCHAR(50),
    website VARCHAR(200),
    city VARCHAR(50),
    state VARCHAR(50),
    notes TEXT
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS jobs (
    job_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    job_title VARCHAR(100) NOT NULL,
    job_type ENUM('Full-time','Part-time','Contract','Internship') DEFAULT 'Full-time',
    salary_min INT,
    salary_max INT,
    job_url VARCHAR(300),
    date_posted DATE,
    requirements JSON,
    CONSTRAINT fk_jobs_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_jobs_company (company_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS applications (
    application_id INT PRIMARY KEY AUTO_INCREMENT,
    job_id INT NOT NULL,
    application_date DATE NOT NULL,
    status ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn')
        NOT NULL DEFAULT 'Applied',
    resume_version VARCHAR(50),
    cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE,
    interview_data JSON,
    CONSTRAINT fk_applications_job FOREIGN KEY (job_id)
        REFERENCES jobs(job_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_applications_job (job_id),
    INDEX idx_applications_status (status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS contacts (
    contact_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes TEXT,
    CONSTRAINT fk_contacts_company FOREIGN KEY (company_id)
        REFERENCES companies(company_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_contacts_company (company_id)
) ENGINE=InnoDB;

-- Verification (should show four required tables; legacy installations may have extras):
SHOW TABLES;
DESCRIBE jobs;
DESCRIBE applications;
