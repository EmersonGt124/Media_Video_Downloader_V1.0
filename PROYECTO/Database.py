import sqlite3
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

def _resolve_db_path() -> Tuple[str, str]:
    if getattr(sys, 'frozen', False):
        if sys.platform.startswith("win"):
            base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        elif sys.platform == "darwin":
            base = str(Path.home() / "Library" / "Application Support")
        else:
            base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        db_dir = os.path.join(base, "MediaDownloaderPro")
    else:
        db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "data")
    os.makedirs(db_dir, exist_ok=True)
    return db_dir, os.path.join(db_dir, "downloads.db")

DB_DIR, DB_PATH = _resolve_db_path()

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
                    filepath TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            try:
                cursor.execute("ALTER TABLE downloads ADD COLUMN filepath TEXT DEFAULT ''")
            except Exception:
                pass
            conn.commit()

    @classmethod
    def add_video(
        cls,
        title: str,
        duration: str,
        status: str,
        link: str,
        thumbnail: str = "",
        uploader: str = "",
        filepath: str = ""
    ) -> int:
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO downloads (title, duration, status, link, thumbnail, uploader, filepath)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(link) DO UPDATE SET
                    title = excluded.title,
                    duration = excluded.duration,
                    thumbnail = excluded.thumbnail,
                    uploader = excluded.uploader,
                    filepath = CASE WHEN excluded.filepath != '' THEN excluded.filepath ELSE downloads.filepath END
            """, (title, duration, status, link, thumbnail, uploader, filepath))
            conn.commit()
            return cursor.lastrowid or 0

    @classmethod
    def add_batch(cls, videos: List[Dict[str, Any]]):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            for v in videos:
                cursor.execute("""
                    INSERT INTO downloads (title, duration, status, link, thumbnail, uploader, filepath)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
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
                    v.get('uploader', ''),
                    v.get('filepath', '')
                ))
            conn.commit()

    @classmethod
    def get_all(cls) -> List[Tuple[Any, ...]]:
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, duration, status, link, thumbnail, uploader, filepath FROM downloads ORDER BY id ASC")
            rows = cursor.fetchall()
            return [tuple(r) for r in rows]

    @classmethod
    def get_filtered(cls, status: str = "Todos", search_query: str = "") -> List[Tuple[Any, ...]]:
        """Obtiene registros filtrados por estado y búsqueda por título o canal."""
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, title, duration, status, link, thumbnail, uploader, filepath FROM downloads WHERE 1=1"
            params = []

            if status and status != "Todos":
                query += " AND status = ?"
                params.append(status)

            if search_query and search_query.strip():
                query += " AND (title LIKE ? OR uploader LIKE ?)"
                like_term = f"%{search_query.strip()}%"
                params.extend([like_term, like_term])

            query += " ORDER BY id ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [tuple(r) for r in rows]

    @classmethod
    def get_item_by_id(cls, item_id: int) -> Optional[Dict[str, Any]]:
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, duration, status, link, thumbnail, uploader, filepath FROM downloads WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @classmethod
    def update_status(cls, link: str, new_status: str, filepath: str = ""):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            if filepath:
                cursor.execute("UPDATE downloads SET status = ?, filepath = ? WHERE link = ?", (new_status, filepath, link))
            else:
                cursor.execute("UPDATE downloads SET status = ? WHERE link = ?", (new_status, link))
            conn.commit()

    @classmethod
    def reset_status_by_id(cls, item_id: int, new_status: str = "Pendiente"):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE downloads SET status = ? WHERE id = ?", (new_status, item_id))
            conn.commit()

    @classmethod
    def delete_by_id(cls, item_id: int):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads WHERE id = ?", (item_id,))
            conn.commit()

    @classmethod
    def delete_batch_ids(cls, item_ids: List[int]):
        if not item_ids:
            return
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(item_ids))
            cursor.execute(f"DELETE FROM downloads WHERE id IN ({placeholders})", item_ids)
            conn.commit()

    @classmethod
    def delete_by_link(cls, link: str):
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads WHERE link = ?", (link,))
            conn.commit()

    @classmethod
    def clear_completed(cls):
        """Elimina solo los elementos con estado 'Terminado'."""
        cls.init_db()
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM downloads WHERE status = 'Terminado'")
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
            cursor.execute("SELECT id, title, duration, status, link, thumbnail, uploader, filepath FROM downloads WHERE status = 'Pendiente'")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

Database.init_db()
