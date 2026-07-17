# CIMS V10 Rice Program Monitoring System

Flask-based monitoring system for Wet Season 2026 and Wet Season 2027 rice-program data. It supports municipality and association records, farmer Excel uploads, dashboard summaries, season comparison, exports, backups, and duplicate handling by RSBSA number.

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

## Deployment notes

- Set `CIMS_SECRET_KEY` in the host environment; do not commit secrets.
- Keep `FLASK_DEBUG=0` in production.
- `database.db`, `uploads`, `exports`, and `backups` are intentionally excluded from Git because they are local operational data.
- Back up the database before deploying a new version or restoring data.

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
