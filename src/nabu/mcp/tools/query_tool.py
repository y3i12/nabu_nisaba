"""Query tool for executing Cypher queries."""

from typing import Any, Dict, Optional
import time

from nabu.mcp.tools.base import NabuTool
from nisaba.utils.response import ErrorSeverity


class QueryRelationshipsTool(NabuTool):
    """Execute Cypher queries against the KuzuDB graph database."""
    
    async def execute(self, cypher_query: str, timeout_ms: Optional[int] = None) -> Dict[str, Any]:
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
                return self._error_response(
                    RuntimeError("Database manager not initialized"),
                    start_time,
                    severity=ErrorSeverity.FATAL,
                    recovery_hint=(
                        "Database manager not initialized. Check --db-path argument and ensure database exists. "
                        "Restart MCP server if needed. If database file is missing, use reindex() tool to rebuild it."
                    ),
                    context={"db_path": str(self.get_codebase_config().db_path) if self.get_codebase_config() else "not set"}
                )
            
            # Validate query not empty
            if not cypher_query or not cypher_query.strip():
                return self._error_response(
                    ValueError("Empty Cypher query provided"),
                    start_time,
                    recovery_hint=(
                        "Provide a non-empty Cypher query string. "
                        "See memory 'kuzu_cypher' for query examples and patterns."
                    )
                )
            
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
            
            return self._success_response(data, start_time)
        
        except RuntimeError as e:
            error_str = str(e)
            
            # Detect timeout errors
            if "timeout" in error_str.lower() or "interrupted" in error_str.lower():
                return self._error_response(
                    e,
                    start_time,
                    severity=ErrorSeverity.ERROR,
                    recovery_hint=(
                        f"Query exceeded timeout ({actual_timeout}ms = {actual_timeout/1000:.1f}s). Consider: "
                        "(1) Adding LIMIT clause to reduce result size, "
                        "(2) Bounding path traversals with depth limits (e.g., [:Edge*1..5] instead of [:Edge*]), "
                        "(3) Adding WHERE filters early to reduce search space, "
                        "(4) Using specific edge types (e.g., [:Edge {type: 'CONTAINS'}]) instead of all edges."
                    ),
                    context={"query": cypher_query[:500], "timeout_ms": actual_timeout}
                )
            
            # Detect Cypher syntax errors
            if "Parser exception" in error_str or "Invalid input" in error_str:
                return self._error_response(
                    e,
                    start_time,
                    recovery_hint=(
                        "Invalid Cypher syntax detected. Common issues: "
                        "(1) Missing or mismatched quotes, "
                        "(2) Invalid MATCH pattern (use parentheses for nodes: (n:Frame)), "
                        "(3) Wrong property access syntax (use n.property not n->property), "
                        "(4) Unsupported regex operators (use CONTAINS instead of =~). "
                        "See memory 'kuzu_cypher' for correct syntax examples."
                    ),
                    context={"query": cypher_query[:500], "error_location": error_str}
                )
            
            # Other runtime errors
            return self._error_response(
                e,
                start_time,
                recovery_hint=(
                    "Query execution failed. Verify: "
                    "(1) Database is initialized (try show_status() tool), "
                    "(2) Query references existing node/edge types (Frame, CALLS, CONTAINS, etc.), "
                    "(3) Property names are correct. "
                    "See memory 'kuzu_cypher' for schema information."
                ),
                context={"query": cypher_query[:500]}
            )
        
        except Exception as e:
            self.logger.error(f"Query failed: {cypher_query[:100]}...", exc_info=True)
            return self._error_response(
                e,
                start_time,
                recovery_hint=(
                    "Unexpected error during query execution. "
                    "Check that query doesn't contain SQL syntax (this is Cypher, not SQL). "
                    "See memory 'kuzu_cypher' for Cypher query examples."
                ),
                context={"query": cypher_query[:500], "error_type": type(e).__name__}
            )
