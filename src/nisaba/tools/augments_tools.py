"""
MCP tools for augments management.

Provides tools to show, activate, deactivate, and learn augments for dynamic
context management in Claude Code.
"""

from typing import Dict, Any, List
from nisaba import BaseTool, BaseToolResponse

class AugmentTool(BaseTool):
    @property
    def augment_manager(self):
        """
        Access to AugmentManager (if factory has one).

        Returns None if factory doesn't implement augments support.

        Returns:
            AugmentManager instance or None
        """
        return getattr(self.factory, 'augment_manager', None)
    
    @property
    def augment_manager_not_present_error(self) -> BaseToolResponse:
        return self.response(success=False, message="ConfigurationError: Augments system not initialized",nisaba=True)
    
    def _augment_result_append_key(self, result:dict[str,Any], key:str, message_list:list[str]) -> list[str]:
        if key in result:
            message_list.append(f"{key} [{', '.join(result[key])}]")
        return message_list

    def augment_manager_result_response(self, result:dict[str,Any]) -> BaseToolResponse:
        message_list:list[str] = []
        for key in ('affected', 'dependencies', 'skipped'):
            message_list = self._augment_result_append_key(result, key, message_list)

        message = ', '.join(message_list)
        return self.response(success=True, message=message, nisaba=True)


class ActivateAugmentsTool(AugmentTool):
    """Activate augments by pattern (supports wildcards and exclusions)."""

    async def execute(self, patterns: List[str], exclude: List[str] = []) -> BaseToolResponse:
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
            augments affected and dependencies
        """
        try:
            if not self.augment_manager:
                return self.augment_manager_not_present_error
            return self.augment_manager_result_response(self.augment_manager.activate_augments(patterns, exclude))
        
        except Exception as e:
            return self.response_exception(e, "Failed to activate augment", nisaba=True)


class DeactivateAugmentsTool(AugmentTool):
    """Deactivate augments by pattern."""

    async def execute(self, patterns: List[str]) -> BaseToolResponse:
        """
        Deactivate augments matching patterns.

        Removes augments from active set and updates composed file.
        Useful for switching context or reducing active context size.

        :meta pitch: Unload augments to switch context or reduce token usage
        :meta when: Use when switching from one task type to another

        Args:
            patterns: Patterns to match for deactivation

        Returns:
            augments affected and skipped (pinned)
        """
        try:
            if not self.augment_manager:
                return self.augment_manager_not_present_error

            return self.augment_manager_result_response(self.augment_manager.deactivate_augments(patterns))
        
        except Exception as e:
            return self.response_exception(e, "Failed to deactivate augment", nisaba=True)


class PinAugmentTool(AugmentTool):
    """Pin augments by pattern (always active, cannot be deactivated)."""

    async def execute(self, patterns: List[str]) -> BaseToolResponse:
        """
        Pin augments matching patterns.

        Pinned augments are always active and cannot be deactivated. Useful for
        core workflow augments that should always be available.

        :meta pitch: Pin core augments to keep them always active
        :meta when: Use for foundational workflows (navigation, windows) that should persist

        Args:
            patterns: List of patterns to match

        Returns:
            augments affected
        """
        try:
            if not self.augment_manager:
                return self.augment_manager_not_present_error

            return self.augment_manager_result_response(self.augment_manager.pin_augment(patterns))
        
        except Exception as e:
            return self.response_exception(e, "Failed to pin augment", nisaba=True)


class UnpinAugmentTool(AugmentTool):
    """Unpin augments by pattern (allows deactivation)."""

    async def execute(self, patterns: List[str]) -> BaseToolResponse:
        """
        Unpin augments matching patterns.

        Removes pin protection, allowing augments to be deactivated.
        Does not deactivate the augments, just removes pin protection.

        :meta pitch: Remove pin protection from augments
        :meta when: Use when augment no longer needs to be always active

        Args:
            patterns: List of patterns to match

        Returns:
            augments affected
        """
        try:
            if not self.augment_manager:
                return self.augment_manager_not_present_error

            return self.augment_manager_result_response(self.augment_manager.unpin_augment(patterns))
        except Exception as e:
            return self.response_exception(e, "Failed to unpin augment", nisaba=True)

class LearnAugmentTool(AugmentTool):
    """Create a new augment."""

    async def execute(self, group: str, name: str, content: str) -> BaseToolResponse:
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
            augments affected
        """
        try:
            if not self.augment_manager:
                return self.augment_manager_not_present_error

            return self.augment_manager_result_response(self.augment_manager.learn_augment(group, name, content))
        except Exception as e:
            return self.response_exception(e, "Failed to create augment", nisaba=True)
