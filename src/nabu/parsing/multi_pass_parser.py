"""
Multi-Pass Parser

Orchestrates the three-phase processing pipeline

This is the main entry point that coordinates:
1. Raw AST Extraction
2. Semantic Frame Creation
3. Symbol Resolution

Implements graceful degradation and confidence-based parsing.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path

from nabu.parsing.raw_extraction import LanguageParser, RawNode
from nabu.parsing.graph_builder import GraphBuilder
from nabu.parsing.symbol_resolver import SymbolResolver
from nabu.core.frames import AstFrameBase, AstEdge
from nabu.core.frame_types import FrameNodeType
from nabu.core.confidence import ConfidenceContext


logger = logging.getLogger(__name__)


class MultiPassParser:
    """
    Main parser orchestrating the three-phase pipeline.
    """

    def __init__(self, extra_ignore_patterns: Optional[List[str]] = None):
        from nabu.core.codebase_context import CodebaseContext
        
        # Create shared context for all parsing components
        self.context = CodebaseContext()
        
        # Store extra ignore patterns for file filtering
        self.extra_ignore_patterns = extra_ignore_patterns or []
        
        # Initialize parsing components with shared context
        self.language_parser = LanguageParser()
        self.graph_builder = GraphBuilder(self.context)
        self.symbol_resolver = SymbolResolver(self.context)  # Track edges from GraphBuilder  # Track edges from GraphBuilder

    def parse_codebase(self, codebase_path: str) -> tuple[AstFrameBase, List[AstEdge]]:
        """
        Main entry point for parsing entire codebase.
        """
        logger.info(f"Starting multi-pass parsing of codebase: {codebase_path}")

        try:
            # Phase 1: Structure Discovery (confidence = 1.0)
            logger.info("Phase 1: Raw AST extraction")
            self.context.confidence_context.set_pass(1)
            raw_nodes_by_file = self._extract_raw_structure(codebase_path)

            # Phase 2: Frame Hierarchy Creation (confidence = 1.0 for parsed, 0.6-0.9 for inferred)
            logger.info("Phase 2: Semantic frame creation")
            self.context.confidence_context.set_pass(2)
            codebase_frame = self._build_frame_hierarchy(codebase_path, raw_nodes_by_file)

            # Phase 3: Symbol Resolution (confidence = 0.3-0.9)
            logger.info("Phase 3: Symbol resolution")
            self.context.confidence_context.set_pass(3)
            edges = self._resolve_symbols(codebase_frame)

            # Phase 4: Additional processing could go here
            # self.context.confidence_context.set_pass(4)
            # self._fuzzy_resolve_unknowns(codebase_frame)

            logger.info(f"Parsing completed. Created {self._count_frames(codebase_frame)} frames and {len(edges)} edges")
            return codebase_frame, edges

        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            # Graceful degradation - create minimal codebase frame
            return self._create_minimal_codebase(codebase_path), []

    def _extract_raw_structure(self, codebase_path: str) -> Dict[str, List[RawNode]]:
        """
        Extract raw AST structure from all source files.
        Returns mapping of file_path -> List[RawNode].
        
        Uses FileFilter to exclude files based on gitignore-style patterns.
        """
        from nabu.file_watcher.filters import FileFilter
        from nabu.language_handlers import language_registry
        
        # Create file filter with default ignores + repository .gitignore + extra patterns
        ignore_patterns = FileFilter.default_ignores()
        repo_gitignore_patterns = self._load_gitignore_patterns(codebase_path)
        if repo_gitignore_patterns:
            ignore_patterns.extend(repo_gitignore_patterns)
            logger.debug(f"Loaded {len(repo_gitignore_patterns)} patterns from .gitignore")
        
        # Add extra patterns from config
        if self.extra_ignore_patterns:
            ignore_patterns.extend(self.extra_ignore_patterns)
            logger.debug(f"Added {len(self.extra_ignore_patterns)} extra ignore patterns from config")
        
        # Get watched extensions from language registry
        watch_extensions = language_registry.get_all_extensions()
        
        file_filter = FileFilter(
            ignore_patterns=ignore_patterns,
            watch_extensions=watch_extensions,
            codebase_path=Path(codebase_path)
        )
        
        # Discover source files with filtering
        source_files = self.language_parser.discover_source_files(codebase_path, file_filter)
        logger.info(f"Discovered {len(source_files)} source files (after filtering)")
        
        raw_nodes_by_file = {}

        for file_path in source_files:
            try:
                raw_nodes = self.language_parser.extract_raw_nodes(file_path)
                raw_nodes_by_file[file_path] = raw_nodes
                logger.debug(f"Extracted {len(raw_nodes)} raw nodes from {file_path}")

            except Exception as e:
                logger.warning(f"Failed to extract raw nodes from {file_path}: {e}")
                # Continue with other files - graceful degradation
                continue

        logger.info(f"Phase 1 completed: extracted raw nodes from {len(raw_nodes_by_file)} files")
        return raw_nodes_by_file

    def _load_gitignore_patterns(self, codebase_path: str) -> List[str]:
        """
        Load gitignore patterns from repository's .gitignore file.
        
        Args:
            codebase_path: Root directory of codebase
            
        Returns:
            List of gitignore patterns, or empty list if .gitignore not found
        """
        gitignore_path = Path(codebase_path) / ".gitignore"
        
        if not gitignore_path.exists():
            return []
        
        try:
            patterns = []
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        patterns.append(line)
            return patterns
        except Exception as e:
            logger.warning(f"Failed to load .gitignore from {gitignore_path}: {e}")
            return []

    def _build_frame_hierarchy(self, codebase_path: str, raw_nodes_by_file: Dict[str, List[RawNode]]) -> AstFrameBase:
        """
        Phase 2: Build semantic frame hierarchy.

        Creates proper CODEBASE → LANGUAGE → (FILE/PACKAGE) → CLASS structure.
        """
        try:
            codebase_frame = self.graph_builder.build_codebase_graph(codebase_path, raw_nodes_by_file)

            # Collect edges from GraphBuilder's FrameStack
            self.context.hierarchy_edges = self.graph_builder.get_all_edges()

            frame_count = self._count_frames(codebase_frame)
            edge_count = len(self.context.hierarchy_edges)
            logger.info(f"Phase 2 completed: built frame hierarchy with {frame_count} frames and {edge_count} edges")
            return codebase_frame

        except Exception as e:
            logger.error(f"Frame hierarchy building failed: {e}")
            return self._create_minimal_codebase(codebase_path)

    def _resolve_symbols(self, codebase_frame: AstFrameBase) -> List[AstEdge]:
        """
        Phase 3: Resolve cross-references and create edges.

        Implements confidence-based symbol resolution.
        """
        try:
            symbol_edges = self.symbol_resolver.resolve_references(codebase_frame)

            # Combine hierarchy edges from GraphBuilder with symbol edges
            all_edges = self.context.hierarchy_edges + symbol_edges

            hierarchy_count = len(self.context.hierarchy_edges)
            symbol_count = len(symbol_edges)
            total_count = len(all_edges)

            logger.info(f"Phase 3 completed: {hierarchy_count} hierarchy edges + {symbol_count} symbol edges = {total_count} total edges")
            return all_edges

        except Exception as e:
            logger.error(f"Symbol resolution failed: {e}")
            # Return at least the hierarchy edges if symbol resolution fails
            return self.context.hierarchy_edges

    def _create_minimal_codebase(self, codebase_path: str) -> AstFrameBase:
        """
        Create minimal codebase frame for graceful degradation.
        """
        from nabu.core.frames import AstCodebaseFrame

        codebase_name = Path(codebase_path).name
        from nabu.core.frame_types import FrameNodeType
        return AstCodebaseFrame(
            id=0,
            type=FrameNodeType.CODEBASE,
            name=codebase_name,
            qualified_name=codebase_name,
            confidence=0.1,
            provenance="parse_failed",
            metadata={'error': 'Parsing failed, created minimal frame'}
        )

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

    # Convenience methods for Phase-by-Phase parsing (for testing/debugging)

    def parse_single_file(self, file_path: str) -> tuple[AstFrameBase, List[AstEdge]]:
        """
        Parse a single file for testing.

        Creates minimal codebase → language → file hierarchy.
        """
        # Create minimal hierarchy for single file
        raw_nodes = self.language_parser.extract_raw_nodes(file_path)
        raw_nodes_by_file = {file_path: raw_nodes}

        # Use parent directory as codebase
        codebase_path = str(Path(file_path).parent)
        codebase_frame = self._build_frame_hierarchy(codebase_path, raw_nodes_by_file)
        edges = self._resolve_symbols(codebase_frame)

        # Set file_path for CODEBASE and LANGUAGE frames for incremental update tracking
        # This ensures they can be queried by file_path in the database
        # Note: We set file_path AFTER compute_id() was called, so IDs remain stable
        absolute_file_path = str(Path(file_path).resolve())
        codebase_frame.file_path = absolute_file_path
        for language_frame in codebase_frame.find_children_by_type(FrameNodeType.LANGUAGE):
            language_frame.file_path = absolute_file_path

        return codebase_frame, edges

    def get_statistics(self, codebase_frame: AstFrameBase, edges: List[AstEdge]) -> Dict[str, any]:
        """
        Get parsing statistics.
        """
        stats = {
            'total_frames': self._count_frames(codebase_frame),
            'total_edges': len(edges),
            'languages': [],
            'frame_types': {},
            'edge_types': {},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0, 'speculative': 0}
        }

        # Collect frame statistics
        self._collect_frame_stats(codebase_frame, stats)

        # Collect edge statistics
        for edge in edges:
            edge_type = edge.type.value
            stats['types'][edge_type] = stats['edge_types'].get(edge_type, 0) + 1

            # Confidence distribution for edges
            tier = edge.confidence_tier.value.lower()
            stats['confidence_distribution'][tier] += 1

        return stats

    def _collect_frame_stats(self, frame: AstFrameBase, stats: Dict[str, any], visited: set = None) -> None:
        """Recursively collect frame statistics with cycle detection."""
        if visited is None:
            visited = set()
            
        # Prevent infinite recursion in multi-parent graphs
        if frame.id in visited:
            return
        visited.add(frame.id)
        
        # Frame type distribution
        frame_type = frame.type.value
        stats['frame_types'][frame_type] = stats['frame_types'].get(frame_type, 0) + 1

        # Language detection
        if frame.language and frame.language not in stats['languages']:
            stats['languages'].append(frame.language)

        # Confidence distribution for frames
        tier = frame.confidence_tier.value.lower()
        if tier in stats['confidence_distribution']:
            stats['confidence_distribution'][tier] += 1

        # Recurse to children
        for child in frame.children:
            self._collect_frame_stats(child, stats, visited)
