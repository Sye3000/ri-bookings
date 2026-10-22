

"""database.py — database foundation for Richfield Booking System."""

import hashlib
import hmac
import os
import re
import sqlite3

DB_FILE = "richfield.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS campuses (
    campus_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    max_duration_minutes INTEGER NOT NULL CHECK(max_duration_minutes > 0),
    closing_time TEXT
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK(
        role IN ('lecturer', 'campus_admin', 'system_operator')
    ),
    campus_id INTEGER,
    email TEXT,
    must_change_password INTEGER NOT NULL DEFAULT 0 CHECK(must_change_password IN (0, 1)),
    FOREIGN KEY(campus_id) REFERENCES campuses(campus_id)
);

CREATE TABLE IF NOT EXISTS resources (
    resource_id TEXT PRIMARY KEY,
    campus_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK(capacity > 0),
    FOREIGN KEY(campus_id) REFERENCES campuses(campus_id)
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    resource_id TEXT NOT NULL,
    booking_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id),
    FOREIGN KEY(resource_id) REFERENCES resources(resource_id)
);
"""


def get_connection(db_file=None):
    """Connect to SQLite and enforce foreign-key constraints."""
    conn = sqlite3.connect(db_file or DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password, salt=None):
    """Hash a password using PBKDF2 and a unique random salt."""
    if salt is None:
        salt = os.urandom(16).hex()

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        100_000
    )
    return digest.hex(), salt


def verify_password(password, stored_hash, salt):
    """Check a password without storing it in plain text."""
    new_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(new_hash, stored_hash)


def create_tables(conn):
    """Create tables and safely migrate older databases."""
    conn.executescript(SCHEMA)

    # Migrate existing databases without deleting existing records.
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if "email" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "must_change_password" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN "
            "must_change_password INTEGER NOT NULL DEFAULT 0"
        )

    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique "
        "ON users(email) WHERE email IS NOT NULL AND email <> ''"
    )
    conn.commit()


def seed_data(conn):
    """Insert initial campuses, accounts and resources once."""
    if conn.execute("SELECT COUNT(*) FROM campuses").fetchone()[0] > 0:
        return

    campuses = [
        ("Campus A", 120, None),
        ("Campus B", 180, None),
        ("Campus C", 240, "18:00"),
    ]

    conn.executemany(
        """
        INSERT INTO campuses
            (name, max_duration_minutes, closing_time)
        VALUES (?, ?, ?)
        """,
        campuses
    )

    def add_user(username, full_name, password, role, campus_id=None):
        password_hash, salt = hash_password(password)

        conn.execute(
            """
            INSERT INTO users
                (username, full_name, password_hash, salt, role, campus_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, full_name, password_hash, salt, role, campus_id)
        )

    add_user(
        "operator", "System Operator",
        "Operator123", "system_operator"
    )
    add_user(
        "admin_a", "Admin Campus A",
        "AdminA123", "campus_admin", 1
    )
    add_user(
        "admin_b", "Admin Campus B",
        "AdminB123", "campus_admin", 2
    )
    add_user(
        "admin_c", "Admin Campus C",
        "AdminC123", "campus_admin", 3
    )

    resources = [
        ("A-LAB-01", 1, "Computer Lab 1", "Lab", 30),
        ("A-VC-01", 1, "Venue Room 1", "Venue", 60),
        ("B-LAB-01", 2, "Computer Lab 1", "Lab", 25),
        ("B-PRJ-01", 2, "Projector Kit", "Equipment", 1),
        ("C-LAB-01", 3, "Computer Lab 1", "Lab", 40),
        ("C-VC-01", 3, "Lecture Hall", "Venue", 120),
    ]

    conn.executemany(
        """
        INSERT INTO resources
            (resource_id, campus_id, name, resource_type, capacity)
        VALUES (?, ?, ?, ?, ?)
        """,
        resources
    )

    conn.commit()


def initialise_database(db_file=None):
    """Create tables and seed initial data when necessary."""
    conn = get_connection(db_file)

    try:
        create_tables(conn)
        seed_data(conn)
        return conn
    except Exception:
        conn.close()
        raise


def create_lecturer(conn, full_name, username, email, campus_id,
                    temporary_password):
    """Create a lecturer account that must change its password at first login."""
    full_name = full_name.strip()
    username = username.strip()
    email = email.strip().lower()

    if not all((full_name, username, email, temporary_password)):
        raise ValueError("All lecturer fields are required.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid email address.")

    if conn.execute(
        "SELECT 1 FROM campuses WHERE campus_id = ?", (campus_id,)
    ).fetchone() is None:
        raise ValueError("The selected campus does not exist.")

    if conn.execute(
        "SELECT 1 FROM users WHERE username = ?", (username,)
    ).fetchone():
        raise ValueError("That username is already registered.")

    if conn.execute(
        "SELECT 1 FROM users WHERE lower(email) = lower(?)", (email,)
    ).fetchone():
        raise ValueError("That email address is already registered.")

    password_hash, salt = hash_password(temporary_password)
    cursor = conn.execute(
        """
        INSERT INTO users
            (username, full_name, password_hash, salt, role, campus_id,
             email, must_change_password)
        VALUES (?, ?, ?, ?, 'lecturer', ?, ?, 1)
        """,
        (username, full_name, password_hash, salt, campus_id, email)
    )
    conn.commit()
    return cursor.lastrowid
