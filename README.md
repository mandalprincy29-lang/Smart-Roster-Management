# Smart Roster Management System

A Flask + SQLite starter implementation for the DataStraw roster-management assessment.

## Features
- Employee and pod management, including weekly-off configuration.
- Brand and process management.
- Brand/process operating rules and minimum staffing.
- Explicit employee eligibility mapping to each brand/process.
- Public holidays, approved leave and approved comp-off records.
- Monthly roster generation with weekly-off, leave, holiday-rule and duplicate-day checks.
- Visible `GAP` rows when staffing cannot be met.
- Manual roster reassignment with basic availability and same-day overlap validation.
- Optional fictional demo data loader.

## Important scheduling assumptions
1. Brand/process operating calendar and employee weekly-off/absence are separate concepts.
2. `All Days` operates on Sundays and public holidays.
3. `Except Public Holidays` operates on Sundays but not configured public holidays.
4. `Sundays & Holidays Off` does not operate on Sundays or configured public holidays.
5. An employee can be assigned to at most one process per calendar day in this first version.
6. Only employees explicitly mapped to a brand/process are eligible for it.
7. All leave records created in the interface are treated as approved.
8. Comp-off records are treated as employee unavailability on the selected date.
9. The demo loader creates fictional sample records only when needed; it does not overwrite existing records.

## Run locally
1. Install Python 3.10+.
2. Open this folder in VS Code.
3. In the terminal run:
   `python -m venv .venv`
4. Activate the environment:
   - Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
5. Install dependencies:
   `pip install -r requirements.txt`
6. Copy `.env.example` to `.env` if desired.
7. Start:
   `python app.py`
8. Open `http://127.0.0.1:5000`.

## Existing project data
The app uses Flask-SQLAlchemy's SQLite instance database at `instance/roster.db` for the default URI. If the previous app was run from this same project folder with the same URI, its database should be reused. The startup migration adds new columns where needed and does not intentionally delete existing tables or rows. Keep a backup of `instance/roster.db` before switching versions.

If your existing database is in a different location, set `DATABASE_URL` in `.env` to its absolute SQLite URI, for example:
`DATABASE_URL=sqlite:///C:/full/path/to/instance/roster.db`
Use forward slashes in Windows paths.

## Demo workflow
1. Click **Load fictional demo data** to create missing sample employees and initial mappings.
2. Check employee weekly offs.
3. Configure additional brand/process rules and eligible employees.
4. Add public holidays and approved leave/comp-off.
5. Select a month and generate the roster.
6. Review `GAP` rows; a gap means minimum coverage was not achieved.
7. Try a manual reassignment and review the roster again.

## Architecture / decision notes
- Flask handles HTTP routes and server-rendered pages.
- SQLAlchemy models represent pods, employees, brands, processes, rules, employee eligibility, holidays, leave, comp-off and roster entries.
- SQLite is used for a simple local demo; PostgreSQL is preferable for a multi-user production deployment.
- Scheduling is a deterministic constraint-based first-fit allocator. It prioritizes hard availability and minimum-staff constraints, and flags unsatisfied coverage rather than claiming a complete roster.
- The current version does not implement authentication, role-based access, concurrency locking, advanced fairness optimization, shift-hour modelling, public-holiday jurisdiction calendars, or production-grade approval workflows. These should be described honestly in the approach note and can be extended.
