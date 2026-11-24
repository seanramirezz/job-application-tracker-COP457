# AI Usage Documentation

**Student:** Sean Ramirez
**Course:** COP4751
**Project:** ApplyFlow — Job Application Tracker

## Tools Used

I used ChatGPT (OpenAI) as a development and troubleshooting assistant. I used it to help interpret the project requirements, work on application code, resolve database compatibility issues, and organize the documentation.

The assistance included generating and revising code for Flask routes, MySQL queries and migration scripts, HTML/CSS templates, input validation, and the Job Match feature. I provided the assignment requirements and information about my existing database, configured the project locally, ran the application and SQL scripts, and checked the results.

## Key Prompts

The following summarize important requests I made during the project:

1. Help develop the Job Application Tracker according to the project specification and grading rubric.
2. Create a rubric checklist showing which requirements are implemented and which still need verification.
3. Help identify differences between my existing database and the structure required by the final application.
4. Help troubleshoot the errors encountered when upgrading the database.
6. Provide SQL queries to check whether records created, edited, or deleted through the website were updated in MySQL.
7. Help prepare the project documentation and submission materials.

I also supplied screenshots of table structures, query results, terminal messages, and application pages. These helped make the troubleshooting specific to my project.

## What Worked Well

### Database troubleshooting

AI assistance helped identify differences between the earlier coursework database and the final project requirements. For example, the existing contacts table used separate first and last names, while the final application expected a single contact name.

### Job Match logic

ChatGPT assisted with the code for comparing entered skills with the required skills stored in each job's JSON data. The implementation calculates a match percentage and identifies matched and missing skills.

### Verification queries

The SQL queries were useful for checking application behavior against the stored records. During the contact test, I created a temporary contact, viewed it, edited its title, and confirmed the updated values in MySQL Workbench. I then deleted the contact through the website and confirmed that it was removed from the database.

## What I Modified

I applied the following configuration and database changes with AI guidance:

### Local configuration

I configured the project to use my local MySQL connection and database. I also corrected the terminal's working directory after initially trying to run the setup script from the parent folder.

### Compatibility with the existing database

I provided the structure of my earlier database and used the revised migration script to make it compatible with the final application. This included populating `contact_name` and `title` from the older contact fields and adding the required URL and JSON fields.

The migration code was revised with AI assistance based on the actual table structure and errors I reported.

### Application status values

The migration stopped when it encountered older statuses such as `Interview Completed` and `Phone Screen`. I ran the suggested correction to map these records to supported statuses while preserving the original labels in JSON.

### Applying and checking the migration

After resolving the status issue, I reran the migration and received `UPGRADE COMPLETE`. I checked that the existing record counts were preserved:

- 6 companies
- 18 jobs
- 6 applications
- 6 contacts

These changes involved configuring the local environment and applying AI-assisted revisions to the existing database. I used the application's behavior and SQL results to check the outcome.

## Lessons Learned

This project showed me that AI-generated code needs to be checked against the actual database being used. Differences in column names, required fields, and allowed values can cause errors even when the application code appears reasonable.

I learned that providing specific error messages and screenshots makes troubleshooting more useful. Sharing the actual table structure helped identify issues that a general description of the project did not reveal.

I also learned to verify changes in MySQL instead of relying only on what appeared on the website. Checking the same record in the interface and the database helped me understand how the application interacts with stored data.

AI was helpful for code assistance, explanations, and troubleshooting. Running the project locally, checking suggested changes, and confirming the results were necessary parts of completing the work.