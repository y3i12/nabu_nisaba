"""
Centralized registry for shared workspace files.

Provides singleton access to StructuredFileCache instances for workspace
coordination files that appear in Claude's system prompt.
"""

from pathlib import Path
from typing import Optional
from nisaba.structured_file import StructuredFileCache, JsonStructuredFile


class WorkspaceFiles:
    """
    Singleton registry for shared workspace files.

    Manages StructuredFileCache instances for files that are:
    - Written by multiple components (tools, managers, proxy)
    - Read by proxy for system prompt injection
    - Visible in Claude's workspace sections

    Component-private state files are NOT managed here.
    """

    _instance: Optional['WorkspaceFiles'] = None

    def __init__(self):
        """Initialize all shared workspace file caches."""

        # === Workspace Markdown Files (system prompt sections) ===

        self.augments = StructuredFileCache(
            file_path=Path(".nisaba/tui/augment_view.md"),
            name="augments",
            tag="AUGMENTS"
        )

        self.system_prompt = StructuredFileCache(
            file_path=Path(".nisaba/tui/system_prompt.md"),
            name="system prompt",
            tag="USER_SYSTEM_PROMPT_INJECTION"
        )

        self.core_system_prompt = StructuredFileCache(
            file_path=Path(".nisaba/tui/core_system_prompt.md"),
            name="core system prompt",
            tag="CORE_SYSTEM_PROMPT"
        )

        self.structural_view = StructuredFileCache(
            file_path=Path(".nisaba/tui/structural_view.md"),
            name="structural view",
            tag="STRUCTURAL_VIEW"
        )

        self.todos = StructuredFileCache(
            file_path=Path(".nisaba/tui/todo_view.md"),
            name="todos",
            tag="TODOS"
        )

        self.notifications = StructuredFileCache(
            file_path=Path(".nisaba/tui/notification_view.md"),
            name="notifications",
            tag="NOTIFICATIONS"
        )

        self.transcript = StructuredFileCache(
            file_path=Path(".nisaba/tui/compacted_transcript.md"),
            name="transcript",
            tag="COMPACTED_TRANSCRIPT"
        )

        # === Shared JSON State Files ===

        self.notification_state = JsonStructuredFile(
            file_path=Path(".nisaba/tui/notification_state.json"),
            name="notification state",
            default_factory=lambda: {
                "session_id": "",
                "last_tool_id_seen": ""
            }
        )

        self.mcp_servers = JsonStructuredFile(
            file_path=Path(".nisaba/mcp_servers.json"),
            name="mcp servers",
            default_factory=lambda: {
                "version": "1.0",
                "servers": {}
            }
        )

    @classmethod
    def instance(cls) -> 'WorkspaceFiles':
        """
        Get singleton instance.

        Returns:
            Shared WorkspaceFiles instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (primarily for testing)."""
        cls._instance = None
