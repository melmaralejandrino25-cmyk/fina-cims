import glob
import os
import shutil
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
import pandas as pd
from werkzeug.utils import secure_filename

from database import DB_PATH, get_db

settings_bp = Blueprint("settings", __name__)

MANILA = ZoneInfo("Asia/Manila")
BACKUP_FOLDER = "backups"
UPLOAD_FOLDER = "uploads"
TARGET_TABLES = [
    "wet_municipalities",
    "wet_associations",
    "wet_farmers",
    "dry_municipalities",
    "dry_associations",
    "dry_farmers",
]


# ==========================
# SETTINGS DASHBOARD
# ==========================
@settings_bp.route("/settings")
def settings():
    db_size = round(os.path.getsize(DB_PATH) / 1024 / 1024, 2) if os.path.exists(DB_PATH) else 0

    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    backup_files = glob.glob(os.path.join(BACKUP_FOLDER, "*.db"))
    backup_count = len(backup_files)

    backup_list = []
    for file in sorted(backup_files, key=os.path.getmtime, reverse=True):
        filename = os.path.basename(file)
        file_time = datetime.fromtimestamp(os.path.getmtime(file), MANILA)

        backup_list.append({
            "name": filename,
            "size": round(os.path.getsize(file) / 1024 / 1024, 2),
            "date": file_time.strftime("%b %d, %Y %I:%M %p")
        })

    last_backup = backup_list[0]["date"] if backup_list else "-"

    return render_template(
        "settings/dashboard.html",
        db_size=db_size,
        backup_count=backup_count,
        last_backup=last_backup,
        backup_list=backup_list
    )


# ==========================
# BACKUP DATABASE
# ==========================
@settings_bp.route("/settings/backup")
def backup_database():
    try:
        os.makedirs(BACKUP_FOLDER, exist_ok=True)
        now = datetime.now(MANILA)
        filename = now.strftime("cims_backup_%Y%m%d_%H%M%S.db")
        destination = os.path.join(BACKUP_FOLDER, filename)

        # Gamitin ang SQLite backup API para sa safe at hot-backup kahit may active connection
        src_conn = get_db()
        dst_conn = sqlite3.connect(destination)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()

        flash(f"Database backed up successfully! ({filename})", "success")
    except Exception as e:
        flash(f"Backup failed: {e}", "danger")

    return redirect(url_for("settings.settings"))


# ==========================
# DOWNLOAD BACKUP
# ==========================
@settings_bp.route("/settings/download/<filename>")
def download_backup(filename):
    filename = secure_filename(filename)
    return send_from_directory(BACKUP_FOLDER, filename, as_attachment=True)


# ==========================
# DELETE BACKUP
# ==========================
@settings_bp.route("/settings/delete/<filename>")
def delete_backup(filename):
    filename = secure_filename(filename)
    filepath = os.path.join(BACKUP_FOLDER, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        flash(f"Backup deleted successfully! ({filename})", "success")
    else:
        flash("Backup file not found.", "danger")

    return redirect(url_for("settings.settings"))


# ==========================
# RESTORE SAVED BACKUP
# ==========================
@settings_bp.route("/settings/restore/<filename>")
def restore_saved_backup(filename):
    filename = secure_filename(filename)
    backup_path = os.path.join(BACKUP_FOLDER, filename)

    if not os.path.exists(backup_path):
        flash("Backup file not found.", "danger")
        return redirect(url_for("settings.settings"))

    try:
        # Gamitin ang SQLite backup API para ligtas na ma-restore sa active main DB
        src_conn = sqlite3.connect(backup_path)
        dst_conn = get_db()
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()

        flash(f"Database restored successfully! ({filename})", "success")
    except Exception as e:
        flash(f"Restore failed: {e}", "danger")

    return redirect(url_for("settings.settings"))


# ==========================
# RESTORE DATABASE UPLOAD
# ==========================
@settings_bp.route("/settings/restore", methods=["POST"])
def restore_database():
    file = request.files.get("backup")

    if not file or file.filename == "":
        flash("Please select a backup file.", "danger")
        return redirect(url_for("settings.settings"))

    if not file.filename.endswith(".db"):
        flash("Invalid backup file.", "danger")
        return redirect(url_for("settings.settings"))

    temp_filename = secure_filename(file.filename)
    temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    try:
        file.save(temp_path)

        # Gamitin ang SQLite backup API mula sa in-upload na file papunta sa active DB
        src_conn = sqlite3.connect(temp_path)
        dst_conn = get_db()
        with dst_conn:
            src_conn.backup(dst_conn)
        src_conn.close()

        flash("Database restored successfully!", "success")
    except Exception as e:
        flash(f"Failed to restore database: {e}", "danger")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return redirect(url_for("settings.settings"))


# ==========================
# EXPORT TO EXCEL
# ==========================
@settings_bp.route("/settings/export")
def export_database():
    conn = get_db()
    filename = "CIMS_V7_Export.xlsx"

    try:
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            for table in TARGET_TABLES:
                df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                df.to_excel(writer, sheet_name=table[:31], index=False)

        return send_file(filename, as_attachment=True)
    except Exception as e:
        flash(f"Export failed: {e}", "danger")
        return redirect(url_for("settings.settings"))


# ==========================
# IMPORT FROM EXCEL
# ==========================
@settings_bp.route("/settings/import", methods=["POST"])
def import_database():
    file = request.files.get("excel")

    if not file or file.filename == "":
        flash("Please select an Excel file.", "danger")
        return redirect(url_for("settings.settings"))

    if not file.filename.endswith(".xlsx"):
        flash("Invalid Excel file.", "danger")
        return redirect(url_for("settings.settings"))

    filename = secure_filename(file.filename)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    temp_file = os.path.join(UPLOAD_FOLDER, filename)

    try:
        file.save(temp_file)
        conn = get_db()

        for table in TARGET_TABLES:
            df = pd.read_excel(temp_file, sheet_name=table)
            df.to_sql(table, conn, if_exists="replace", index=False)

        flash("Excel imported successfully!", "success")
    except Exception as e:
        flash(f"Import failed: {e}", "danger")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    return redirect(url_for("settings.settings"))