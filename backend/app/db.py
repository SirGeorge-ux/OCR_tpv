from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "ocr_tpv.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row["name"] == column_name for row in rows)


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        if not _column_exists(conn, "image_uploads", "ocr_status"):
            conn.execute(
                "ALTER TABLE image_uploads ADD COLUMN ocr_status TEXT NOT NULL DEFAULT 'pending'"
            )

        if not _column_exists(conn, "image_uploads", "ocr_processed_at"):
            conn.execute(
                "ALTER TABLE image_uploads ADD COLUMN ocr_processed_at TEXT"
            )

        if not _column_exists(conn, "image_uploads", "ocr_error"):
            conn.execute(
                "ALTER TABLE image_uploads ADD COLUMN ocr_error TEXT"
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ocr_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER NOT NULL UNIQUE,
                raw_text TEXT,
                line_count INTEGER NOT NULL DEFAULT 0,
                avg_confidence REAL NOT NULL DEFAULT 0,
                parsed_name TEXT,
                parsed_phone TEXT,
                phone_candidates TEXT NOT NULL DEFAULT '[]',
                name_candidates TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(upload_id) REFERENCES image_uploads(id) ON DELETE CASCADE
            )
            """
        )

        conn.commit()