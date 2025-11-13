"""Reindex tool for rebuilding the database."""

import asyncio
from pathlib import Path
from typing import Any, Dict
import time

from nisaba.tools.base_tool import BaseToolResponse
from nabu.mcp.tools.base import NabuTool
from nisaba import ToolMarkerMutating


class RebuildDatabaseTool(NabuTool, ToolMarkerMutating):
    """Re-index the codebase by rebuilding the KuzuDB database."""
    
    async def execute(self) -> BaseToolResponse:
        """
        Rebuild the entire KuzuDB database from scratch.
        
        This tool performs a complete re-indexing of the codebase by parsing
        all files and recreating the database. Use with caution as this is
        a time-consuming operation that will replace the existing database.
        
        :meta pitch: Full database rebuild. Slow but thorough. Only use when database is corrupted or after major structural changes.
        :meta when: Database corrupted, schema changes, or initial database creation
        :meta emoji: 🔄
        :meta tips: **When to Reindex:**
            - **Major codebase refactoring** - After moving/renaming many files or packages
            **Warning:** This is a SLOW operation (minutes for large codebases). Avoid using unnecessarily.
        :return: JSON object confirming successful database rebuild with frame statistics and counts
        """
        start_time = time.time()
        
        try:
            # Get active codebase configuration (context-aware)
            codebase_config = self.get_codebase_config()
            repo_path = codebase_config.repo_path
            db_path = codebase_config.db_path
            
            # Validate paths
            if not repo_path:
                return self.response_error("Repository path not configured")
            
            if not repo_path.exists():
                return self.response_error("Repository path not found: {repo_path}")
            
            if not db_path:
                return self.response_error("Database path not configured")
            
            self.logger().info(f"Re-indexing repository: {repo_path}")
            self.logger().info(f"Target database: {db_path}")
            
            # Run rebuild in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._rebuild_database)
            
            return self.response_success(result)
        
        except Exception as e:
            return self.response_exception(e, "Unexpected error during reindex.")
    
    def _rebuild_database(self) -> Dict[str, Any]:
        """Heavy lifting - rebuild database (runs in thread pool)."""
        import nabu.main
        from nabu.db import KuzuConnectionManager
        
        codebase_config = self.get_codebase_config()
        repo_str = str(codebase_config.repo_path.resolve())
        db_str = str(codebase_config.db_path)
        
        self.logger().info(f"Reindexing codebase: {repo_str}")
        self.logger().info(f"Target database: {db_str}")
        
        # Close existing manager
        if self.db_manager:
            self.db_manager.close()
            self.factory.db_manager = None
        
        # Remove existing database
        codebase_config = self.get_codebase_config()
        db_path = codebase_config.db_path
        
        if db_path.exists():
            if db_path.is_dir():
                raise RuntimeError(f"Found directory at db-path: {db_path}")
            db_path.unlink()
            db_path.with_suffix(".wal").unlink(missing_ok=True)
            db_path.with_suffix(".wal.shadow").unlink(missing_ok=True)
            self.logger().info("Removed existing database file")
        
        # Rebuild with extra ignore patterns from config
        nabu.main.parse_codebase(
            codebase_path=repo_str, 
            output_db=db_str,
            extra_ignore_patterns=self.factory.config.extra_ignore_patterns
        )
        
        # Re-initialize manager (update BOTH dict and backward-compat reference)
        manager = KuzuConnectionManager.get_instance(db_str)
        codebase_name = codebase_config.name

        # Update agent's db_managers dictionary
        self.factory.agent.db_managers[codebase_name] = manager

        # Update backward-compat reference
        self.factory.agent.db_manager = manager

        self.logger().info(f"Database manager re-initialized for '{codebase_name}' after rebuild")
        
        # Get stats (use longer timeout for large databases)
        result = self.db_manager.execute("MATCH (n:Frame) RETURN n.type as type, count(*) as count", timeout_ms=30000)
        stats = {}
        if result:
            df = result.get_as_df()
            for _, row in df.iterrows():
                stats[row['type']] = int(row['count'])

        # Reset auto-indexing status after manual rebuild
        if self.factory.auto_indexer:
            from nabu.mcp.indexing import IndexingStatus, IndexingState
            import time
            target_codebase = codebase_config.name
            self.factory.auto_indexer.status[target_codebase] = IndexingStatus(
                codebase=target_codebase,
                state=IndexingState.INDEXED,
                completed_at=time.time()
            )
            self.logger().info(f"Reset auto-indexing status for '{target_codebase}' to INDEXED")

        # Invalidate structural view TUI cache (force fresh tree on next operation)
        from nabu.mcp.tools.structural_view_tool import StructuralViewTool
        for tool in self.factory._iter_tools():
            if isinstance(tool, StructuralViewTool):
                tool._tui = None
                self.logger().info("Invalidated structural view TUI cache after rebuild")
                break

        return {
            "database_path": db_str,
            "frame_stats": stats,
            "total_frames": sum(stats.values())
        }
