"""Base class for nabu MCP tools."""

from abc import abstractmethod
from typing import Any, Dict, TYPE_CHECKING, get_type_hints, Optional, get_origin, get_args, List, Union
from pathlib import Path
import logging
import time
import inspect
import re
from contextvars import ContextVar

# Import from framework
from nisaba import BaseTool
from nisaba.utils.response import ResponseBuilder, ErrorSeverity

from nabu.mcp.utils.regex_helpers import extract_keywords_from_regex

# Docstring parsing (optional dependency)
try:
    from docstring_parser import parse as parse_docstring
    from docstring_parser.common import Docstring
    DOCSTRING_PARSER_AVAILABLE = True
except ImportError:
    DOCSTRING_PARSER_AVAILABLE = False
    Docstring = None  # type: ignore

if TYPE_CHECKING:
    from nabu.mcp.factory import NabuMCPFactory

logger = logging.getLogger(__name__)

# Thread-safe context for current codebase during tool execution
_current_codebase_context: ContextVar[Optional[str]] = ContextVar('current_codebase', default=None)


def detect_regex_pattern(target: str) -> bool:
    """
    Detect if target string looks like a regex pattern.

    Uses heuristics to identify common regex metacharacters and patterns.

    Args:
        target: String to analyze

    Returns:
        True if target appears to be a regex pattern, False otherwise

    Examples:
        >>> detect_regex_pattern("MyClass")
        False
        >>> detect_regex_pattern(".*Tool$")
        True
        >>> detect_regex_pattern("(Foo|Bar|Baz)")
        True
    """
    regex_indicators = [
        '.*', '.+', '|', '^', '$',
        '\\(', '\\)', '\\[', '\\]',
        '{', '}', '?', '+'
    ]
    return any(indicator in target for indicator in regex_indicators)


class NabuTool(BaseTool):
    """
    Nabu-specific MCP tool base class.

    Extends BaseTool with nabu-specific features:
    - Database manager access
    - Incremental updater access
    - Output formatters (markdown, json)
    - Enhanced response builders
    - Schema generation from docstrings

    Each tool must implement:
    - execute(**kwargs) -> Dict[str, Any]: The main tool logic
    """

    def __init__(self, factory: "NabuMCPFactory"):
        """
        Initialize tool with factory reference.

        Args:
            factory: The NabuMCPFactory that created this tool
        """
        super().__init__(factory)
        self._output_format = "json"  # Nabu-specific: track requested output format

    # Note: get_name_from_cls() and get_name() inherited from BaseTool

    # Agent access property (explicit pattern acknowledgment)
    @property
    def agent(self):
        """
        Access to NabuAgent for stateful resources.

        The agent manages:
        - Database managers (multi-codebase)
        - Incremental updaters
        - Auto-indexing
        - Session tracking
        - Workflow guidance

        Returns:
            NabuAgent instance
        """
        return self.factory.agent

    # Nabu-specific: Database access properties
    @property
    def db_manager(self):
        """
        Access to database manager.
        
        Automatically uses the codebase from execution context if set,
        otherwise falls back to active codebase.
        """
        # Check if we're in a codebase-specific execution context
        context_codebase = _current_codebase_context.get()
        
        if context_codebase:
            # Use context-specific database manager
            return self.factory.db_managers.get(context_codebase, self.factory.db_manager)
        
        # Fall back to factory's current db_manager (active codebase)
        return self.factory.db_manager

    @property
    def incremental_updater(self):
        """
        Access to incremental updater.
        
        Automatically uses the codebase from execution context if set,
        otherwise falls back to active codebase.
        """
        # Check if we're in a codebase-specific execution context
        context_codebase = _current_codebase_context.get()
        
        if context_codebase:
            # Use context-specific incremental updater
            return self.factory.incremental_updaters.get(context_codebase, self.factory.incremental_updater)
        
        # Fall back to factory's current incremental_updater (active codebase)
        return self.factory.incremental_updater

    def get_db_manager(self, codebase: Optional[str] = None):
        """
        Get database manager for specified codebase.
        
        Args:
            codebase: Codebase name, or None to use active codebase
            
        Returns:
            KuzuConnectionManager for the codebase
            
        Raises:
            ValueError: If codebase not found
        """
        target = codebase or self.config.active_codebase
        
        if target not in self.factory.db_managers:
            available = list(self.factory.db_managers.keys())
            raise ValueError(
                f"Codebase '{target}' not found. Available: {available}"
            )
        
        return self.factory.db_managers[target]

    def get_codebase_config(self, codebase: Optional[str] = None):
        """
        Get configuration for specified codebase.
        
        Args:
            codebase: Codebase name, or None to use active codebase
            
        Returns:
            CodebaseConfig for the codebase
            
        Raises:
            ValueError: If codebase not found
        """
        target = codebase or self.config.active_codebase
        
        if target not in self.config.codebases:
            available = list(self.config.codebases.keys())
            raise ValueError(
                f"Codebase '{target}' not found. Available: {available}"
            )
        
        return self.config.codebases[target]

    def _check_indexing_status(self, codebase: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if codebase is being indexed and return error response if so.

        This method should be called at the start of execute() in tools that
        require database access (search, query, skeleton, etc.).

        Args:
            codebase: Codebase to check, or None for active codebase

        Returns:
            Error response dict if indexing in progress or failed, None if ready
        """
        target = codebase or self.config.active_codebase

        if not self.factory.auto_indexer:
            return None  # No auto-indexer, skip check

        from nabu.mcp.indexing import IndexingState
        status = self.factory.auto_indexer.get_status(target)

        if status.state in (IndexingState.UNINDEXED, IndexingState.QUEUED):
            return self._error_response(
                RuntimeError(f"Codebase '{target}' is queued for indexing"),
                severity=ErrorSeverity.WARNING,
                recovery_hint=(
                    f"Database is being prepared. State: {status.state.value}. "
                    "Check show_status() for progress."
                )
            )

        if status.state == IndexingState.INDEXING:
            elapsed = time.time() - status.started_at if status.started_at else 0
            return self._error_response(
                RuntimeError(f"Codebase '{target}' is currently being indexed"),
                severity=ErrorSeverity.WARNING,
                recovery_hint=(
                    f"Indexing in progress ({elapsed:.1f}s elapsed). "
                    "This may take several minutes for large codebases. "
                    "Check show_status() for updates."
                )
            )

        if status.state == IndexingState.ERROR:
            return self._error_response(
                RuntimeError(f"Codebase '{target}' indexing failed"),
                severity=ErrorSeverity.ERROR,
                recovery_hint=(
                    f"Auto-indexing failed: {status.error_message}. "
                    "Use rebuild_database() tool to retry manually."
                )
            )

        # State is INDEXED - all good
        return None

    async def _resolve_frame(
        self,
        target: str,
        frame_type: Optional[str] = None,
        require_exact: bool = False,
        is_regex: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Unified frame resolution with intelligent matching and regex support.

        Supports flexible input formats:
        - Simple name: "MyClass" → matches any frame with that name
        - Hierarchical path: "utils/MyClass" or "MyClass/my_method"
        - Qualified name: "nabu.mcp.utils.MyClass"
        - Regex pattern (with is_regex=True): ".*Tool$" or "(Foo|Bar)Handler"

        Args:
            target: Frame identifier (name, qualified name, hierarchical path, or regex pattern)
            frame_type: Optional frame type filter (e.g., "CLASS", "CALLABLE")
            require_exact: If True, only exact qualified_name matches allowed (ignored if is_regex=True)
            is_regex: If True, treat target as regex pattern and return multiple matches
            limit: Maximum number of results to return (only applies when is_regex=True)

        Returns:
            List of frame data dicts. Returns single-element list for non-regex queries,
            multiple elements for regex queries, or empty list if no matches found.
        """
        if not self.db_manager:
            raise RuntimeError("Database manager not initialized - cannot resolve frames")

        # ========== REGEX PATH ==========
        if is_regex:
            # Validate regex pattern
            try:
                regex_obj = re.compile(target)
            except re.error as e:
                self.logger.error(f"Invalid regex pattern '{target}': {e}")
                return []

            try:
                # STRATEGY: Two-path approach (aligned with SearchTool._regex_search)
                # PATH 1: Cypher native regex (fast, database-side filtering)
                # PATH 2: Keyword extraction + Python regex (fallback for complex patterns)

                results = []
                result_ids = set()

                # ========== PATH 1: Cypher Native Regex (Primary) ==========
                # Escape single quotes for safe Cypher interpolation
                escaped_pattern = target.replace("'", "\\'")

                cypher_query = f"""
                MATCH (f:Frame)
                WHERE f.name =~ '{escaped_pattern}'
                   OR f.qualified_name =~ '{escaped_pattern}'
                """

                # Add frame type filter if specified
                if frame_type:
                    # Support both single type and pipe-separated list
                    if '|' in frame_type:
                        type_list = [t.strip() for t in frame_type.split('|')]
                        type_list_str = str(type_list).replace("'", '"')  # Cypher uses double quotes
                        cypher_query += f"\n   AND f.type IN {type_list_str}"
                    else:
                        cypher_query += f"\n   AND f.type = '{frame_type}'"

                cypher_query += f"""
                RETURN f.id as id, f.type as type, f.name as name,
                       f.qualified_name as qualified_name,
                       f.file_path as file_path, f.start_line as start_line,
                       f.end_line as end_line, f.language as language,
                       f.instance_fields as instance_fields, f.static_fields as static_fields,
                       f.content as content, f.parameters as parameters,
                       f.return_type as return_type
                LIMIT {limit}
                """

                result = self.db_manager.execute(cypher_query)

                if result and hasattr(result, 'get_as_df'):
                    df = result.get_as_df()
                    if not df.empty:
                        for _, row in df.iterrows():
                            frame_dict = self._row_to_frame_dict(row)
                            results.append(frame_dict)
                            result_ids.add(frame_dict['id'])

                # ========== PATH 2: Keyword Extraction Fallback ==========
                # If Cypher regex found nothing, try keyword extraction approach
                # This helps with patterns where Cypher regex behaves differently than Python
                if not results:
                    keywords = extract_keywords_from_regex(target)

                    if keywords:
                        # Use CONTAINS with extracted keywords to narrow candidates
                        keyword_list = keywords.split()
                        contains_conditions = " OR ".join(
                            f"f.name CONTAINS '{kw}' OR f.qualified_name CONTAINS '{kw}'"
                            for kw in keyword_list[:3]  # Limit to first 3 keywords
                        )

                        fallback_query = f"""
                        MATCH (f:Frame)
                        WHERE {contains_conditions}
                        """

                        # Add frame type filter
                        if frame_type:
                            if '|' in frame_type:
                                type_list = [t.strip() for t in frame_type.split('|')]
                                type_list_str = str(type_list).replace("'", '"')
                                fallback_query += f"\n   AND f.type IN {type_list_str}"
                            else:
                                fallback_query += f"\n   AND f.type = '{frame_type}'"

                        fallback_query += f"""
                        RETURN f.id as id, f.type as type, f.name as name,
                               f.qualified_name as qualified_name,
                               f.file_path as file_path, f.start_line as start_line,
                               f.end_line as end_line, f.language as language,
                               f.instance_fields as instance_fields, f.static_fields as static_fields,
                               f.content as content, f.parameters as parameters,
                               f.return_type as return_type
                        LIMIT {limit * 3}
                        """

                        result = self.db_manager.execute(fallback_query)
                        candidates = []

                        if result and hasattr(result, 'get_as_df'):
                            df = result.get_as_df()
                            if not df.empty:
                                for _, row in df.iterrows():
                                    candidates.append(self._row_to_frame_dict(row))

                        # Apply Python regex filter on candidates
                        for candidate in candidates:
                            if candidate['id'] in result_ids:
                                continue  # Skip duplicates

                            if regex_obj.search(candidate['name']) or regex_obj.search(candidate['qualified_name']):
                                results.append(candidate)
                                result_ids.add(candidate['id'])
                                if len(results) >= limit:
                                    break

                return results

            except Exception as e:
                self.logger.error(f"Regex frame resolution failed for '{target}': {e}", exc_info=True)
                return []

        # ========== NON-REGEX PATH (backward compatible) ==========
        # Normalize hierarchical paths: "utils/MyClass" → "utils.MyClass"
        normalized_target = target.replace('/', '.')

        # Build query based on requirements
        if require_exact:
            # Vector tools need exact match for performance
            # Support both full qualified names and simple names (ends with)
            query = """
            MATCH (f:Frame)
            WHERE (f.qualified_name = $target
               OR f.qualified_name ENDS WITH $target_suffix)
            """
        else:
            # Flexible matching with priority ordering
            query = """
            MATCH (f:Frame)
            WHERE (f.name = $target
               OR f.qualified_name = $normalized_target
               OR f.qualified_name CONTAINS $normalized_target
               OR f.name CONTAINS $target)
            """

        # Add frame type filter if specified
        if frame_type:
            # Support both single type and pipe-separated list
            if '|' in frame_type:
                type_list = [t.strip() for t in frame_type.split('|')]
                type_list_str = str(type_list).replace("'", '"')  # Cypher uses double quotes
                query += f"\n        AND f.type IN {type_list_str}"
            else:
                query += f"\n        AND f.type = '{frame_type}'"

        query += """
        RETURN f.id as id, f.type as type, f.name as name,
               f.qualified_name as qualified_name,
               f.file_path as file_path, f.start_line as start_line,
               f.end_line as end_line, f.language as language,
               f.instance_fields as instance_fields, f.static_fields as static_fields,
               f.content as content, f.parameters as parameters,
               f.return_type as return_type
        """

        if not require_exact:
            query += """
            ORDER BY
                CASE
                    WHEN f.qualified_name = $normalized_target THEN 0
                    WHEN f.name = $target THEN 1
                    WHEN f.qualified_name CONTAINS $normalized_target THEN 2
                    ELSE 3
                END
            """

        query += "\n        LIMIT 1"

        # Prepare target suffix for ENDS WITH matching (e.g., ".my_function")
        target_suffix = f".{target}" if not target.startswith('.') else target

        try:
            # Build parameters dict - only include target_suffix for exact matching
            params = {
                "target": target,
                "normalized_target": normalized_target
            }
            if require_exact:
                params["target_suffix"] = target_suffix

            result = self.db_manager.execute(query, params)
            df = result.get_as_df()

            if df.empty:
                # Step 4: FTS fuzzy fallback (if not require_exact)
                if not require_exact:
                    candidates = await self._fts_fuzzy_resolve(target, frame_type, limit=10)
                    if candidates:
                        # Mark as FTS resolution
                        for candidate in candidates:
                            candidate['_resolution_strategy'] = 'fts_fuzzy'
                        return candidates
                return []

            row = df.iloc[0]
            # Return as single-element list for backward compatibility
            frame_dict = self._row_to_frame_dict(row)
            frame_dict['_resolution_strategy'] = 'contains' if not require_exact else 'exact'
            return [frame_dict]

        except Exception as e:
            self.logger.error(f"Frame resolution failed for '{target}': {e}", exc_info=True)
            return []

    async def _fts_fuzzy_resolve(
        self,
        target: str,
        frame_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        FTS-based fuzzy resolution with multi-signal ranking.

        Uses porter stemmer for case-insensitivity and stemming.
        Generates naming convention variants (PascalCase ↔ snake_case).

        Args:
            target: Original target string
            frame_type: Optional frame type filter
            limit: Max results to return

        Returns:
            List of frame dicts sorted by relevance score
        """
        from nabu.mcp.utils.regex_helpers import generate_fts_query_variants

        # Generate FTS query with convention variants
        fts_query = generate_fts_query_variants(target)

        # Build FTS query on resolution index (porter stemmer handles case)
        cypher_query = (
            f"CALL QUERY_FTS_INDEX('Frame', 'frame_resolution_fts_index', '{fts_query}', "
            f"conjunctive := false"  # OR behavior for variants
        )

        if limit > 0:
            cypher_query += f", TOP := {limit * 3}"  # Over-fetch for ranking

        cypher_query += (
            ") RETURN score, node.id as id, node.type as type, node.name as name, "
            "node.qualified_name as qualified_name, node.file_path as file_path, "
            "node.start_line as start_line, node.end_line as end_line, "
            "node.language as language, node.instance_fields as instance_fields, "
            "node.static_fields as static_fields, node.content as content, "
            "node.parameters as parameters, node.return_type as return_type;"
        )

        # Execute FTS query
        try:
            result = self.db_manager.execute(cypher_query, load_extensions=True)
        except Exception as e:
            self.logger.error(f"FTS fuzzy resolve failed: {e}")
            return []

        if not result or not hasattr(result, 'get_as_df'):
            return []

        df = result.get_as_df()
        if df.empty:
            return []

        # Convert to list and apply multi-signal ranking
        candidates = []
        target_lower = target.lower()

        for _, row in df.iterrows():
            frame_dict = self._row_to_frame_dict(row)
            bm25_score = float(row['score'])

            # Multi-signal boosting (FTS already did base matching)
            boosts = []

            # Exact name match (case-insensitive, since FTS matched)
            if frame_dict['name'].lower() == target_lower:
                boosts.append(('exact_name', 3.0))

            # Exact qualified name match (rare but highest confidence)
            if frame_dict['qualified_name'].lower() == target_lower:
                boosts.append(('exact_qname', 5.0))

            # Type match boost
            if frame_type:
                type_filter = frame_type.split('|')
                if frame_dict['type'] in type_filter:
                    boosts.append(('type_match', 2.0))

            # File path heuristics (penalize tests/examples, boost src)
            file_path = frame_dict['file_path'].lower()
            if 'test' in file_path or '/tests/' in file_path:
                boosts.append(('test_penalty', -1.0))
            elif 'example' in file_path or 'demo' in file_path:
                boosts.append(('demo_penalty', -0.5))
            elif '/src/' in file_path:
                boosts.append(('src_boost', 0.5))

            # Calculate final score
            total_boost = sum(b[1] for b in boosts)
            final_score = bm25_score + total_boost

            # Build explanation
            boost_parts = [f"{name}={val:+.1f}" for name, val in boosts]
            explanation = f"FTS fuzzy (BM25={bm25_score:.1f}" + (f", {', '.join(boost_parts)}" if boost_parts else "") + ")"

            frame_dict['_fts_score'] = final_score
            frame_dict['_match_explanation'] = explanation
            candidates.append(frame_dict)

        # Sort by final score and limit
        candidates.sort(key=lambda x: x['_fts_score'], reverse=True)
        return candidates[:limit]

    def _row_to_frame_dict(self, row) -> Dict[str, Any]:
        """
        Convert database row to frame dictionary.

        Args:
            row: Database row (pandas Series or similar)

        Returns:
            Frame data dictionary
        """
        # Handle frames without file locations (CODEBASE, LANGUAGE)
        # Check for None, pd.NA, nan, empty string
        file_path = row['file_path']
        start_line = row['start_line'] if row['start_line'] is not None else 0
        end_line = row['end_line'] if row['end_line'] is not None else 0

        if file_path is not None and str(file_path).lower() != 'nan' and file_path != '':
            location = f"{Path(file_path).name}:{start_line}-{end_line}"
        else:
            file_path = ""
            location = "virtual"

        return {
            "id": row['id'],
            "type": row['type'],
            "name": row['name'],
            "qualified_name": row['qualified_name'],
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "location": location,
            "language": row.get('language', ''),
            "instance_fields": row.get('instance_fields', []) or [],
            "static_fields": row.get('static_fields', []) or [],
            "content": row.get('content', ''),
            "parameters": row.get('parameters', []) or [],
            "return_type": row.get('return_type', '')
        }


    @classmethod
    def _python_type_to_json_type(cls, python_type: Any) -> str:
        """
        Convert Python type hint to JSON Schema type.
        
        Args:
            python_type: Python type annotation
            
        Returns:
            JSON Schema type string
        """
        # Handle None/NoneType
        if python_type is None or python_type == type(None):
            return "null"
        
        # Handle typing module types
        origin = get_origin(python_type)
        
        # Handle Optional[T] -> T | None
        if origin is type(None) or str(python_type).startswith('typing.Optional'):
            args = get_args(python_type)
            if args:
                return cls._python_type_to_json_type(args[0])
            return "null"
        
        # Handle List, Dict, etc
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
        if origin is tuple:
            return "array"
        
        # Handle Union types (not Optional)
        if origin is Union:
            args = get_args(python_type)
            # For now, just use first non-None type
            for arg in args:
                if arg != type(None):
                    return cls._python_type_to_json_type(arg)
        
        # Map basic Python types to JSON Schema types
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            dict: "object",
            list: "array",
            Dict: "object",
            List: "array",
        }
        
        # Try exact match first
        if python_type in type_map:
            return type_map[python_type]
        
        # Check if it's a class (try name-based matching)
        if hasattr(python_type, '__name__'):
            type_name = python_type.__name__
            if type_name in ['str', 'string']:
                return "string"
            elif type_name in ['int', 'integer']:
                return "integer"
            elif type_name in ['float', 'number', 'double']:
                return "number"
            elif type_name in ['bool', 'boolean']:
                return "boolean"
            elif type_name in ['dict', 'Dict']:
                return "object"
            elif type_name in ['list', 'List']:
                return "array"
        
        # Default to string
        return "string"
    
    @classmethod
    def get_tool_schema(cls) -> Dict[str, Any]:
        """
        Generate JSON schema from execute() signature and docstring.
        
        Parses the execute() method's signature and docstring to generate
        a JSON schema compatible with MCP tool registration.
        
        Returns:
            Dict containing tool name, description, and parameter schema
            
        Example output:
            {
                "name": "query",
                "description": "Execute Cypher queries against KuzuDB",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cypher_query": {
                            "type": "string",
                            "description": "The Cypher query to execute"
                        }
                    },
                    "required": ["cypher_query"]
                }
            }
        """
        tool_name = cls.get_name_from_cls()
        
        # Get execute method
        execute_method = cls.execute
        sig = inspect.signature(execute_method)
        
        # Parse docstring
        docstring_text = execute_method.__doc__ or ""
        
        if DOCSTRING_PARSER_AVAILABLE and docstring_text:
            docstring = parse_docstring(docstring_text)
            
            # Build description components
            description_parts = []
            
            # Add short description
            if docstring.short_description:
                description_parts.append(docstring.short_description.strip())
            
            # Add long description
            if docstring.long_description:
                description_parts.append(docstring.long_description.strip())
            
            # Add return description if available
            if docstring.returns and docstring.returns.description:
                return_desc = docstring.returns.description.strip()
                description_parts.append(f"Returns: {return_desc}")
            
            # Combine all parts
            description = "\n\n".join(description_parts)
            
            # Build param description map
            param_descriptions = {
                param.arg_name: param.description 
                for param in docstring.params 
                if param.description
            }
            
            # Extract meta fields for enhanced documentation
            meta_fields = {}
            if hasattr(docstring, 'meta') and docstring.meta:
                for meta in docstring.meta:
                    if hasattr(meta, 'args') and len(meta.args) >= 2:
                        # For :meta pitch: syntax, args = ['meta', 'pitch']
                        if meta.args[0] == 'meta':
                            meta_fields[meta.args[1]] = meta.description
        else:
            # Fallback if docstring_parser not available
            description = docstring_text.strip()
            param_descriptions = {}
            meta_fields = {}
        
        # Build parameter schema
        properties = {}
        required = []
        type_hints = get_type_hints(execute_method)
        
        for param_name, param in sig.parameters.items():
            if param_name in ["self", "kwargs"]:
                continue
            
            # Get type annotation
            param_type = type_hints.get(param_name, Any)
            json_type = cls._python_type_to_json_type(param_type)
            
            # Get description from docstring
            param_desc = param_descriptions.get(param_name, "")
            
            # Format description: capitalize first letter and ensure period at end
            if param_desc:
                param_desc = param_desc.strip().rstrip('.')  # Remove trailing dots first
                if param_desc:  # Check again after stripping
                    # Capitalize first letter
                    param_desc = param_desc[0].upper() + param_desc[1:] if len(param_desc) > 0 else param_desc
                    # Add period at end
                    param_desc += '.'
            
            # Build parameter schema entry
            param_schema = {
                "type": json_type
            }
            
            # Add description only if non-empty
            if param_desc:
                param_schema["description"] = param_desc
            
            # Add default value if available
            if param.default != inspect.Parameter.empty:
                # Only include serializable defaults
                try:
                    import json
                    json.dumps(param.default)  # Test if serializable
                    param_schema["default"] = param.default
                except (TypeError, ValueError):
                    # Skip non-serializable defaults
                    pass
            else:
                # No default = required parameter
                required.append(param_name)
            
            properties[param_name] = param_schema

        # Inject output_format parameter (not in execute() signature)
        properties["output_format"] = {
            "type": "string",
            "description": "Output format for response data (json, markdown, etc.).",
            "default": "markdown"
        }

        # Inject codebase parameter (automatic multi-codebase support)
        # Only inject if not already defined by the tool (e.g., ActivateCodebaseTool)
        if "codebase" not in properties:
            properties["codebase"] = {
                "type": "string",
                "description": "Codebase to query (defaults to active codebase).",
                "default": None
            }

        return {
            "name": tool_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            },
            "meta": meta_fields
        }
    
    @classmethod
    def get_tool_description(cls) -> str:
        """
        Get human-readable tool description.
        
        Returns:
            Description string extracted from class and execute() docstrings
        """
        class_doc = cls.__doc__ or ""
        execute_doc = cls.execute.__doc__ or ""
        
        if DOCSTRING_PARSER_AVAILABLE and execute_doc:
            docstring = parse_docstring(execute_doc)
            return docstring.short_description or class_doc.strip()
        
        # Fallback: use first line of execute docstring or class docstring
        if execute_doc:
            return execute_doc.strip().split('\n')[0]
        return class_doc.strip()

    # Note: get_tool_pitch, get_tool_examples, get_tool_tips, and get_tool_patterns
    # are now inherited from nisaba.BaseTool base class
    # Note: execute() is also inherited from nisaba.BaseTool base class

    async def execute_with_timing(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with automatic timing and codebase context switching.

        Wrapper around execute() that adds:
        - Timing and error handling
        - Automatic codebase context management (middleware pattern)
        - Session tracking
        """
        start_time = time.time()

        # Check if tool's execute() method expects 'codebase' as its own parameter
        # (e.g., ActivateCodebaseTool uses it as a tool parameter, not for context switching)
        sig = inspect.signature(self.execute)
        tool_expects_codebase = 'codebase' in sig.parameters

        # Extract special parameters (don't pass to execute())
        self._output_format = kwargs.pop("output_format", "json")

        # Only pop codebase for context switching if tool doesn't use it as parameter
        if tool_expects_codebase:
            # Tool uses codebase as its own parameter - don't pop it
            requested_codebase = None
        else:
            # Pop codebase for context switching (multi-codebase query support)
            requested_codebase = kwargs.pop("codebase", None)
        
        # Validate requested codebase if specified
        if requested_codebase is not None:
            if requested_codebase not in self.factory.db_managers:
                available = list(self.factory.db_managers.keys())
                return self._error_response(
                    ValueError(f"Unknown codebase: '{requested_codebase}'"),
                    start_time,
                    recovery_hint=f"Available codebases: {', '.join(available)}. Use list_codebases() to see all registered codebases."
                )
        
        # Set codebase context for this execution (thread-safe via contextvars)
        token = _current_codebase_context.set(requested_codebase)

        try:
            # Execute tool (tools transparently use correct db_manager via property)
            result = await self.execute(**kwargs)
    
            # Record in guidance system using parent class method
            self._record_guidance(self.get_name(), kwargs, result)

            return result
        
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}", exc_info=True)
            return self._error_response(e, start_time)
        
        finally:
            # ALWAYS restore context (critical for async safety)
            _current_codebase_context.reset(token)
    
    def _success_response(
        self, 
        data: Any, 
        warnings: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create standardized success response using ResponseBuilder.
        
        Args:
            data: Response payload
            start_time: Start time for execution time calculation
            warnings: Optional warning messages
            metadata: Optional operation metadata
            
        Returns:
            Standardized success response
        """
        # Format data according to requested output format
        from nabu.mcp.formatters import get_formatter_registry

        try:
            formatter_registry = get_formatter_registry()
            formatter = formatter_registry.get_formatter(self._output_format)
            # Round floats before formatting (so markdown gets clean numbers)
            from nisaba.utils.response import ResponseBuilder as RB
            data = RB._round_floats(data)
            formatted_data = formatter.format(data, tool_name=self.get_name())
        except ValueError as e:
            # Unsupported format - log warning and fall back to JSON
            self.logger.warning(f"Output format error: {e}. Falling back to JSON.")
            formatted_data = data

        return ResponseBuilder.success(
            data=formatted_data,
            warnings=warnings,
            metadata=metadata
        )
    
    def _error_response(
        self, 
        error: Exception, 
        start_time: float = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        recovery_hint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create standardized error response using ResponseBuilder.
        
        Args:
            error: Exception that occurred
            start_time: Start time for execution time calculation
            severity: Error severity level
            recovery_hint: Suggested recovery action
            context: Error context information
            
        Returns:
            Standardized error response
        """
        return ResponseBuilder.error(
            error=error,
            severity=severity,
            recovery_hint=recovery_hint,
            context=context
        )
    
    # Note: is_optional(), is_dev_only(), is_mutating() inherited from BaseTool
