"""Nabu MCP factory."""

from abc import abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncIterator, Iterator

# Import from framework
from nisaba import MCPFactory
from mcp.server.fastmcp import FastMCP

from nabu.mcp.config.nabu_config import NabuConfig
from nabu.mcp.tools.base import NabuTool


class NabuMCPFactory(MCPFactory):
    """
    Nabu-specific MCP factory.

    Extends MCPFactory for nabu. Concrete implementations should create
    a NabuAgent instance to manage stateful resources (database managers,
    incremental updaters, and workflow guidance).
    """

    def __init__(self, config: NabuConfig):
        """
        Initialize nabu factory.

        Args:
            config: NabuConfig instance
        """
        super().__init__(config)

        # Note: db_manager, incremental_updater, and guidance
        # are now managed by NabuAgent. Access via self.agent.* in subclasses.

    def _get_tool_base_class(self) -> type:
        """Get nabu's tool base class."""
        return NabuTool

    def _get_module_prefix(self) -> str:
        """Get nabu's tool module prefix."""
        return "nabu.mcp.tools"

    # Abstract methods remain abstract for subclasses
    @abstractmethod
    def _iter_tools(self) -> Iterator[NabuTool]:
        """Iterate over enabled tool instances."""
        pass

    @abstractmethod
    def _get_initial_instructions(self) -> str:
        """Get initial instructions for nabu MCP."""
        pass

    @asynccontextmanager
    @abstractmethod
    async def server_lifespan(self, mcp_server: FastMCP) -> AsyncIterator[None]:
        """Manage nabu server lifecycle."""
        yield
