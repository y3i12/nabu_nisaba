"""Query tool for executing Cypher queries."""

from typing import Any, Dict, Optional
import time

from nisaba.tools.base_tool import BaseToolResponse
from nabu.mcp.tools.base import NabuTool


class QueryRelationshipsTool(NabuTool):
    """Execute Cypher queries against the KuzuDB graph database."""
    
    async def execute(self, cypher_query: str, timeout_ms: Optional[int] = None) -> BaseToolResponse:
        """
        Execute Cypher queries against the KuzuDB graph database.

        Allows read and write Cypher queries to explore codebase structure, relationships,
        and metadata. Use LIMIT clauses to avoid overwhelming output on large codebases.

        Query tips:
        - Use LIMIT to constrain result size
        - Filter by frame type early: `WHERE f.type = 'CLASS'`
        - Check confidence on CALLS edges: `WHERE e.confidence >= 0.8`
        - JSON metadata requires json_extract(): `json_extract(e.metadata, 'key')`

        :param cypher_query: Cypher query string to execute
        :param timeout_ms: Query timeout in milliseconds (default 5000)
        :return: Query results with rows, columns, and execution metrics
        """
        start_time = time.time()
        
        # Use default timeout if not specified
        actual_timeout = timeout_ms if timeout_ms is not None else 5000
        
        try:
            # Check indexing status before proceeding
            indexing_check = self._check_indexing_status()
            if indexing_check:
                return indexing_check

            # Validate database manager
            if self.db_manager is None:
                return self.response_error("Database manager not initialized")
            
            # Validate query not empty
            if not cypher_query or not cypher_query.strip():
                return self.response_error("Empty Cypher query provided")
            
            # Execute query with timeout
            result = self.db_manager.execute(cypher_query, load_extensions=True, timeout_ms=actual_timeout)
            
            # Convert to DataFrame
            if result and hasattr(result, 'get_as_df'):
                df = result.get_as_df()
                data = {
                    "rows": df.to_dict('records') if not df.empty else [],
                    "row_count": len(df),
                    "columns": list(df.columns) if not df.empty else []
                }
            else:
                data = {
                    "rows": [],
                    "row_count": 0,
                    "columns": []
                }
            
            return self.response_success(data)
        
        except Exception as e:
            return self.response_exception(e, f"Unexpected error during query execution")
