"""
Base service class with common functionality.

Services in nabu follow these principles:
- Accept simple parameters (not MCP-specific)
- Return domain objects (not MCP response dicts)
- Orchestrate core components
- No knowledge of MCP protocol
"""

from abc import ABC
from typing import Any
import logging


class BaseService(ABC):
    """
    Base service with common functionality.

    All nabu services inherit from this class to get:
    - Database manager access
    - Logging infrastructure
    - Common utilities
    """

    def __init__(self, db_manager):
        """
        Initialize service with database manager.

        Args:
            db_manager: KuzuConnectionManager instance
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(self.__class__.__name__)
