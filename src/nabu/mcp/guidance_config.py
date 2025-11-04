"""
Nabu guidance configuration.

Augments-based guidance system - contextual suggestions come from active augments,
not hardcoded patterns. See augments system for dynamic context management.
"""

from nisaba.guidance import GuidanceGraph

# Empty guidance graph - all suggestions come from augments
NABU_GUIDANCE_GRAPH = GuidanceGraph()
