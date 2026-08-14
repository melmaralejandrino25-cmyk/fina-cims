# CIMS V10 Rice Program Monitoring System

Flask-based monitoring system for Wet Season 2026 and Wet Season 2027 rice-program data. It supports municipality and association records, farmer Excel uploads, dashboard summaries, season comparison, exports, backups, duplicate handling by RSBSA number, and PostgreSQL persistence for Render deployments.

## Features

- Wet Season 2026 and Wet Season 2027 farmer management
- Excel/CSV upload with RSBSA-based duplicate skipping
- Main executive dashboard and seasonal comparison dashboard
- Municipality and association production, area, farmer, and yield summaries
- Export and database backup/restore tools
- Fixed navigation sidebar across season pages

## Requirements

- Python 3.10 or newer
- pip

## Local setup

```powershell
git clone <your-github-repository-url>
cd CIMS-V10
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open `http://127.0.0.1:5000` in a browser. The application creates `database.db` automatically when it does not exist.

Local development uses SQLite when `DATABASE_URL` is blank. Production should set `DATABASE_URL` to PostgreSQL.

## Deployment notes

- Set `CIMS_SECRET_KEY` in the host environment; do not commit secrets.
- Set `DATABASE_URL` to the PostgreSQL internal database URL on Render.
- Keep `FLASK_DEBUG=0` in production.
- `database.db`, `uploads`, `exports`, and `backups` are intentionally excluded from Git because they are local operational data.
- Render disks are not persistent unless configured separately, so production data must live in PostgreSQL.
- The included `Procfile` starts the app with `gunicorn app:app`.
- SQLite `.db` backup/restore actions in Settings are disabled when PostgreSQL is active. Use Render/PostgreSQL backups for production.

## Migrate SQLite data to PostgreSQL

Run this once after creating the PostgreSQL database and setting `DATABASE_URL`:

```powershell
$env:DATABASE_URL="<your-render-postgresql-internal-url>"
python migrate_sqlite_to_postgres.py database.db
```

The migration creates missing tables, clears existing PostgreSQL table data, copies all rows from SQLite, preserves IDs and foreign-key relationships, and resets PostgreSQL sequences.

## Render setup

1. Create a PostgreSQL database in Render.
2. Copy the database's Internal Database URL.
3. In the Render web service environment variables, set:
   - `DATABASE_URL=<internal database url>`
   - `CIMS_SECRET_KEY=<long random secret>`
   - `FLASK_DEBUG=0`
4. Use `pip install -r requirements.txt` as the build command.
5. Use `gunicorn app:app` as the start command, or let Render read the included `Procfile`.
6. Deploy the app.
7. Run `python migrate_sqlite_to_postgres.py database.db` once from a machine that has access to the PostgreSQL URL.

## GitHub upload

1. Extract this project folder.
2. Create an empty GitHub repository.
3. In the project folder, run:

```powershell
git init
git add .
git commit -m "Initial CIMS V10 release"
git branch -M main
git remote add origin <your-github-repository-url>
git push -u origin main
```

Do not use `git add -f` for `.env`, `database.db`, uploads, backups, or exports.
