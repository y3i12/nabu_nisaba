"""
Usage:
    from nabu import CodebaseParser

    parser = CodebaseParser()
    codebase_frame, edges = parser.parse_codebase("/path/to/code")

    # Export to KuzuDB
    parser.export_to_kuzu(codebase_frame, edges, "analysis.db")
"""

from nabu.main import CodebaseParser
from nabu.core import (
    FrameNodeType, EdgeType, ConfidenceTier,
    AstFrameBase, AstEdge
)
from nabu.parsing import MultiPassParser
from nabu.exporter import KuzuDbExporter

__version__ = "3.0.0-dev"

__all__ = [
    'CodebaseParser',
    'FrameNodeType',
    'EdgeType',
    'ConfidenceTier',
    'AstFrameBase',
    'AstEdge',
    'MultiPassParser',
    'KuzuDbExporter'
]