import os
import sqlite3
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(app=None):
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    users = [
        ("admin", generate_password_hash("admin"), "admin")
    ]

    c.executemany("""
        INSERT OR IGNORE INTO users(username,password,role)
        VALUES (?,?,?)
    """, users)

    # ...ituloy ang ibang CREATE TABLE...
    # ==========================
    # WET MUNICIPALITIES
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS wet_municipalities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    # ==========================
    # DRY MUNICIPALITIES
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS dry_municipalities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    # ==========================
    # WET ASSOCIATIONS
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS wet_associations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        municipality_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(municipality_id)
        REFERENCES wet_municipalities(id)
        ON DELETE CASCADE
    )
    """)

    # ==========================
    # DRY ASSOCIATIONS
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS dry_associations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        municipality_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(municipality_id)
        REFERENCES dry_municipalities(id)
        ON DELETE CASCADE
    )
    """)

    # ==========================
    # WET VARIETIES
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS wet_varieties(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    # ==========================
    # DRY VARIETIES
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS dry_varieties(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    default_varieties = [
        ("Bigante",),
        ("Lp2096",),
        ("Nk 5017",),
        ("S6003",),
        ("SL 20",),
        ("SL 19",),
        ("JACKPOT",),
        ("SL 8",),
        ("TH 82",)
    ]

    c.executemany("""
        INSERT OR IGNORE INTO wet_varieties(name)
        VALUES(?)
    """, default_varieties)

    c.executemany("""
        INSERT OR IGNORE INTO dry_varieties(name)
        VALUES(?)
    """, default_varieties)

    # ==========================
    # WET FARMERS
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS wet_farmers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        association_id INTEGER NOT NULL,
        rsbsa TEXT,
        last_name TEXT,
        first_name TEXT,
        middle_name TEXT,
        suffix TEXT,
        area REAL DEFAULT 0,
        variety TEXT,
        sacks REAL DEFAULT 0,
        kg REAL DEFAULT 0,
        FOREIGN KEY(association_id)
        REFERENCES wet_associations(id)
        ON DELETE CASCADE
    )
    """)

    # ==========================
    # DRY FARMERS
    # ==========================
    c.execute("""
    CREATE TABLE IF NOT EXISTS dry_farmers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        association_id INTEGER NOT NULL,
        rsbsa TEXT,
        last_name TEXT,
        first_name TEXT,
        middle_name TEXT,
        suffix TEXT,
        area REAL DEFAULT 0,
        variety TEXT,
        sacks REAL DEFAULT 0,
        kg REAL DEFAULT 0,
        FOREIGN KEY(association_id)
        REFERENCES dry_associations(id)
        ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


# Alias for Flask extension-style initialization
init_app = init_db