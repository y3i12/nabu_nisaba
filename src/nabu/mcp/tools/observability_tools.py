"""Observability tools for monitoring database health."""

from typing import Any, Dict, Optional
import time

from nabu.mcp.tools.base import NabuTool
from nisaba import ToolMarkerOptional, ToolMarkerDevOnly
from nisaba.utils.response import ErrorSeverity


class ShowStatusTool(NabuTool):
    """Unified observability: codebase health + database diagnostics."""
    
    async def execute(
        self,
        codebase: Optional[str] = None,
        detail_level: str = "summary"
    ) -> Dict[str, Any]:
        """
        Unified status and diagnostics for codebases and database.
        
        Progressive disclosure based on detail level:
        - summary: Frame counts and health status only (default)
        - detailed: Add database connections and codebase configuration
        - debug: Full diagnostics including connection pool internals
        
        :param codebase: Optional specific codebase to show (defaults to all)
        :param detail_level: Level of detail - "summary", "detailed", or "debug"
        :return: Status information with frame counts and optional database diagnostics
        :meta pitch: View codebase health and database status
        :meta when: Check system health, frame counts, or debug database issues
        """
        start_time = time.time()
        
        # Validate detail_level
        valid_levels = ["summary", "detailed", "debug"]
        if detail_level not in valid_levels:
            return self._error_response(
                ValueError(f"Invalid detail_level: {detail_level}. Must be one of {valid_levels}"),
                start_time,
                recovery_hint=f"Use detail_level in {valid_levels}"
            )
        
        target_codebases = [codebase] if codebase else list(self.config.codebases.keys())
        
        # Validate if specific codebase requested
        if codebase and codebase not in self.config.codebases:
            available = list(self.config.codebases.keys())
            return self._error_response(
                ValueError(f"Unknown codebase: {codebase}"),
                start_time,
                recovery_hint=f"Available codebases: {', '.join(available)}"
            )
        
        # Gather codebase status
        codebases_info = []
        for name in target_codebases:
            cb_config = self.config.codebases[name]
            db_manager = self.factory.db_managers.get(name)
            
            codebase_data = {
                "name": name,
                "is_active": name == self.config.active_codebase,
                "status": "not_initialized",
                "frame_count": None
            }

            if db_manager and db_manager.db:
                try:
                    result = db_manager.execute("MATCH (f:Frame) RETURN count(f) as count")
                    rows = list(result)
                    codebase_data["frame_count"] = rows[0][0] if rows else 0
                    codebase_data["status"] = "healthy"
                except Exception as e:
                    codebase_data["status"] = f"error: {e}"

            # Override status with indexing state if auto-indexer is active
            if self.factory.auto_indexer:
                from nabu.mcp.indexing import IndexingState
                indexing_status = self.factory.auto_indexer.get_status(name)
                if indexing_status.state != IndexingState.INDEXED:
                    codebase_data["status"] = indexing_status.state.value

                    # Add indexing metadata for detailed/debug levels
                    if detail_level in ["detailed", "debug"] and indexing_status.state in (
                        IndexingState.INDEXING, IndexingState.ERROR
                    ):
                        codebase_data["indexing_metadata"] = {
                            "state": indexing_status.state.value,
                            "started_at": indexing_status.started_at,
                            "completed_at": indexing_status.completed_at,
                            "error_message": indexing_status.error_message
                        }

            # Add detailed info if requested
            if detail_level in ["detailed", "debug"]:
                codebase_data.update({
                    "role": cb_config.role,
                    "db_path": str(cb_config.db_path),
                    "watch_enabled": cb_config.watch_enabled
                })

                # Add confidence distribution for detailed/debug levels
                if db_manager and db_manager.db:
                    try:
                        # Query edge confidence distribution
                        conf_query = """
                        MATCH ()-[e:Edge]->()
                        RETURN
                            e.confidence_tier as tier,
                            count(e) as count
                        """
                        conf_result = db_manager.execute(conf_query)
                        conf_rows = list(conf_result)

                        confidence_dist = {
                            "HIGH": 0,
                            "MEDIUM": 0,
                            "LOW": 0,
                            "SPECULATIVE": 0
                        }

                        for row in conf_rows:
                            tier = row[0]
                            count = row[1]
                            if tier in confidence_dist:
                                confidence_dist[tier] = count

                        codebase_data["confidence_distribution"] = confidence_dist
                    except Exception as e:
                        self.logger.warning(f"Failed to get confidence distribution for {name}: {e}")

            codebases_info.append(codebase_data)
        
        # Build response
        response_data = {
            "codebases": codebases_info,
            "active_codebase": self.config.active_codebase
        }
        
        # Add database diagnostics for detailed/debug levels
        if detail_level in ["detailed", "debug"]:
            try:
                from nabu.db import KuzuConnectionManager
                
                db_info = {
                    "active_connections": len(KuzuConnectionManager._instances),
                    "updater_connected": self.incremental_updater is not None
                }
                
                # Debug level: add full diagnostics
                if detail_level == "debug":
                    codebase_config = self.get_codebase_config(codebase)
                    db_info.update({
                        "database_path": str(codebase_config.db_path),
                        "codebase_name": codebase_config.name,
                        "dev_mode": self.config.dev_mode
                    })
                
                response_data["database"] = db_info
                
            except Exception as e:
                return self._error_response(
                    e,
                    start_time,
                    severity=ErrorSeverity.ERROR,
                    recovery_hint=(
                        "Failed to retrieve database diagnostics. "
                        "Codebase status available but database stats unavailable. "
                        "Check database connection or consider rebuild_database()."
                    ),
                    context={"detail_level": detail_level}
                )
        
        return self._success_response(response_data, start_time)
