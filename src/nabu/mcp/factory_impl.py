"""Concrete factory implementation for single-process nabu MCP server."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Iterator
import logging

from mcp.server.fastmcp import FastMCP

from nabu.mcp.factory import NabuMCPFactory
from nabu.mcp.config.nabu_config import NabuConfig
from nabu.mcp.tools.base import NabuTool
from nabu.mcp.guidance_config import NABU_GUIDANCE_GRAPH
from nisaba.guidance import WorkflowGuidance

logger = logging.getLogger(__name__)


class NabuMCPFactorySingleProcess(NabuMCPFactory):
    """
    Single-process nabu MCP server factory.
    
    Runs database manager and tools in the same process as MCP server.
    """
    
    def __init__(self, config: NabuConfig):
        """Initialize single-process factory."""
        super().__init__(config)
        self._tool_instances = None

        # Initialize agent (holds all stateful resources)
        from nabu.mcp.agent import NabuAgent
        self.agent = NabuAgent(config, factory=self)

        # Backward compatibility: Expose agent attributes on factory
        # (Tools may still access self.factory.db_manager, etc.)
        # These are now properties that delegate to agent

    # Backward compatibility properties - delegate to agent
    @property
    def db_managers(self):
        return self.agent.db_managers

    @property
    def incremental_updaters(self):
        return self.agent.incremental_updaters

    @property
    def db_manager(self):
        return self.agent.db_manager

    @db_manager.setter
    def db_manager(self, value):
        # During __init__, agent might not exist yet (parent class sets these)
        if hasattr(self, 'agent'):
            self.agent.db_manager = value

    @property
    def incremental_updater(self):
        return self.agent.incremental_updater

    @incremental_updater.setter
    def incremental_updater(self, value):
        # During __init__, agent might not exist yet (parent class sets these)
        if hasattr(self, 'agent'):
            self.agent.incremental_updater = value

    @property
    def auto_indexer(self):
        return self.agent.auto_indexer

    @auto_indexer.setter
    def auto_indexer(self, value):
        # During __init__, agent might not exist yet
        if hasattr(self, 'agent'):
            self.agent.auto_indexer = value

    @property
    def guidance(self):
        """
        Delegate to agent's guidance for nisaba MCPTool integration.

        Nisaba's MCPTool._record_guidance() checks self.factory.guidance,
        so we expose agent's guidance system at factory level.
        """
        return self.agent.guidance if hasattr(self, 'agent') else None

    # Note: session_tracker is accessed via agent directly
    # Tools should use: self.factory.agent.session_tracker or self.agent.session_tracker

    def _iter_tools(self) -> Iterator[NabuTool]:
        """
        Iterate over enabled tool instances.
        
        Lazily instantiates tools on first call.
        """
        if self._tool_instances is None:
            self._instantiate_tools()
        
        return iter(self._tool_instances)
    
    def _instantiate_tools(self):
        """Create tool instances for enabled tools."""
        enabled_tool_names = self._filter_enabled_tools()
        
        self._tool_instances = []
        
        for tool_name in enabled_tool_names:
            try:
                tool_class = self.registry.get_tool_class(tool_name)
                tool_instance = tool_class(factory=self)
                self._tool_instances.append(tool_instance)
            except Exception as e:
                logger.error(f"Failed to instantiate tool {tool_name}: {e}")
        
        logger.info(f"Instantiated {len(self._tool_instances)} tools: {enabled_tool_names}")
    
    # ==================================================================================
    # Dynamic Instructions Generation Methods
    # ==================================================================================

    def _get_initial_instructions(self) -> str:
        """Generate complete initial instructions with dynamic content."""
        try:
            # Load template using nisaba's engine
            instructions_path = Path(__file__).parent / "resources" / "instructions_template.md"
            engine = self._load_template_engine(
                template_path=instructions_path,
                runtime_context={'dev_mode': self.config.dev_mode}
            )

            # Generate dynamic sections
            logger.info("Generating MCP instructions...")

            # Render with placeholders and clear unused ones
            instructions = engine.render_and_clear()

            logger.info(f"Generated instructions ({len(instructions)} chars)")
            return instructions

        except Exception as e:
            logger.error(f"Failed to generate instructions: {e}", exc_info=True)
            return ""
    
    @asynccontextmanager
    async def server_lifespan(self, mcp_server: FastMCP) -> AsyncIterator[None]:
        """
        Manage nabu MCP server lifecycle.

        Delegates to NabuAgent for resource management.
        """
        # STARTUP
        logger.info("=" * 60)
        logger.info("Nabu MCP Server - Lifecycle Starting")
        logger.info("=" * 60)

        # Initialize agent (database managers, updaters, file watchers)
        await self.agent.initialize()

        # Register tools
        self._register_tools(mcp_server)

        # Start HTTP transport if enabled
        await self._start_http_transport_if_enabled()

        logger.info("Nabu MCP Server - Ready")
        logger.info("=" * 60)

        yield  # Server runs here

        # SHUTDOWN
        logger.info("=" * 60)
        logger.info("Nabu MCP Server - Lifecycle Shutdown")
        logger.info("=" * 60)

        # Stop HTTP transport
        await self._stop_http_transport()

        # Cleanup agent resources
        await self.agent.shutdown()

        logger.info("Nabu MCP Server - Shutdown Complete")
        logger.info("=" * 60)

    def _handle_file_change(self, file_path: str, codebase_name: str) -> None:
        """
        Handle file change event from watcher.
        
        Runs in file watcher thread pool. Updates file in database.
        
        Args:
            file_path: Absolute path to changed file
            codebase_name: Name of codebase being updated
        """
        updater = self.incremental_updaters.get(codebase_name)
        if not updater:
            logger.warning(f"File change detected but no updater for '{codebase_name}': {file_path}")
            return
        
        try:
            logger.debug(f"Processing file change in '{codebase_name}': {file_path}")
            result = updater.update_file(file_path)
            
            if result.success:
                logger.info(
                    f"✓ Auto-updated {Path(file_path).name} in '{codebase_name}': "
                    f"+{result.frames_added} -{result.frames_deleted} "
                    f"(={result.frames_stable}, {result.stability_percentage:.1f}% stable)"
                )
            else:
                logger.warning(
                    f"✗ Failed to auto-update {file_path} in '{codebase_name}': {result.errors}"
                )
        except Exception as e:
            logger.error(
                f"Error handling file change for {file_path} in '{codebase_name}': {e}",
                exc_info=self.config.dev_mode
            )
