import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


TABLES = [
    "users",
    "wet_municipalities",
    "dry_municipalities",
    "wet_associations",
    "dry_associations",
    "wet_varieties",
    "dry_varieties",
    "wet_farmers",
    "dry_farmers",
]

DEFAULT_VARIETIES = [
    ("Bigante",),
    ("Lp2096",),
    ("Nk 5017",),
    ("S6003",),
    ("SL 20",),
    ("SL 19",),
    ("JACKPOT",),
    ("SL 8",),
    ("TH 82",),
]


def _default_admin_password():
    from werkzeug.security import generate_password_hash

    return generate_password_hash("admin")


def is_postgres():
    return bool(DATABASE_URL)


def _postgres_url():
    if DATABASE_URL.startswith("postgres://"):
        return DATABASE_URL.replace("postgres://", "postgresql://", 1)
    return DATABASE_URL


def _translate_sql(sql):
    if not is_postgres():
        return sql
    return sql.replace("?", "%s")


class PostgresCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=None):
        self.cursor.execute(_translate_sql(sql), params or ())
        return self

    def executemany(self, sql, params=None):
        self.cursor.executemany(_translate_sql(sql), params or [])
        return self

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def __iter__(self):
        return iter(self.cursor)

    def __getattr__(self, name):
        return getattr(self.cursor, name)


class PostgresConnection:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        cursor = self.cursor()
        cursor.execute(sql, params)
        return cursor

    def executemany(self, sql, params=None):
        cursor = self.cursor()
        cursor.executemany(sql, params)
        return cursor

    def cursor(self):
        return PostgresCursor(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_db():
    if is_postgres():
        import psycopg2
        from psycopg2.extras import DictCursor

        conn = psycopg2.connect(_postgres_url(), cursor_factory=DictCursor)
        return PostgresConnection(conn)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init_sqlite(conn):
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wet_municipalities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dry_municipalities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wet_associations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        municipality_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(municipality_id) REFERENCES wet_municipalities(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dry_associations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        municipality_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY(municipality_id) REFERENCES dry_municipalities(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wet_varieties(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dry_varieties(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
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
        FOREIGN KEY(association_id) REFERENCES wet_associations(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
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
        FOREIGN KEY(association_id) REFERENCES dry_associations(id) ON DELETE CASCADE
    )
    """)

    cursor.execute(
        "INSERT OR IGNORE INTO users(username,password,role) VALUES (?,?,?)",
        ("admin", _default_admin_password(), "admin"),
    )
    cursor.executemany("INSERT OR IGNORE INTO wet_varieties(name) VALUES(?)", DEFAULT_VARIETIES)
    cursor.executemany("INSERT OR IGNORE INTO dry_varieties(name) VALUES(?)", DEFAULT_VARIETIES)


def _init_postgres(conn):
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wet_municipalities(
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dry_municipalities(
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wet_associations(
        id SERIAL PRIMARY KEY,
        municipality_id INTEGER NOT NULL REFERENCES wet_municipalities(id) ON DELETE CASCADE,
        name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dry_associations(
        id SERIAL PRIMARY KEY,
        municipality_id INTEGER NOT NULL REFERENCES dry_municipalities(id) ON DELETE CASCADE,
        name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wet_varieties(
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dry_varieties(
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wet_farmers(
        id SERIAL PRIMARY KEY,
        association_id INTEGER NOT NULL REFERENCES wet_associations(id) ON DELETE CASCADE,
        rsbsa TEXT,
        last_name TEXT,
        first_name TEXT,
        middle_name TEXT,
        suffix TEXT,
        area DOUBLE PRECISION DEFAULT 0,
        variety TEXT,
        sacks DOUBLE PRECISION DEFAULT 0,
        kg DOUBLE PRECISION DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dry_farmers(
        id SERIAL PRIMARY KEY,
        association_id INTEGER NOT NULL REFERENCES dry_associations(id) ON DELETE CASCADE,
        rsbsa TEXT,
        last_name TEXT,
        first_name TEXT,
        middle_name TEXT,
        suffix TEXT,
        area DOUBLE PRECISION DEFAULT 0,
        variety TEXT,
        sacks DOUBLE PRECISION DEFAULT 0,
        kg DOUBLE PRECISION DEFAULT 0
    )
    """)

    cursor.execute(
        """
        INSERT INTO users(username,password,role)
        VALUES (%s,%s,%s)
        ON CONFLICT (username) DO NOTHING
        """,
        ("admin", _default_admin_password(), "admin"),
    )
    cursor.executemany(
        "INSERT INTO wet_varieties(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
        DEFAULT_VARIETIES,
    )
    cursor.executemany(
        "INSERT INTO dry_varieties(name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
        DEFAULT_VARIETIES,
    )


def reset_postgres_sequences(conn):
    cursor = conn.cursor()
    for table in TABLES:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence(%s, 'id'),
                COALESCE((SELECT MAX(id) FROM """ + table + """), 1),
                (SELECT COUNT(*) FROM """ + table + """) > 0
            )
            """,
            (table,),
        )


def init_db(app=None):
    conn = get_db()
    try:
        if is_postgres():
            _init_postgres(conn.conn)
            reset_postgres_sequences(conn.conn)
        else:
            _init_sqlite(conn)
        conn.commit()
    finally:
        conn.close()


init_app = init_db
