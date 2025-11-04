"""
KuzuDB Connection Manager

Singleton manager ensuring one Database instance per database file.
Prevents corruption from multiple Database instances.
"""

import kuzu
import threading
import asyncio
from typing import Optional, Any
from contextlib import contextmanager
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class KuzuConnectionManager:
    """
    Singleton manager for KuzuDB Database instances.
    
    Ensures single Database instance per database file path.
    Provides connection lifecycle management with proper extension loading.
    
    Usage:
        # Initialize (once at startup)
        manager = KuzuConnectionManager.get_instance("/path/to/db.kuzu")
        
        # Execute query with ephemeral connection
        result = manager.execute("MATCH (n) RETURN count(n)")
        
        # Async execution
        result = await manager.execute_async("MATCH (n) RETURN n LIMIT 10")
        
        # Context manager for transaction
        with manager.connection() as conn:
            conn.execute("BEGIN TRANSACTION")
            conn.execute("CREATE ...")
            conn.execute("COMMIT")
    """
    
    _instances = {}  # Map: db_path -> manager instance
    _lock = threading.Lock()

    def __init__(self, db_path: str):
        """
        Initialize manager with Database instance.

        Args:
            db_path: Path to database file

        Note:
            Database is always opened in read-write mode to ensure
            all connections see committed changes immediately.
            Read-only behavior can be enforced at the application level.
        """
        self.db_path = str(Path(db_path).resolve())

        logger.info(f"Creating KuzuDB Database instance: {self.db_path}")
        self.db = kuzu.Database(self.db_path, read_only=False)
        logger.info(f"Database instance created successfully")
    
    @classmethod
    def get_instance(cls, db_path: str) -> 'KuzuConnectionManager':
        """
        Get or create manager instance for database path.

        Thread-safe singleton per database path.

        Args:
            db_path: Path to database file

        Returns:
            KuzuConnectionManager instance

        Note:
            Only one Database instance exists per path, shared by all
            readers and writers. This ensures all connections see
            committed changes immediately.
        """
        # Normalize path for consistent key
        normalized_path = str(Path(db_path).resolve())

        if normalized_path not in cls._instances:
            with cls._lock:
                # Double-check locking
                if normalized_path not in cls._instances:
                    cls._instances[normalized_path] = cls(db_path)

        return cls._instances[normalized_path]
    
    @contextmanager
    def connection(self, load_extensions: bool = True, timeout_ms: int = 5000):
        """
        Context manager for connection lifecycle.
        
        Creates connection, optionally loads extensions, yields, then closes.
        
        Args:
            load_extensions: Whether to load FTS extension
            timeout_ms: Query timeout in milliseconds (default: 5000ms = 5s)
            
        Yields:
            kuzu.Connection instance
            
        Example:
            with manager.connection() as conn:
                result = conn.execute("MATCH (n) RETURN n")
        """
        conn = kuzu.Connection(self.db)
        try:
            # Set query timeout
            conn.set_query_timeout(timeout_ms)
            
            if load_extensions:
                # Load bundled extensions (required per connection in Kuzu 0.11.3)
                # Note: Catch "already loaded" error to make this idempotent
                try:
                    conn.execute("LOAD FTS;")
                except RuntimeError as e:
                    if "already loaded" not in str(e):
                        raise
                    # Extension already loaded - this is fine, continue
                
                try:
                    conn.execute("LOAD VECTOR;")
                except RuntimeError as e:
                    if "already loaded" not in str(e):
                        raise
                    # Extension already loaded - this is fine, continue
            
            yield conn
        finally:
            conn.close()
    
    def execute(self, query: str, params: Optional[dict] = None, load_extensions: bool = True, timeout_ms: int = 5000) -> Any:
        """
        Execute query with ephemeral connection.
        
        Args:
            query: Cypher query string
            params: Optional query parameters
            load_extensions: Whether to load extensions
            timeout_ms: Query timeout in milliseconds (default: 5000ms = 5s)
            
        Returns:
            Query result
        """
        with self.connection(load_extensions=load_extensions, timeout_ms=timeout_ms) as conn:
            if params:
                return conn.execute(query, params)
            else:
                return conn.execute(query)
    
    async def execute_async(self, query: str, params: Optional[dict] = None, load_extensions: bool = True, timeout_ms: int = 5000) -> Any:
        """
        Async wrapper for query execution.
        
        Runs query in thread pool executor to avoid blocking event loop.
        
        Args:
            query: Cypher query string
            params: Optional query parameters
            load_extensions: Whether to load extensions
            timeout_ms: Query timeout in milliseconds (default: 5000ms = 5s)
            
        Returns:
            Query result
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.execute, 
            query, 
            params, 
            load_extensions,
            timeout_ms
        )
    
    def close(self):
        """
        Close Database instance and remove from registry.

        Should only be called during shutdown or before deleting database file.
        """
        if self.db:
            logger.info(f"Closing Database instance: {self.db_path}")
            self.db.close()
            self.db = None

            # Remove from registry
            if self.db_path in self._instances:
                del self._instances[self.db_path]
    
    @classmethod
    def close_all(cls):
        """Close all managed Database instances."""
        with cls._lock:
            for manager in list(cls._instances.values()):
                manager.close()
            cls._instances.clear()
