"""
Kindred v1.7.0 - Database Backup Scheduler
Automatic SQLite backups with rotation.
"""

import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from app.config import DB_PATH, BACKUP_DIR, BACKUP_KEEP_COUNT, BACKUP_INTERVAL_HOURS
from app.logging_config import get_logger

logger = get_logger("backup")

_scheduler_thread = None
_running = False


def create_backup() -> str:
    """Create a timestamped backup of the database. Returns backup filename."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"kindred_backup_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_name
    import sqlite3
    src = sqlite3.connect(str(DB_PATH))
    dst = sqlite3.connect(str(backup_path))
    src.backup(dst)
    dst.close()
    src.close()
    logger.info(f"Database backup created: {backup_name}")
    _rotate_backups()
    return backup_name


def _rotate_backups():
    """Delete oldest backups beyond BACKUP_KEEP_COUNT."""
    backups = sorted(BACKUP_DIR.glob("kindred_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[BACKUP_KEEP_COUNT:]:
        old.unlink()
        logger.info(f"Rotated old backup: {old.name}")


def list_backups() -> list[dict]:
    """List all available backups."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = sorted(BACKUP_DIR.glob("kindred_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "filename": b.name,
            "size_mb": round(b.stat().st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(b.stat().st_mtime).isoformat(),
        }
        for b in backups
    ]


def restore_backup(filename: str) -> bool:
    """Restore database from a backup file."""
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists() or not filename.startswith("kindred_backup_"):
        return False
    # Create a pre-restore backup first
    create_backup()
    shutil.copy2(str(backup_path), str(DB_PATH))
    logger.info(f"Database restored from: {filename}")
    return True


def _scheduler_loop():
    global _running
    interval = BACKUP_INTERVAL_HOURS * 3600
    while _running:
        try:
            create_backup()
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
        elapsed = 0
        while _running and elapsed < interval:
            time.sleep(10)
            elapsed += 10


def start_backup_scheduler():
    """Start the background backup scheduler."""
    global _scheduler_thread, _running
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _running = True
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()
    logger.info(f"Backup scheduler started (every {BACKUP_INTERVAL_HOURS}h, keeping {BACKUP_KEEP_COUNT})")


def stop_backup_scheduler():
    global _running
    _running = False
