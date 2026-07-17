import os
from dotenv import load_dotenv

load_dotenv()

# ==========================
# Base Directory
# ==========================
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ==========================
# Security
# ==========================
SECRET_KEY = os.environ.get(
    "CIMS_SECRET_KEY",
    "change-this-before-production"
)

# ==========================
# Database
# ==========================
DATABASE = os.path.join(BASE_DIR, "database.db")

# ==========================
# Folders
# ==========================
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EXPORT_FOLDER = os.path.join(BASE_DIR, "exports")

# Automatically create folders if missing
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# ==========================
# Session Security
# ==========================
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Enable this only when using HTTPS in production
SESSION_COOKIE_SECURE = False

# ==========================
# Upload Limits
# ==========================
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
