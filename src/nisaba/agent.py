"""Base agent class for MCP lifecycle management."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nisaba.guidance import WorkflowGuidance


class Agent(ABC):
    """
    Abstract base class for MCP agents with lifecycle management.

    Agents handle stateful resources (databases, file watchers, caches, etc.)
    that require proper initialization and cleanup during MCP server lifecycle.

    The factory's server_lifespan() should call:
    1. await agent.initialize() - during startup
    2. await agent.shutdown() - during shutdown

    Attributes:
        guidance: Optional workflow guidance system for contextual tool suggestions.
                  Subclasses can set this to enable guidance (e.g., NabuAgent does).
    """

    def __init__(self):
        """
        Initialize base agent.

        Subclasses should call super().__init__() and then initialize their
        specific resources. Guidance is optional - set to WorkflowGuidance
        instance if desired.
        """
        self.guidance: Optional["WorkflowGuidance"] = None

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize agent resources (lifecycle startup).

        Called once during MCP server startup, before tools are registered.
        Use this for:
        - Database connection initialization
        - File watcher setup
        - Cache loading
        - Auto-indexing startup
        - Any heavyweight resource allocation

        Raises:
            Exception: If initialization fails (will prevent server startup)
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Cleanup agent resources (lifecycle shutdown).

        Called once during MCP server shutdown, after tools stop accepting requests.
        Use this for:
        - Database connection cleanup
        - File watcher teardown
        - Cache saving
        - Auto-indexing stop
        - Any resource deallocation

        Should handle errors gracefully (log warnings, don't raise).
        """
        pass
