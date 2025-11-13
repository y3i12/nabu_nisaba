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
        
        This tool allows you to run read and write Cypher queries to explore
        the codebase structure, relationships, and metadata stored in the KuzuDB
        graph database.
        
        :meta pitch: Your main tool for structural analysis. Use AFTER fts_query to dig deeper into relationships.
        :meta when: After discovery phase, when you need precise relationship queries
        :meta emoji: 🏗️
        :meta tips: **Query Strategy:**
            - **Discovery → Structure → Details** - Start broad with `fts_query`, narrow with Cypher `query`, verify with `content` property
            - **Always use LIMIT** - Nabu databases can be large; limit results to avoid overwhelming output
            - **Filter by frame type early** - Specify `{type: 'CLASS'}` or `{type: 'CALLABLE'}` to narrow searches
            - **Check confidence scores** - For CALLS edges, verify `confidence` field to assess reliability
            - **JSON metadata** - Edge metadata is JSON type; use `json_extract(e.metadata, 'key')` not `CONTAINS`
        :meta examples: **Introspection Queries:**

            Get complete schema information:
            ```cypher
            CALL SHOW_TABLES() RETURN *
            ```

            Count all nodes and edges:
            ```cypher
            MATCH (f:Frame) WITH count(f) as frames
            MATCH ()-[e:Edge]->() WITH frames, count(e) as edges
            RETURN frames, edges
            ```

            Find all property names:
            ```cypher
            CALL TABLE_INFO('Frame') RETURN name, type
            ```
        :meta patterns: **Field Usage Queries (USES Edges):**

            USES edges track which methods access class fields. Each edge contains metadata about the field access:
            - `field_name`: The name of the field being accessed
            - `access_type`: "read", "write", or "both"
            - `line`: Line number where the access occurs

            Find all methods using a specific field:
            ```cypher
            MATCH (m:Frame {type: 'CALLABLE'})-[u:Edge {type: 'USES'}]->(c:Frame {type: 'CLASS'})
            WHERE json_extract(u.metadata, 'field_name') = '"my_field"'
            RETURN m.qualified_name, 
                   json_extract(u.metadata, 'field_name') as field,
                   json_extract(u.metadata, 'access_type') as access
            ```

            Find all fields used by a method:
            ```cypher
            MATCH (m:Frame {qualified_name: 'MyClass.my_method'})-[u:Edge {type: 'USES'}]->(c:Frame)
            RETURN json_extract(u.metadata, 'field_name') as field,
                   json_extract(u.metadata, 'access_type') as access,
                   json_extract(u.metadata, 'line') as line
            ```

            Find write-only fields (potential dead code):
            ```cypher
            MATCH (c:Frame {type: 'CLASS'})<-[u:Edge {type: 'USES'}]-()
            WHERE json_extract(u.metadata, 'access_type') = '"write"'
            AND NOT EXISTS {
              MATCH (c)<-[r:Edge {type: 'USES'}]-()
              WHERE json_extract(r.metadata, 'access_type') IN ['"read"', '"both"']
            }
            RETURN c.qualified_name, 
                   json_extract(u.metadata, 'field_name') as unused_field
            ```
        :param cypher_query: The Cypher query string to execute against the database
        :param timeout_ms: Query timeout in milliseconds (optional, defaults to 5000ms if not specified)
        :return: JSON object containing query results with rows, columns, and execution metrics
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
