"""
Database module for storing and retrieving API key data.
"""

import sqlite3
from typing import Optional, List, Tuple
from datetime import datetime


class Database:
    """SQLite database handler for API key storage."""

    def __init__(self, db_path: str = "google_places.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'unknown',
                source_url TEXT,
                file_path TEXT,
                language TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                error_message TEXT,
                quota_remaining INTEGER
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT,
                language TEXT,
                page INTEGER,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                keys_found INTEGER DEFAULT 0
            )
        """)
        
        self.conn.commit()

    def add_key(
        self,
        api_key: str,
        source_url: str = None,
        file_path: str = None,
        language: str = None
    ) -> bool:
        """
        Add a new API key to the database.
        
        Returns:
            True if key was added, False if it already exists.
        """
        try:
            self.cursor.execute("""
                INSERT INTO api_keys (api_key, source_url, file_path, language)
                VALUES (?, ?, ?, ?)
            """, (api_key, source_url, file_path, language))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Key already exists
            return False

    def update_key_status(
        self,
        api_key: str,
        status: str,
        error_message: str = None,
        quota_remaining: int = None
    ):
        """Update the status of an API key after validation."""
        self.cursor.execute("""
            UPDATE api_keys
            SET status = ?, last_checked = ?, error_message = ?, quota_remaining = ?
            WHERE api_key = ?
        """, (status, datetime.now(), error_message, quota_remaining, api_key))
        self.conn.commit()

    def get_unchecked_keys(self) -> List[Tuple]:
        """Get all keys that haven't been validated yet."""
        self.cursor.execute("""
            SELECT id, api_key, source_url FROM api_keys
            WHERE status = 'unknown'
        """)
        return self.cursor.fetchall()

    def get_all_keys(self) -> List[Tuple]:
        """Get all keys from the database."""
        self.cursor.execute("""
            SELECT id, api_key, status, source_url, file_path, language,
                   discovered_at, last_checked, error_message
            FROM api_keys
            ORDER BY discovered_at DESC
        """)
        return self.cursor.fetchall()

    def get_valid_keys(self) -> List[Tuple]:
        """Get all valid/working keys."""
        self.cursor.execute("""
            SELECT id, api_key, source_url FROM api_keys
            WHERE status = 'valid'
        """)
        return self.cursor.fetchall()

    def get_key_count(self) -> dict:
        """Get count of keys by status."""
        self.cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM api_keys
            GROUP BY status
        """)
        results = self.cursor.fetchall()
        return {row[0]: row[1] for row in results}

    def add_scan_record(
        self,
        keyword: str,
        language: str,
        page: int,
        keys_found: int
    ):
        """Record a scan attempt."""
        self.cursor.execute("""
            INSERT INTO scan_history (keyword, language, page, keys_found)
            VALUES (?, ?, ?, ?)
        """, (keyword, language, page, keys_found))
        self.conn.commit()

    def get_last_scan_page(self, keyword: str, language: str) -> Optional[int]:
        """Get the last scanned page for a keyword/language combination."""
        self.cursor.execute("""
            SELECT MAX(page) FROM scan_history
            WHERE keyword = ? AND language = ?
        """, (keyword, language))
        result = self.cursor.fetchone()
        return result[0] if result[0] is not None else None

    def close(self):
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
