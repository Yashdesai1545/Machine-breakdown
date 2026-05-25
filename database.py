"""
database.py - MySQL database for JSW Machine Breakdown Prediction System
Machines are seeded directly from machine_data_new_502.csv (502 rows, 60 unique machines)
"""

import os
import pandas as pd
import pymysql
import pymysql.cursors

# ── MySQL Connection Config ─────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("MYSQL_HOST",     "localhost"),
    "port":     int(os.environ.get("MYSQL_PORT", 3306)),
    "user":     os.environ.get("MYSQL_USER",     "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "root1527"),          # ← set your password
    "database": os.environ.get("MYSQL_DB",       "jsw_breakdown"),
    "charset":  "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}

DATASET_PATH = "dataset/machine_data_new_502.csv"

# Type → department mapping
TYPE_DEPT = {
    "H": "Heavy Industrial",
    "M": "Medium Industrial",
    "L": "Light Industrial",
}

# Machine name → JSW ID prefix mapping (auto-generate from name)
def _machine_id_from_name(name: str, idx: int) -> str:
    """Generate JSW-XXX-NN style IDs from machine names."""
    parts = name.split("-")
    suffix = parts[-1].strip().zfill(2) if len(parts) > 1 else str(idx + 1).zfill(2)
    # Build 3-letter prefix from first letters of words
    words = parts[0].strip().split()
    prefix = "".join(w[0].upper() for w in words)[:3].ljust(3, "X")
    return f"JSW-{prefix}-{suffix}"


def get_connection():
    """Return a new MySQL connection."""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except pymysql.err.OperationalError as e:
        raise ConnectionError(
            f"Cannot connect to MySQL: {e}\n"
            f"  Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}\n"
            f"  User: {DB_CONFIG['user']}  DB: {DB_CONFIG['database']}\n"
            "  Set MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD env vars or edit DB_CONFIG in database.py"
        )


def _create_database_if_missing():
    """Create the jsw_breakdown database if it doesn't exist yet."""
    cfg = {k: v for k, v in DB_CONFIG.items()
           if k not in ("database", "cursorclass", "autocommit")}
    cfg["cursorclass"] = pymysql.cursors.DictCursor
    conn = pymysql.connect(**cfg)
    with conn.cursor() as c:
        c.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
                  f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn.commit()
    conn.close()


def init_db():
    _create_database_if_missing()
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS machines (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            machine_id       VARCHAR(50)  NOT NULL UNIQUE,
            machine_name     VARCHAR(100) NOT NULL,
            machine_type     VARCHAR(10),
            department       VARCHAR(100),
            installation_date VARCHAR(20),
            last_maintenance VARCHAR(20),
            status           VARCHAR(30) DEFAULT 'Operational',
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id                   INT AUTO_INCREMENT PRIMARY KEY,
            machine_id           VARCHAR(50)  NOT NULL,
            timestamp            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            air_temperature      FLOAT,
            process_temperature  FLOAT,
            rotational_speed     FLOAT,
            torque               FLOAT,
            tool_wear            FLOAT,
            vibration            FLOAT,
            risk_score           FLOAT,
            risk_level           VARCHAR(20),
            predicted_breakdown  TINYINT DEFAULT 0,
            recommendation       TEXT,
            INDEX idx_machine_id (machine_id),
            INDEX idx_timestamp  (timestamp)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            machine_id   VARCHAR(50)  NOT NULL,
            alert_type   VARCHAR(50),
            severity     VARCHAR(20),
            message      TEXT,
            timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            acknowledged TINYINT DEFAULT 0,
            INDEX idx_ack (acknowledged)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            username      VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id               INT AUTO_INCREMENT PRIMARY KEY,
            machine_id       VARCHAR(50) NOT NULL,
            maintenance_type VARCHAR(50),
            performed_by     VARCHAR(100),
            date_performed   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes            TEXT,
            cost             FLOAT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # ── Seed all machines from CSV dataset ───────────────────────────────────
    c.execute("SELECT COUNT(*) as cnt FROM machines")
    if c.fetchone()["cnt"] == 0:
        _seed_machines_from_csv(c)

    conn.commit()
    conn.close()
    print("MySQL database initialized successfully.")


def _seed_machines_from_csv(cursor):
    """Load all 60 unique machines from CSV and insert into machines table."""
    try:
        df = pd.read_csv(DATASET_PATH)
        unique = (
            df[["Machine Name", "Machine ID", "Type"]]
            .drop_duplicates("Machine Name")
            .sort_values("Machine Name")
            .reset_index(drop=True)
        )

        rows = []
        for i, row in unique.iterrows():
            name      = str(row["Machine Name"])
            prod_id   = str(row["Machine ID"])
            mtype     = str(row["Type"])
            dept      = TYPE_DEPT.get(mtype, "General")

            # Build a consistent JSW-XXX-NN ID from the machine name
            parts     = name.rsplit("-", 1)
            num_part  = parts[1].strip().zfill(2) if len(parts) == 2 else str(i + 1).zfill(2)
            words     = parts[0].strip().split()
            prefix    = "".join(w[0].upper() for w in words)[:3].ljust(3, "X")
            machine_id = f"JSW-{prefix}-{num_part}"

            rows.append((machine_id, name, mtype, dept))

        cursor.executemany(
            "INSERT IGNORE INTO machines (machine_id, machine_name, machine_type, department) "
            "VALUES (%s, %s, %s, %s)",
            rows
        )
        print(f"  Seeded {len(rows)} machines from CSV into MySQL.")
    except Exception as e:
        print(f"  Warning: Could not seed machines from CSV: {e}")
        print("  Falling back to hardcoded machine list.")
        _seed_machines_hardcoded(cursor)


def _seed_machines_hardcoded(cursor):
    """Fallback: Load all machines from CSV instead of hardcoded list."""
    try:
        df = pd.read_csv(DATASET_PATH)
        unique = (
            df[["Machine Name", "Machine ID", "Type"]]
            .drop_duplicates("Machine Name")
            .sort_values("Machine Name")
            .reset_index(drop=True)
        )
        rows = []
        for i, row in unique.iterrows():
            name    = str(row["Machine Name"])
            prod_id = str(row["Machine ID"])
            mtype   = str(row["Type"])
            dept    = TYPE_DEPT.get(mtype, "General")
            parts   = name.rsplit("-", 1)
            num_part = parts[1].strip().zfill(2) if len(parts) == 2 else str(i + 1).zfill(2)
            words   = parts[0].strip().split()
            prefix  = "".join(w[0].upper() for w in words)[:3].ljust(3, "X")
            machine_id = f"JSW-{prefix}-{num_part}"
            rows.append((machine_id, name, mtype, dept))
        cursor.executemany(
            "INSERT IGNORE INTO machines (machine_id,machine_name,machine_type,department) VALUES (%s,%s,%s,%s)",
            rows
        )
    except Exception as e:
        print(f"  Error in hardcoded fallback: {e}")
        raise
    print(f"  Seeded {len(rows)} machines (hardcoded fallback).")


if __name__ == "__main__":
    init_db()
