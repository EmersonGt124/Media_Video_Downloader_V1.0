import sqlite3
import os
from typing import List, Tuple, Dict, Any, Optional

DB_DIR = os.path.join(os.path.dirname(__file__), "lib", "data")
DB_PATH = os.path.join(DB_DIR, "downloads.db")

class Database:
    @staticmethod
    def get_connection():
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls):
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    duration TEXT,
                    status TEXT DEFAULT 'Pendiente',
                    link TEXT UNIQUE,
                    thumbnail TEXT DEFAULT '',
                    uploader TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @classmethod
    def add_video(cls, title: str, duration: str, status: str, link: str, thumbnail: str = "", uploader: str = "") -> int:
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloads (title, duration, status, link, thumbnail, uploader)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(link) DO UPDATE SET
                    title = excluded.title,
                    duration = excluded.duration,
                    thumbnail = excluded.thumbnail,
                    uploader = excluded.uploader
            """, (title, duration, status, link, thumbnail, uploader))
            conn.commit()
            return cursor.lastrowid or 0

    @classmethod
    def add_batch(cls, videos: List[Dict[str, Any]]):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            for v in videos:
                cursor.execute("""
                    INSERT INTO downloads (title, duration, status, link, thumbnail, uploader)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(link) DO UPDATE SET
                        title = excluded.title,
                        duration = excluded.duration,
                        thumbnail = excluded.thumbnail,
                        uploader = excluded.uploader
                """, (
                    v.get('title', 'Video'),
                    v.get('duration_str') or str(v.get('duration', '00:00')),
                    v.get('status', 'Pendiente'),
                    v.get('url') or v.get('link', ''),
                    v.get('thumbnail', ''),
                    v.get('uploader', '')
                ))
            conn.commit()

    @classmethod
    def get_all(cls) -> List[Tuple[Any, ...]]:
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, duration, status, link, thumbnail, uploader FROM downloads ORDER BY id ASC")
            rows = cursor.fetchall()
            return [tuple(r) for r in rows]

    @classmethod
    def update_status(cls, link: str, new_status: str):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE downloads SET status = ? WHERE link = ?", (new_status, link))
            conn.commit()

    @classmethod
    def delete_by_id(cls, item_id: int):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads WHERE id = ?", (item_id,))
            conn.commit()

    @classmethod
    def delete_by_link(cls, link: str):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads WHERE link = ?", (link,))
            conn.commit()

    @classmethod
    def clear_all(cls):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads")
            conn.commit()

    @classmethod
    def get_pending(cls) -> List[Dict[str, Any]]:
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, duration, status, link, thumbnail, uploader FROM downloads WHERE status = 'Pendiente'")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

# Inicializar al importar
Database.init_db()
