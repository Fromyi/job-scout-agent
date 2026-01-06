"""SQLite database for tracking seen jobs."""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Set
from contextlib import contextmanager

from config import config
from scrapers import Job


class JobDatabase:
    """Track seen jobs to avoid duplicates."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_jobs (
                    job_id TEXT PRIMARY KEY,
                    title TEXT,
                    company TEXT,
                    url TEXT,
                    source TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notified BOOLEAN DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_first_seen ON seen_jobs(first_seen)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_seen_job_ids(self) -> Set[str]:
        """Get all seen job IDs."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT job_id FROM seen_jobs")
            return {row["job_id"] for row in cursor.fetchall()}

    def filter_new_jobs(self, jobs: List[Job]) -> List[Job]:
        """Filter out jobs we've already seen."""
        seen_ids = self.get_seen_job_ids()
        return [job for job in jobs if job.id not in seen_ids]

    def mark_jobs_seen(self, jobs: List[Job], notified: bool = True):
        """Mark jobs as seen in the database."""
        with self._get_connection() as conn:
            for job in jobs:
                conn.execute("""
                    INSERT OR REPLACE INTO seen_jobs
                    (job_id, title, company, url, source, notified)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (job.id, job.title, job.company, job.url, job.source, notified))
            conn.commit()

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
            notified = conn.execute("SELECT COUNT(*) FROM seen_jobs WHERE notified = 1").fetchone()[0]
            today = conn.execute(
                "SELECT COUNT(*) FROM seen_jobs WHERE date(first_seen) = date('now')"
            ).fetchone()[0]
            by_source = {}
            for row in conn.execute("SELECT source, COUNT(*) as count FROM seen_jobs GROUP BY source"):
                by_source[row["source"]] = row["count"]

            return {
                "total_seen": total,
                "total_notified": notified,
                "found_today": today,
                "by_source": by_source,
            }

    def cleanup_old_jobs(self, days: int = 30):
        """Remove jobs older than X days."""
        with self._get_connection() as conn:
            cutoff = datetime.now() - timedelta(days=days)
            conn.execute("DELETE FROM seen_jobs WHERE first_seen < ?", (cutoff,))
            conn.commit()


if __name__ == "__main__":
    # Test database
    db = JobDatabase("test_jobs.db")
    print("Database initialized")
    print("Stats:", db.get_stats())
