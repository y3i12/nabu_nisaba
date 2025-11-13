"""Nabu MCP tools package."""

from nabu.mcp.tools.base import NabuTool

# Import all tool classes for auto-discovery
from nabu.mcp.tools.codebase_management_tools import ActivateCodebaseTool, ListCodebasesTool
from nabu.mcp.tools.observability_tools import ShowStatusTool
from nabu.mcp.tools.query_tool import QueryRelationshipsTool
from nabu.mcp.tools.reindex_tool import RebuildDatabaseTool
from nabu.mcp.tools.search_tools import SearchTool
from nabu.mcp.tools.show_structure_tools import ShowStructureTool
from nabu.mcp.tools.structural_view_tool import StructuralViewTool
from nabu.mcp.tools.vector_search_tools import FindClonesTool
from nabu.mcp.tools.workflow_tools import CheckImpactTool

__all__ = [
    "NabuTool",
    
    "RebuildDatabaseTool",
    
    "QueryRelationshipsTool",
    
    "ShowStatusTool",
    "ShowStructureTool",

    "ActivateCodebaseTool",
    "ListCodebasesTool",
    
    "CheckImpactTool",
    
    "SearchTool",
    "FindClonesTool",
    
    "StructuralViewTool"
]
