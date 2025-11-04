"""
MCP tools for augments management.

Provides tools to show, activate, deactivate, and learn augments for dynamic
context management in Claude Code.
"""

from typing import Dict, Any, List
from nisaba.tools.base import NisabaTool


class ActivateAugmentsTool(NisabaTool):
    """Activate augments by pattern (supports wildcards and exclusions)."""

    async def execute(self, patterns: List[str], exclude: List[str] = []) -> Dict[str, Any]:
        """
        Activate augments matching patterns.

        Supports wildcards: "group/*" (all in group), "group/augment", "*" (all augments).
        Automatically resolves dependencies and updates composed file.

        :meta pitch: Load context-specific workflows dynamically
        :meta when: Use when starting task-specific work (analysis, refactoring, debugging)

        Args:
            patterns: List of patterns to match
            exclude: Patterns to exclude

        Returns:
            Dict with 'loaded', 'dependencies', 'failed' lists
        """
        try:
            if not self.augment_manager:
                return {
                    "success": False,
                    "error": "Augments system not initialized",
                    "error_type": "ConfigurationError"
                }

            result = self.augment_manager.activate_augments(patterns, exclude)
            return {"success": True, "data": result}
        except Exception as e:
            self.logger.error(f"Failed to activate augments: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}


class DeactivateAugmentsTool(NisabaTool):
    """Deactivate augments by pattern."""

    async def execute(self, patterns: List[str]) -> Dict[str, Any]:
        """
        Deactivate augments matching patterns.

        Removes augments from active set and updates composed file.
        Useful for switching context or reducing active context size.

        :meta pitch: Unload augments to switch context or reduce token usage
        :meta when: Use when switching from one task type to another

        Args:
            patterns: Patterns to match for deactivation

        Returns:
            Dict with 'unloaded' list
        """
        try:
            if not self.augment_manager:
                return {
                    "success": False,
                    "error": "Augments system not initialized",
                    "error_type": "ConfigurationError"
                }

            result = self.augment_manager.deactivate_augments(patterns)
            return {"success": True, "data": result}
        except Exception as e:
            self.logger.error(f"Failed to deactivate augments: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}


class PinAugmentTool(NisabaTool):
    """Pin augments by pattern (always active, cannot be deactivated)."""

    async def execute(self, patterns: List[str]) -> Dict[str, Any]:
        """
        Pin augments matching patterns.

        Pinned augments are always active and cannot be deactivated. Useful for
        core workflow augments that should always be available.

        :meta pitch: Pin core augments to keep them always active
        :meta when: Use for foundational workflows (navigation, windows) that should persist

        Args:
            patterns: List of patterns to match

        Returns:
            Dict with 'pinned' list
        """
        try:
            if not self.augment_manager:
                return {
                    "success": False,
                    "error": "Augments system not initialized",
                    "error_type": "ConfigurationError"
                }

            result = self.augment_manager.pin_augment(patterns)
            return {"success": True, "data": result}
        except Exception as e:
            self.logger.error(f"Failed to pin augments: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}


class UnpinAugmentTool(NisabaTool):
    """Unpin augments by pattern (allows deactivation)."""

    async def execute(self, patterns: List[str]) -> Dict[str, Any]:
        """
        Unpin augments matching patterns.

        Removes pin protection, allowing augments to be deactivated.
        Does not deactivate the augments, just removes pin protection.

        :meta pitch: Remove pin protection from augments
        :meta when: Use when augment no longer needs to be always active

        Args:
            patterns: List of patterns to match

        Returns:
            Dict with 'unpinned' list
        """
        try:
            if not self.augment_manager:
                return {
                    "success": False,
                    "error": "Augments system not initialized",
                    "error_type": "ConfigurationError"
                }

            result = self.augment_manager.unpin_augment(patterns)
            return {"success": True, "data": result}
        except Exception as e:
            self.logger.error(f"Failed to unpin augments: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}


class LearnAugmentTool(NisabaTool):
    """Create a new augment."""

    async def execute(self, group: str, name: str, content: str) -> Dict[str, Any]:
        """
        Create a new augment and save it to the augments directory.

        Augment content should include TOOLS and optionally REQUIRES sections.

        :meta pitch: Create new augments to capture workflows and knowledge
        :meta when: Use when discovering useful patterns worth preserving

        Args:
            group: Augment group/category (e.g., 'code_analysis')
            name: Augment name (e.g., 'find_circular_deps')
            content: Augment content in markdown format

        Returns:
            Dict with 'path' and 'file_path'
        """
        try:
            if not self.augment_manager:
                return {
                    "success": False,
                    "error": "Augments system not initialized",
                    "error_type": "ConfigurationError"
                }

            result = self.augment_manager.learn_augment(group, name, content)
            return {"success": True, "data": result}
        except Exception as e:
            self.logger.error(f"Failed to create augment: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}
