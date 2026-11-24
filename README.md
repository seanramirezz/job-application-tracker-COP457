# ApplyFlow — Job Application Tracker

**COP4751 Final Project**  
**Author:** Sean Ramirez  
**GitHub:** [seanramirezz](https://github.com/seanramirezz)

ApplyFlow is a local web application for organizing companies, job openings, applications, and professional contacts. It uses Python, Flask, MySQL, HTML, and CSS. A Job Match feature ranks saved jobs based on how closely their required skills match the user's skills.

## Features

| Page | Functionality |
|---|---|
| Dashboard | Displays record totals, the application pipeline, and recent activity. |
| Companies | Create, search, view, edit, and delete companies. |
| Jobs | Manage job openings, company relationships, salary ranges, posting URLs, and required/preferred skills. |
| Applications | Create, view, edit, and delete applications; filter by status; store interview information as JSON. |
| Contacts | Create, search, view, edit, and delete professional contacts linked to companies. |
| Job Match | Rank saved jobs by matching skills and display matched and missing requirements. |

Additional functionality includes:

- Server-side form validation.
- Parameterized SQL queries.
- CSRF protection for form submissions.
- Delete confirmation.
- Protection against deleting records with dependent records.
- JSON storage for job requirements and interview information.
- Responsive page layouts.

## Requirements

- Python 3.10 or later.
- MySQL Server 8 or later.
- MySQL Workbench for executing the supplied SQL scripts.
- A web browser.
- A terminal; VS Code is recommended.
- Python dependencies listed in `requirements.txt`.

The Python dependencies include:

- Flask.
- mysql-connector-python.
- python-dotenv.

## Project Files

| File or folder | Purpose |
|---|---|
| `app.py` | Flask routes, page rendering, and CRUD controllers. |
| `database.py` | MySQL connections, parameterized queries, and transaction handling. |
| `logic.py` | Form validation, JSON handling, and job matching. |
| `check_database.py` | Read-only checks of the database structure. |
| `templates/` | HTML templates, shared layouts, and icons. |
| `static/style.css` | Application styling. |
| `schema.sql` | Creates the database and tables for a fresh installation. |
| `migrate_existing.sql` | Upgrades the existing database from earlier coursework. |
| `seed_demo.sql` | Adds optional fictional demonstration records. |
| `requirements.txt` | Lists the Python dependencies. |
| `.env.example` | Provides sample configuration without actual credentials. |
| `.gitignore` | Excludes local credentials, virtual environments, and generated files from Git. |
| `SETUP_WINDOWS.bat` | Creates the virtual environment, installs dependencies, and opens local configuration. |
| `RUN_WINDOWS.bat` | Checks the database and starts the application. |
| `tests/` | Contains automated logic, metadata, structure, and template tests. |
| `AI_USAGE.md` | Documents AI assistance, useful output, changes, and lessons learned. |
| `README.md` | Provides installation, usage, and submission instructions. |

The final submission also requires a separately recorded `demo_video.mp4` showing the running application.

## Windows Setup

### 1. Install the prerequisites

Install Python, MySQL Server, and MySQL Workbench.

Make sure MySQL Server is running and that you can connect to it through MySQL Workbench.

### 2. Open the project

Clone the project repository or download and extract its source files.

Open the folder containing `app.py`, `requirements.txt`, and the Windows batch files in VS Code.

Select **Terminal → New Terminal**.

Run the commands below from that project folder.

### 3. Create the database

For a fresh installation:

1. Open MySQL Workbench.
2. Connect to your MySQL server.
3. Select **File → Open SQL Script**.
4. Open `schema.sql`.
5. Execute the entire script.

The script creates the `job_tracker` database and these four tables:

- `companies`
- `jobs`
- `applications`
- `contacts`

If you already have the database from earlier COP4751 assignments, follow the **Upgrading an Existing Coursework Database** section instead.

`schema.sql` uses `CREATE TABLE IF NOT EXISTS`. It does not update the structure of incompatible tables that already exist.

### 4. Install the Python dependencies

In the VS Code PowerShell terminal, run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

These commands create a virtual environment and install the required Python packages.

### 5. Configure the local environment

Create `.env` if it does not already exist, then open it:

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

notepad .env
```

Use the following configuration:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=YOUR_MYSQL_PASSWORD
DB_NAME=job_tracker
SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET
FLASK_DEBUG=0
```

The MySQL username for my local setup is `root`.

Replace `YOUR_MYSQL_PASSWORD` with the password for your local MySQL account. Other users should adjust the username, host, and port if their MySQL setup uses different values.

Generate a random Flask secret key with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated value into `SECRET_KEY` and save `.env`.

Keep `.env` and actual passwords on your computer. Upload `.env.example` to GitHub so another user can create their own configuration.

### 6. Check the database

Run:

```powershell
.\.venv\Scripts\python.exe check_database.py
```

The checker verifies the four required tables and three foreign-key relationships.

Continue when all checks report `[OK]` and the final message reports `PASS`.

### 7. Start the application

Run:

```powershell
.\.venv\Scripts\python.exe app.py
```

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

Leave the terminal open while using the application.

To stop the server, press **Ctrl + C** in the terminal.

To restart it, run the same command again.

## Windows Batch-File Alternative

After initializing the MySQL database, you can use the included batch files instead of the manual Python setup commands.

First, run:

```powershell
.\SETUP_WINDOWS.bat
```

The setup script:

- Creates the `.venv` virtual environment.
- Installs the Python dependencies.
- Creates `.env` if it does not already exist.
- Opens `.env` for configuration.

Complete the configuration and finish the setup prompts.

Then run:

```powershell
.\RUN_WINDOWS.bat
```

The run script checks the database and starts Flask only if the checks pass.

The setup script does not initialize MySQL. The database scripts must be executed separately through MySQL Workbench.

To stop the application, press **Ctrl + C**. If Windows asks whether to terminate the batch job, enter **Y**.

## Upgrading an Existing Coursework Database

Use `migrate_existing.sql` when upgrading the existing `job_tracker` database containing the four core tables from earlier assignments.

1. Stop the Flask application.
2. Export a backup of the database structure and data through **MySQL Workbench → Server → Data Export**.
3. Open `migrate_existing.sql` in MySQL Workbench.
4. Execute the entire script.
5. Review the results.
6. Confirm that the script reports **UPGRADE COMPLETE** and that the record counts are unchanged.
7. Run `check_database.py` before restarting the application.

The migration adds missing final-project fields, copies compatible legacy contact names, contact titles, and posting URLs, and converts supported salary and enum types.

Existing rows, IDs, and extra coursework objects are retained. Older contact fields remain as historical data; the application updates `contact_name` and `title` going forward.

If the script reports a `STOP` error, review the listed records and error message before continuing. The script does not automatically reinterpret unknown statuses, round fractional salaries, or shorten oversized values.

MySQL schema changes commit individually, so the migration is not one rollbackable transaction. Keep the backup and review any interruption before rerunning the script.

Newly added JSON columns initially contain `NULL`. Add required skills through the Jobs form before expecting meaningful Job Match scores for those jobs.

## macOS and Linux Setup

First initialize the database using `schema.sql`, or follow the migration instructions for an existing coursework database.

From the project directory, run:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `.env` if it does not already exist:

```bash
if [ ! -f .env ]; then
    cp .env.example .env
fi
```

Edit `.env` with your MySQL connection settings and a random secret key.

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Check the database:

```bash
python check_database.py
```

If the result is `PASS`, start the application:

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Database Structure

| Table | Primary key | Purpose and relationship |
|---|---|---|
| `companies` | `company_id` | Stores company details and is referenced by jobs and contacts. |
| `jobs` | `job_id` | Stores job listings and references `companies.company_id`. |
| `applications` | `application_id` | Stores application information and references `jobs.job_id`. |
| `contacts` | `contact_id` | Stores professional contacts and references `companies.company_id`. |

Each table uses an auto-incrementing primary key.

The foreign-key relationships are:

- `jobs.company_id` → `companies.company_id`
- `applications.job_id` → `jobs.job_id`
- `contacts.company_id` → `companies.company_id`

The fresh schema blocks deletion of companies or jobs while dependent records exist.

For temporary test records, delete applications and contacts first, then their jobs, and finally their company.

### JSON fields

- `jobs.requirements` stores required skills, preferred skills, and additional job requirements.
- `applications.interview_data` stores interview-related information.

The complete table definitions are provided in `schema.sql`.

## Optional Demonstration Data

Execute `seed_demo.sql` in MySQL Workbench if you want fictional example records.

On a fresh database, the script adds:

- 3 companies.
- 3 jobs.
- 3 applications.
- 2 contacts.

The script skips matching existing examples instead of resetting records that have been edited.

## How Job Match Works

Enter a comma-separated list of skills, such as:

```text
Python, SQL, Flask
```

The application compares those skills with each job's required skills:

```text
Match percentage = (matched required skills / total required skills) × 100
```

Matching:

- Ignores capitalization.
- Ignores duplicate skills.
- Uses required skills to calculate the percentage.
- Displays preferred skills separately.
- Shows matched and missing required skills.
- Ranks jobs from highest to lowest match percentage.
- Marks jobs without required skills as unscorable and displays 0%.

Requirements are read from the MySQL JSON data using `required_skills`, with support for the older `skills` key when `required_skills` is absent.

For the supplied, unmodified sample jobs, entering `Python, SQL, Flask` produces:

| Company | Job | Expected match | Missing required skills |
|---|---|---:|---|
| TechCorp | Software Developer | 100% | None |
| DataCo | Data Analyst | 67% | Tableau |
| CloudNine Labs | Cloud Engineer | 33% | AWS, Linux |

Results depend on the requirements currently stored in the database.

## Testing and Verification

### Database structure check

On Windows:

```powershell
.\.venv\Scripts\python.exe check_database.py
```

The checker reads database metadata and checks required columns, data types, keys, and compatibility with application inserts.

A successful result ends with `PASS`.

This verifies the database structure. CRUD behavior still needs to be tested through the running application.

### Automated tests

On Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

On macOS or Linux, with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
```

The automated tests cover:

- Application logic.
- Form validation.
- JSON handling.
- Schema-checking logic using metadata fixtures.
- Required project files.
- Template compilation.

These tests do not require a running MySQL server and do not replace live application testing.

### Manual application checks

1. Create a temporary company.
2. Create a job linked to that company.
3. Create an application linked to the job.
4. Create a contact linked to the company.
5. Open and edit each record.
6. Check the saved values in MySQL Workbench.
7. Test search, application status filtering, required fields, salary validation, and JSON input.
8. Verify Job Match scores against the saved required skills.
9. Confirm that deleting a parent with dependent records is blocked.
10. Delete the temporary application and contact, then the job, and finally the company.
11. Confirm that the database and dashboard reflect the changes.

## AI Assistance

AI tools were used to assist with development, troubleshooting, and documentation.

See [AI_USAGE.md](AI_USAGE.md) for the tools used, key prompts, useful output, modifications, and lessons learned.

## Demonstration Video

The course submission requires an actual **3–7-minute demonstration video** showing the running:

- **Client:** The application in a browser.
- **Server:** The Flask application in the terminal.
- **Database:** MySQL Workbench and relevant query results.

The demonstration should include:

- The dashboard and navigation.
- Creating, viewing, editing, and deleting records.
- Job Match percentages and matched/missing skills.
- Evidence that changes made through the website are saved in MySQL.
- A brief view of the project files and setup documentation.

Save the recording as `demo_video.mp4` and upload the actual video file to the GitHub repository.

Narration is optional. The assignment states that projects without the required video will not be graded.

Keep passwords and the contents of `.env` off-screen while recording.

## Submission

The final repository should contain:

- Application source files.
- HTML templates and static assets.
- Database scripts.
- Python dependency requirements.
- `.env.example` and `.gitignore`.
- Setup scripts and tests.
- `README.md`.
- `AI_USAGE.md`.
- The required demonstration video.

Exclude:

- `.env`
- `.venv` or other virtual-environment folders.
- `__pycache__` folders.
- Actual passwords or secret keys.
- Unrelated database backups.

Before submitting:

1. Commit and push the project files to the repository.
2. Upload `demo_video.mp4`.
3. Confirm that the uploaded video can be opened.
4. Make the repository public or provide the instructor with the required access.
5. Verify the setup from a separate clone or downloaded copy using this README.
6. Submit the specific project repository URL through the course assignment.

My GitHub profile is [https://github.com/seanramirezz](https://github.com/seanramirezz). The final submission must use the URL of the project repository.

## Troubleshooting

| Problem | Suggested action |
|---|---|
| Setup script is not recognized | Open the terminal in the folder containing the script and run `.\SETUP_WINDOWS.bat`. |
| Python or `py` is not recognized | Check the Python installation and reopen the terminal after installation. |
| A Python dependency is missing | Install `requirements.txt` using the same virtual-environment Python used to run the application. |
| MySQL connection is refused | Confirm that MySQL Server is running and that `DB_HOST` and `DB_PORT` are correct. |
| MySQL access is denied | Check the username and password in the local `.env` file. |
| Unknown database | Initialize a fresh database with `schema.sql` and confirm `DB_NAME=job_tracker`. |
| Missing columns or incompatible types | Review the existing-database migration instructions, then rerun the checker. |
| Migration reports `STOP` | Review the listed records and error, resolve the specific issue, and rerun the migration. |
| Parent record cannot be deleted | Delete its dependent records first. |
| JSON input is rejected | Enter a valid JSON object using double quotes, such as `{"interview_rounds": 1}`. |
| Job Match shows unscorable jobs | Add required skills to those jobs. |
| Port 5000 is already in use | Stop the previous Flask process before starting another instance. |

## Project Scope

ApplyFlow is intended for a local, single-user course demonstration. It does not include a user-account or authentication system and runs on `127.0.0.1` by default.