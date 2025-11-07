"""Abstract base class for MCP tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import time

# Docstring parsing (optional dependency)
try:
    from docstring_parser import parse as parse_docstring
    DOCSTRING_PARSER_AVAILABLE = True
except ImportError:
    DOCSTRING_PARSER_AVAILABLE = False


class MCPTool(ABC):
    """
    Abstract base class for all MCP tools.

    Each tool must implement:
    - execute(**kwargs) -> Dict[str, Any]: The main tool logic
    """

    def __init__(self, factory: "MCPFactory"):
        """
        Initialize tool with factory reference.

        Args:
            factory: The MCPFactory that created this tool
        """
        self.factory = factory
        self.config = factory.config
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.get_name()}")

    @classmethod
    def get_name_from_cls(cls) -> str:
        """
        Get tool name from class name.

        Converts class name like "QueryTool" to "query".

        Returns:
            Tool name in snake_case
        """
        name = cls.__name__
        if name.endswith("Tool"):
            name = name[:-4]
        # Convert to snake_case
        name = "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")
        return name

    def get_name(self) -> str:
        """Get instance tool name."""
        return self.get_name_from_cls()

    @classmethod
    @abstractmethod
    def get_tool_schema(cls) -> Dict[str, Any]:
        """
        Get tool schema for MCP registration.

        Must return a dict with:
        {
            "name": str,
            "description": str,
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }

        Returns:
            Tool schema dictionary
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.

        Must return a dictionary with structure:
        {
            "success": bool,
            "data": Any,              # if success
            "error": str,             # if not success
            "error_type": str         # if not success
        }

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Dict with success/error response
        """
        pass

    def _record_guidance(self, tool_name: str, params: Dict[str, Any], result: Dict[str, Any]) -> None:
        """
        Record tool call in guidance system and add suggestions to result.

        This method can be called by subclasses that override execute_with_timing().
        Modifies result dict in-place to add _guidance field if suggestions available.

        Args:
            tool_name: Name of the tool that was executed
            params: Parameters passed to the tool
            result: Result dict (modified in-place)
        """
        if hasattr(self.factory, 'guidance') and self.factory.guidance is not None:
            try:
                self.factory.guidance.record_tool_call(
                    tool_name=tool_name,
                    params=params,
                    result=result
                )

                # Optionally add suggestions to result metadata
                suggestions = self.factory.guidance.get_suggestions()
                if suggestions:
                    result["_guidance"] = suggestions

            except Exception as guidance_error:
                # Don't fail tool execution if guidance fails
                self.logger.warning(f"Guidance tracking failed: {guidance_error}")

    async def execute_with_timing(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tool with automatic timing and error handling.

        Wrapper around execute() that adds timing and optional guidance tracking.

        Args:
            **kwargs: Tool-specific parameters

        Returns:
            Tool execution result with timing and optional guidance metadata
        """
        start_time = time.time()

        try:
            result = await self.execute(**kwargs)

            # Record in guidance system (subclasses can also call this)
            self._record_guidance(self.get_name(), kwargs, result)

            return result

        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }

    @classmethod
    def is_optional(cls) -> bool:
        """
        Check if tool is optional (disabled by default).

        Returns:
            True if tool is optional
        """
        from .markers import ToolMarkerOptional
        return issubclass(cls, ToolMarkerOptional)

    @classmethod
    def is_dev_only(cls) -> bool:
        """
        Check if tool is development-only.

        Returns:
            True if tool is dev-only
        """
        from .markers import ToolMarkerDevOnly
        return issubclass(cls, ToolMarkerDevOnly)

    @classmethod
    def is_mutating(cls) -> bool:
        """
        Check if tool modifies state.

        Returns:
            True if tool mutates state
        """
        from .markers import ToolMarkerMutating
        return issubclass(cls, ToolMarkerMutating)

    @classmethod
    @abstractmethod
    def get_tool_description(cls) -> str:
        """
        Get full tool description for instructions.

        This is typically extracted from the execute() method's docstring.

        Returns:
            Full description string
        """
        pass

    @classmethod
    def _get_meta_field(cls, field_name: str) -> Optional[str]:
        """
        Extract a :meta field: from execute() docstring.

        Args:
            field_name: Name of meta field (e.g., 'pitch', 'examples')

        Returns:
            Field description or None
        """
        execute_doc = cls.execute.__doc__ or ""

        if not DOCSTRING_PARSER_AVAILABLE or not execute_doc:
            return None

        docstring = parse_docstring(execute_doc)

        # Look for :meta field_name: field
        if hasattr(docstring, 'meta') and docstring.meta:
            for meta in docstring.meta:
                if hasattr(meta, 'args') and len(meta.args) >= 2:
                    if meta.args[0] == 'meta' and meta.args[1] == field_name:
                        return meta.description

        return None

    @classmethod
    def get_tool_pitch(cls) -> Optional[str]:
        """
        Get brief, inciting tool pitch for instructions.

        Extracts the :meta pitch: field from execute() docstring.
        Falls back to short_description if no pitch provided.

        Returns:
            Brief pitch string or None
        """
        pitch = cls._get_meta_field('pitch')
        if pitch:
            return pitch

        # Fallback to short description
        execute_doc = cls.execute.__doc__ or ""
        if DOCSTRING_PARSER_AVAILABLE and execute_doc:
            docstring = parse_docstring(execute_doc)
            return docstring.short_description

        return None

    @classmethod
    def get_tool_examples(cls) -> Optional[str]:
        """
        Get usage examples for this tool.

        Extracts the :meta examples: field from execute() docstring.

        Returns:
            Markdown-formatted examples or None
        """
        return cls._get_meta_field('examples')

    @classmethod
    def get_tool_tips(cls) -> Optional[str]:
        """
        Get best practices and tips for using this tool.

        Extracts the :meta tips: field from execute() docstring.

        Returns:
            Markdown-formatted tips or None
        """
        return cls._get_meta_field('tips')

    @classmethod
    def get_tool_patterns(cls) -> Optional[str]:
        """
        Get common usage patterns for this tool.

        Extracts the :meta patterns: field from execute() docstring.

        Returns:
            Markdown-formatted patterns or None
        """
        return cls._get_meta_field('patterns')
