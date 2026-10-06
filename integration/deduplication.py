"""Deduplication and Idempotency store for WhatsApp webhook deliveries using Python standard sqlite3."""

import os
import time
import sqlite3
import asyncio
import logging
from typing import Optional, Set

logger = logging.getLogger(__name__)


class IdempotencyStore:
    """Persistent SQLite-backed deduplication store using standard library sqlite3."""

    def __init__(self, db_path: str = "/opt/data/router/dedup.db", ttl_seconds: int = 86400):
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._memory_cache: Set[str] = set()
        self._lock = asyncio.Lock()
        self._initialized = False

    def _sync_init_db(self) -> Set[str]:
        """Synchronous database initialization and cache preloading."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        cached_ids = set()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    sender_id TEXT,
                    created_at REAL
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_created_at ON processed_messages (created_at)"
            )
            conn.commit()

            # Preload recent messages within TTL
            cutoff = time.time() - self.ttl_seconds
            cursor.execute(
                "SELECT message_id FROM processed_messages WHERE created_at > ?", (cutoff,)
            )
            for row in cursor.fetchall():
                cached_ids.add(row[0])

        return cached_ids

    async def initialize(self) -> None:
        """Initialize the store asynchronously."""
        cached_ids = await asyncio.to_thread(self._sync_init_db)
        self._memory_cache.update(cached_ids)
        self._initialized = True
        logger.info(
            "IdempotencyStore initialized at %s with %d cached messages.",
            self.db_path,
            len(self._memory_cache),
        )

    def _sync_insert(self, message_id: str, sender_id: str, now: float) -> bool:
        """Synchronous insert. Returns True if duplicate (was already present), False if newly inserted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO processed_messages (message_id, sender_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (message_id, sender_id, now),
                )
                conn.commit()
                return False  # Successfully inserted -> Not a duplicate
            except sqlite3.IntegrityError:
                # Primary key collision -> Duplicate!
                return True

    async def is_duplicate_or_record(self, message_id: str, sender_id: Optional[str] = None) -> bool:
        """Check if message_id was already processed. If not, record it atomically.
        
        Returns:
            True if duplicate (already seen), False if newly recorded.
        """
        if not message_id:
            return False

        async with self._lock:
            # Fast in-memory check
            if message_id in self._memory_cache:
                return True

            now = time.time()
            try:
                is_dup = await asyncio.to_thread(
                    self._sync_insert, message_id, sender_id or "", now
                )
                self._memory_cache.add(message_id)
                return is_dup
            except Exception as e:
                logger.error("Error accessing deduplication database: %s", e)
                # Fail open to avoid dropping messages on transient errors
                return False

    def _sync_cleanup(self, cutoff: float) -> int:
        """Synchronous database cleanup."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM processed_messages WHERE created_at < ?", (cutoff,))
            conn.commit()
            deleted = cursor.rowcount

            # Re-read remaining active messages
            cursor.execute("SELECT message_id FROM processed_messages")
            remaining = {row[0] for row in cursor.fetchall()}

        return deleted, remaining

    async def cleanup_expired(self) -> int:
        """Remove message IDs older than TTL."""
        cutoff = time.time() - self.ttl_seconds
        try:
            deleted, remaining = await asyncio.to_thread(self._sync_cleanup, cutoff)
            async with self._lock:
                self._memory_cache = remaining
            logger.info("Cleaned up %d expired message IDs from IdempotencyStore.", deleted)
            return deleted
        except Exception as e:
            logger.error("Error during IdempotencyStore cleanup: %s", e)
            return 0
