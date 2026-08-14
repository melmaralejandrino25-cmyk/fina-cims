import os
import sqlite3
import sys

from database import DB_PATH, TABLES, get_db, init_db, is_postgres, reset_postgres_sequences


def table_columns(sqlite_conn, table):
    rows = sqlite_conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [row["name"] for row in rows]


def clear_table(postgres_conn, table):
    postgres_conn.cursor().execute(f"DELETE FROM {table}")


def migrate_table(sqlite_conn, postgres_conn, table):
    columns = table_columns(sqlite_conn, table)
    quoted_columns = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))

    rows = sqlite_conn.execute(f"SELECT {quoted_columns} FROM {table} ORDER BY id").fetchall()
    if not rows:
        return 0

    postgres_conn.cursor().executemany(
        f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders})",
        [tuple(row[column] for column in columns) for row in rows],
    )
    return len(rows)


def main():
    if not is_postgres():
        print("DATABASE_URL is required and must point to PostgreSQL.", file=sys.stderr)
        return 1

    sqlite_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    if not os.path.exists(sqlite_path):
        print(f"SQLite database not found: {sqlite_path}", file=sys.stderr)
        return 1

    init_db()

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_conn.execute("PRAGMA foreign_keys = ON")

    postgres = get_db()
    try:
        migrated = {}
        for table in reversed(TABLES):
            clear_table(postgres.conn, table)

        for table in TABLES:
            migrated[table] = migrate_table(sqlite_conn, postgres.conn, table)

        reset_postgres_sequences(postgres.conn)
        postgres.commit()

        for table, count in migrated.items():
            print(f"{table}: {count} row(s) migrated")
        return 0
    except Exception:
        postgres.rollback()
        raise
    finally:
        sqlite_conn.close()
        postgres.close()


if __name__ == "__main__":
    raise SystemExit(main())
