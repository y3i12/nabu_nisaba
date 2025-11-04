"""
Main Entry Point for Nabu

Usage:
    parser = CodebaseParser()
    codebase_frame, edges = parser.parse_codebase("/path/to/code")
    parser.export_to_kuzu(codebase_frame, edges, "analysis.db")
"""

import logging
from typing import Tuple, List, Dict, Any, Optional
from pathlib import Path

from nabu.core.frames import AstFrameBase, AstEdge
from nabu.parsing.multi_pass_parser import MultiPassParser
from nabu.exporter.kuzu_exporter import KuzuDbExporter


logger = logging.getLogger(__name__)


class CodebaseParser:
    """
    Main entry point for parsing codebases.
    """

    def __init__(self, extra_ignore_patterns: Optional[List[str]] = None):
        self.parser = MultiPassParser(extra_ignore_patterns=extra_ignore_patterns)
        self.exporter = KuzuDbExporter()

    def parse_codebase(self, codebase_path: str) -> Tuple[AstFrameBase, List[AstEdge]]:
        """
        Parse entire codebase and return frame hierarchy + edges.

        This is the main method that orchestrates the three-phase pipeline:
        1. Raw AST Extraction
        2. Semantic Frame Creation
        3. Symbol Resolution
        """
        logger.info(f"Parsing codebase: {codebase_path}")

        if not Path(codebase_path).exists():
            raise FileNotFoundError(f"Codebase path does not exist: {codebase_path}")

        # Execute multi-pass parsing
        codebase_frame, edges = self.parser.parse_codebase(codebase_path)

        logger.info(f"Parsing completed: {self._count_frames(codebase_frame)} frames, {len(edges)} edges")
        return codebase_frame, edges

    def parse_single_file(self, file_path: str) -> Tuple[AstFrameBase, List[AstEdge]]:
        """
        Parse a single file for testing or incremental parsing.

        Creates minimal codebase → language → file hierarchy.
        """
        logger.info(f"Parsing single file: {file_path}")
        return self.parser.parse_single_file(file_path)

    def export_to_kuzu(
        self,
        codebase_frame: AstFrameBase,
        edges: List[AstEdge],
        db_path: str
    ) -> None:
        """
        Export parsed codebase to KuzuDB.

        Based on the working export from current implementation.
        Passes parser context to exporter for registry-based frame collection.
        """
        logger.info(f"Exporting to KuzuDB: {db_path}")
        # Pass context to enable registry-based export (fixes 89% frame loss bug)
        self.exporter.create_database(codebase_frame, edges, db_path, context=self.parser.context)

    def get_parsing_statistics(
        self,
        codebase_frame: AstFrameBase,
        edges: List[AstEdge]
    ) -> Dict[str, Any]:
        """
        Get detailed parsing statistics.

        Useful for debugging and performance analysis.
        """
        return self.parser.get_statistics(codebase_frame, edges)

    def _count_frames(self, codebase_frame: AstFrameBase) -> int:
        """
        Count total UNIQUE frames in hierarchy.
        
        CRITICAL: Uses visited set to avoid counting frames multiple times
        in multi-parent graphs where a frame can appear as child of multiple parents.
        """
        visited = set()
        
        def count_unique(frame: AstFrameBase) -> int:
            if frame.id in visited:
                return 0  # Already counted
            visited.add(frame.id)
            return 1 + sum(count_unique(child) for child in frame.children)
        
        return count_unique(codebase_frame)

    # Convenience methods for common workflows

    def _collect_structural_info(self, frame: AstFrameBase, analysis: Dict[str, Any]) -> None:
        """Collect structural information for analysis."""
        from .core.frame_types import FrameNodeType

        if frame.type == FrameNodeType.LANGUAGE and frame.language:
            if frame.language not in analysis['languages']:
                analysis['languages'].append(frame.language)

        elif frame.type == FrameNodeType.PACKAGE and frame.qualified_name:
            analysis['packages'].append(frame.qualified_name)

        elif frame.type == FrameNodeType.CLASS and frame.qualified_name:
            analysis['classes'].append(frame.qualified_name)



        # Recurse to children
        for child in frame.children:
            self._collect_structural_info(child, analysis)


# Convenience function for direct usage
def parse_codebase(
    codebase_path: str, 
    output_db: Optional[str] = None,
    extra_ignore_patterns: Optional[List[str]] = None
) -> Tuple[AstFrameBase, List[AstEdge]]:
    """
    Convenience function for direct codebase parsing.

    Args:
        codebase_path: Path to codebase root directory
        output_db: Optional path to export database
        extra_ignore_patterns: Additional gitignore-style patterns to exclude files
    
    Example:
        from nabu import parse_codebase
        codebase, edges = parse_codebase("/path/to/code", "analysis.db")
    """
    parser = CodebaseParser(extra_ignore_patterns=extra_ignore_patterns)
    codebase_frame, edges = parser.parse_codebase(codebase_path)

    if output_db:
        parser.export_to_kuzu(codebase_frame, edges, output_db)

    return codebase_frame, edges