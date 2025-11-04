"""
Workflow guidance system for MCP tools.

Provides contextual suggestions and redundancy detection based on tool usage patterns.
Configuration-driven approach allows each MCP to define its own guidance behavior.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)


@dataclass
class GuidancePattern:
    """
    A pattern that triggers workflow suggestions.

    Attributes:
        name: Identifier for this pattern
        condition: Function that checks if pattern matches current history
        suggestion: What to do next (tool names, queries, etc.)
        reason: Why this suggestion makes sense
        priority: HIGH, MEDIUM, or LOW
    """
    name: str
    condition: Callable[[List[Dict]], bool]
    suggestion: str
    reason: str
    priority: str = "MEDIUM"

    def matches(self, history: List[Dict]) -> bool:
        """Check if this pattern matches current state."""
        try:
            return self.condition(history)
        except Exception as e:
            logger.warning(f"Pattern '{self.name}' condition failed: {e}")
            return False


@dataclass
class GuidanceGraph:
    """
    Configuration for workflow guidance.

    Defines patterns and redundancy checks that guide tool usage.
    Each MCP can provide its own GuidanceGraph configuration.

    Attributes:
        patterns: List of patterns to check for suggestions
        redundancy_checks: Dict of tool_name -> checker function
    """
    patterns: List[GuidancePattern] = field(default_factory=list)
    redundancy_checks: Dict[str, Callable] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "GuidanceGraph":
        """
        Load configuration from YAML file.

        Future enhancement - allows external configuration.
        """
        raise NotImplementedError("YAML loading not yet implemented")


class WorkflowGuidance:
    """
    Generic workflow guidance system.

    Tracks tool usage and provides contextual suggestions based on
    configurable patterns. Framework-level component that any MCP
    can use by providing a GuidanceGraph configuration.

    This is non-intrusive:
    - Guidance is optional (can be None)
    - Failures don't break tool execution
    - Suggestions returned as metadata, not forced

    Example:
        graph = GuidanceGraph(patterns=[...])
        guidance = WorkflowGuidance(graph)
        guidance.record_tool_call("my_tool", {}, {"success": True})
        suggestions = guidance.get_suggestions()
    """

    def __init__(self, augment_manager=None, guidance_graph: Optional[GuidanceGraph] = None):
        """
        Initialize guidance system.

        Args:
            augment_manager: AugmentManager for augment-based tool associations (primary source)
            guidance_graph: Optional GuidanceGraph for legacy pattern-based guidance
        """
        self.augment_manager = augment_manager
        self.graph = guidance_graph or GuidanceGraph()  # Empty graph as fallback
        self.history: List[Dict[str, Any]] = []
        self.start_time = time.time()

        if augment_manager:
            logger.debug("WorkflowGuidance initialized with augments support")
        else:
            logger.debug("WorkflowGuidance initialized (no augments manager)")

    def record_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """
        Record a tool execution.

        Args:
            tool_name: Name of the tool that was called
            params: Parameters passed to the tool
            result: Result returned by the tool
        """
        entry = {
            "timestamp": time.time(),
            "tool": tool_name,
            "params": params.copy(),  # Copy to avoid mutation
            "result_summary": {
                "success": result.get("success", False),
                "has_data": bool(result.get("data")),
                "error": result.get("error")
            }
        }
        self.history.append(entry)
        logger.debug(f"Recorded tool call: {tool_name} | Total calls: {len(self.history)}")

    def get_suggestions(self) -> Optional[Dict[str, Any]]:
        """
        Get suggestions based on active augments.

        Returns tool associations from active augments only. No algorithmic patterns.
        Returns None if no augments active or no associations found (non-intrusive).

        Returns:
            Dict with suggestion, reason, priority, pattern_name or None
        """
        # Only source of suggestions: active augments
        if self.augment_manager:
            return self._get_augment_based_suggestion()

        return None

    def _get_augment_based_suggestion(self) -> Optional[Dict[str, Any]]:
        """
        Get suggestions based on active augments tool associations.

        Returns:
            Dict with suggestion or None
        """
        if not self.history:
            return None

        last_tool = self.history[-1]['tool']
        related_tools = self.augment_manager.get_related_tools(last_tool)

        if related_tools:
            return {
                "suggestion": f"{', '.join(related_tools)}",
                "reason": f"Tools mentioned with {last_tool}() in active augments",
                "priority": "LOW",
                "pattern_name": "augment_association"
            }

        return None

    def check_redundancy(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if tool call would be redundant.

        Simple exact-match detection in recent history. No custom checkers.
        This is technical safety, not opinionated guidance.

        Args:
            tool_name: Tool about to be called
            params: Parameters for the tool call

        Returns:
            Dict with is_redundant (bool), reason, suggestion
        """
        # Check last 10 calls for exact parameter matches
        for entry in self.history[-10:]:
            if entry["tool"] == tool_name:
                if entry["params"] == params:
                    return {
                        "is_redundant": True,
                        "reason": f"Called {tool_name} with same parameters recently",
                        "suggestion": "Use previous result or modify parameters"
                    }

        return {"is_redundant": False}

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current workflow session.

        Returns:
            Dict with statistics about tool usage
        """
        tool_counts = {}
        for entry in self.history:
            tool = entry["tool"]
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return {
            "total_calls": len(self.history),
            "tool_usage": tool_counts,
            "session_duration_seconds": time.time() - self.start_time,
            "unique_tools_used": len(tool_counts)
        }

    def clear(self) -> None:
        """Reset tracking for new session."""
        logger.debug(f"Clearing guidance session (had {len(self.history)} calls)")
        self.history.clear()
        self.start_time = time.time()
