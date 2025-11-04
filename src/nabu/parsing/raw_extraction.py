"""
Raw AST Extraction

Pure tree-sitter → flat list:
- Uses tree-sitter to parse source files
- Extracts lightweight RawNode data holders
- No relationships or business logic
- Memory efficient (can discard AST nodes after extraction)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

# Tree-sitter imports (same as current implementation)
try:
    from tree_sitter_language_pack import get_parser, get_language
    from tree_sitter import Language, Parser, Node as TSNode
except ImportError:
    raise ImportError("tree-sitter language modules not available. Install with: pip install tree-sitter tree-sitter-python tree-sitter-cpp tree-sitter-java")


@dataclass
class RawNode:
    """
    Data holder from tree-sitter.
    """
    node_type: str              # tree-sitter node type
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    content: str
    file_path: str
    ts_node: TSNode
    children_indices: List[int] = None  # Just indices, not objects
    parent_index: Optional[int] = None

    def __post_init__(self):
        if self.children_indices is None:
            self.children_indices = []


class LanguageParser:
    """
    Pure AST → flat list conversion.

    Uses language_registry for language detection and parser initialization.
    """

    def __init__(self):
        self.parsers: Dict[str, Parser] = {}
        self._initialize_parsers()

    def _initialize_parsers(self) -> None:
        """Initialize tree-sitter parsers for all registered languages."""
        from nabu.language_handlers import language_registry

        try:
            for language in language_registry.get_supported_languages():
                self.parsers[language] = get_parser(language)

        except Exception as e:
            raise RuntimeError(f"Failed to initialize tree-sitter parsers: {e}")

    def detect_language(self, file_path: str) -> Optional[str]:
        """Detect language from file extension using language registry."""
        from nabu.language_handlers import language_registry
        return language_registry.detect_language(file_path)

    def extract_raw_nodes(self, file_path: str) -> List[RawNode]:
        """
        Extract raw nodes from file.

        Returns flat list of RawNode objects with no relationships.
        This is pure data extraction with no business logic.
        """
        language = self.detect_language(file_path)
        if not language or language not in self.parsers:
            raise ValueError(f"Unsupported language for file: {file_path}")

        # Read source file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            raise IOError(f"Failed to read file {file_path}: {e}")

        # Parse with tree-sitter
        parser = self.parsers[language]
        tree = parser.parse(source_code.encode('utf-8'))

        # Extract raw nodes
        raw_nodes: List[RawNode] = []
        source_lines = source_code.split('\n')

        def visit_node(ts_node: TSNode, parent_idx: Optional[int] = None) -> int:
            """Recursively visit tree-sitter nodes."""
            current_idx = len(raw_nodes)

            # Extract content (convert tree-sitter 0-indexed to 1-indexed for storage)
            start_line = ts_node.start_point[0] + 1
            end_line = ts_node.end_point[0] + 1
            content = self._extract_node_content(ts_node, source_lines)

            # Create raw node
            raw_node = RawNode(
                node_type=ts_node.type,
                start_line=start_line,
                end_line=end_line,
                start_byte=ts_node.start_byte,
                end_byte=ts_node.end_byte,
                content=content,
                file_path=file_path,
                parent_index=parent_idx,
                ts_node=ts_node
            )

            raw_nodes.append(raw_node)

            # Process children
            for child in ts_node.children:
                child_idx = visit_node(child, current_idx)
                raw_node.children_indices.append(child_idx)

            return current_idx

        # Start extraction from root
        visit_node(tree.root_node)
        return raw_nodes

    def _extract_node_content(self, ts_node: TSNode, source_lines: List[str]) -> str:
        """
        Extract the source code content for a node.

        Handles multi-line nodes properly.
        """
        start_line = ts_node.start_point[0]
        end_line = ts_node.end_point[0]
        start_col = ts_node.start_point[1]
        end_col = ts_node.end_point[1]

        if start_line == end_line:
            # Single line
            if start_line < len(source_lines):
                line = source_lines[start_line]
                return line[start_col:end_col]
        else:
            # Multi-line
            lines = []
            for line_idx in range(start_line, min(end_line + 1, len(source_lines))):
                line = source_lines[line_idx]
                if line_idx == start_line:
                    lines.append(line[start_col:])
                elif line_idx == end_line:
                    lines.append(line[:end_col])
                else:
                    lines.append(line)
            return '\n'.join(lines)

        return ""

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions from language registry."""
        from nabu.language_handlers import language_registry
        return language_registry.get_all_extensions()

    def discover_source_files(self, root_path: str, file_filter: Optional['FileFilter'] = None) -> List[str]:
        """
        Discover source files in directory tree.

        Args:
            root_path: Root directory to search
            file_filter: Optional FileFilter to exclude files (e.g., .venv, node_modules)
                        If None, no filtering is applied (backwards compatible)
        
        Returns:
            Sorted list of file paths matching extensions and filter criteria
        """
        from nabu.language_handlers import language_registry

        source_files = []
        root = Path(root_path)

        for extension in language_registry.get_all_extensions():
            pattern = f"**/*{extension}"
            files = root.glob(pattern)
            for f in files:
                if not f.is_file():
                    continue
                
                file_path_str = str(f)
                
                # Apply filter if provided
                if file_filter and not file_filter.should_watch(file_path_str):
                    continue
                
                source_files.append(file_path_str)

        return sorted(source_files)