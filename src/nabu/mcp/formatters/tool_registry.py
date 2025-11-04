"""
Tool-specific formatter registry.

Manages mapping between tool names and their specialized formatters.
"""

from typing import Dict, List, Optional
from .tool_base import BaseToolMarkdownFormatter


class ToolMarkdownFormatterRegistry:
    """
    Registry for tool-specific markdown formatters.

    Manages mapping between tool names and their specialized formatters.
    Similar to language handler registries in the skeleton formatter system.
    Provides extensibility for adding new tool-specific formatters.
    """

    def __init__(self):
        """Initialize registry with built-in tool formatters."""
        self._formatters: Dict[str, BaseToolMarkdownFormatter] = {}
        self._register_builtin_formatters()

    def _register_builtin_formatters(self):
        """Register built-in tool formatters."""
        # Lazy imports to avoid circular dependencies
        from .tools.exploration import ExploreProjectMarkdownFormatter
        from .tools.query import QueryMarkdownFormatter
        from .tools.structure import ShowStructureMarkdownFormatter
        from .tools.impact import ImpactAnalysisWorkflowMarkdownFormatter
        from .tools.reindex import ReindexMarkdownFormatter
        from .tools.clones import FindClonesMarkdownFormatter
        from .tools.status import ShowStatusMarkdownFormatter
        from .tools.codebases import ListCodebasesMarkdownFormatter, ActivateCodebaseMarkdownFormatter
        from .tools.search import SearchToolMarkdownFormatter

        # Register map_codebase compact formatter
        self.register("map_codebase", ExploreProjectMarkdownFormatter())
        # Register query_relationships compact formatter
        self.register("query_relationships", QueryMarkdownFormatter())
        # Register show_structure compact formatter (skeleton + optional relationships)
        self.register("show_structure", ShowStructureMarkdownFormatter())
        # Register check_impact compact formatter
        self.register("check_impact", ImpactAnalysisWorkflowMarkdownFormatter())
        # Register rebuild_database compact formatter
        self.register("rebuild_database", ReindexMarkdownFormatter())
        # Register find_clones compact formatter
        self.register("find_clones", FindClonesMarkdownFormatter())
        # Register show_status compact formatter
        self.register("show_status", ShowStatusMarkdownFormatter())
        # Register list_codebases compact formatter
        self.register("list_codebases", ListCodebasesMarkdownFormatter())
        # Register activate_codebase compact formatter
        self.register("activate_codebase", ActivateCodebaseMarkdownFormatter())
        # Register search compact formatter
        self.register("search", SearchToolMarkdownFormatter())

    def register(self, tool_name: str, formatter: BaseToolMarkdownFormatter):
        """
        Register a tool-specific formatter.

        Args:
            tool_name: Tool name (e.g., "show_structure", "fts_query")
            formatter: Formatter instance
        """
        self._formatters[tool_name] = formatter

    def get_formatter(self, tool_name: str) -> Optional[BaseToolMarkdownFormatter]:
        """
        Get formatter for specified tool.

        Args:
            tool_name: Tool name

        Returns:
            Formatter instance if registered, None otherwise
        """
        return self._formatters.get(tool_name)

    def has_formatter(self, tool_name: str) -> bool:
        """
        Check if tool has a registered formatter.

        Args:
            tool_name: Tool name

        Returns:
            True if formatter is registered, False otherwise
        """
        return tool_name in self._formatters

    def list_tools(self) -> List[str]:
        """
        List tools with registered formatters.

        Returns:
            List of tool names with specialized formatters
        """
        return list(self._formatters.keys())


def _setup_tool_formatters():
    """
    Setup function to initialize tool formatters.

    Called automatically on module import to register all tool formatters.
    """
    # The initialization happens in ToolMarkdownFormatterRegistry.__init__()
    # This function exists for consistency with language_handlers pattern
    pass
