from typing import List, Dict, Optional
from pathlib import Path
import logging

from nabu.parsing.raw_extraction import RawNode
from nabu.core.frames import (
    AstFrameBase, AstCodebaseFrame, AstLanguageFrame, AstPackageFrame,
    AstClassFrame, AstCallableFrame, AstEdge
)
from nabu.core.frame_types import FrameNodeType, EdgeType
from nabu.core.frame_stack import FrameStack
from nabu.core.confidence import ConfidenceCalculator
from nabu.core.registry import FrameRegistry
from nabu.language_handlers import language_registry


class GraphBuilder:
    """
    Converts raw nodes to semantic frames.
    """

    def _get_frame_mappings(self, language: str) -> Dict[str, FrameNodeType]:
        """
        Get frame mappings for a specific language from the language handler.

        Args:
            language: Language name (python, cpp, java, perl)

        Returns:
            Dictionary mapping tree-sitter node types to FrameNodeType
        """
        handler = language_registry.get_handler(language)
        if handler:
            return handler.get_frame_mappings()

        # Fallback to empty dict if no handler found
        logging.getLogger(__name__).warning(f"No handler found for language: {language}")
        return {}

    def __init__(self, context: 'CodebaseContext'):
        """
        Initialize GraphBuilder with shared CodebaseContext.
        
        Args:
            context: Shared context containing registries, frame_stack, etc.
        """
        from nabu.core.codebase_context import CodebaseContext
        
        self.context = context

    def build_codebase_graph(self, root_path: str, file_raw_nodes: Dict[str, List[RawNode]]) -> AstFrameBase:
        """
        Build complete codebase graph.

        Creates the proper hierarchy: CODEBASE → LANGUAGE → (FILE/PACKAGE) → CLASS
        Addresses missing language root frames from current implementation.
        """
        # Create root codebase frame
        codebase_name = Path(root_path).name
        codebase_frame = AstCodebaseFrame(
            id="temp",  # Temporary - will be computed immediately
            type=FrameNodeType.CODEBASE,
            name=codebase_name,
            qualified_name=codebase_name,
            confidence=1.0,
            provenance="parsed"
        )
        
        # Compute ID immediately so edges can reference it
        codebase_frame.compute_id()

        # Store root path for relative path calculation
        self.context.codebase_root = root_path

        # Initialize frame stack with codebase
        self.context.initialize_frame_stack(codebase_frame)

        # Group files by language
        language_files = self._group_files_by_language(file_raw_nodes)

        # Create language root frames
        for language, files in language_files.items():
            # Reuse existing language frame or create new one
            if language not in self.context.language_frames:
                language_frame = self._create_language_frame(language, codebase_frame)
                self.context.language_frames[language] = language_frame
                # Initialize registry for this language
                self.context.registries[language] = FrameRegistry(language_frame)
            else:
                language_frame = self.context.language_frames[language]

            with self.context.frame_stack.language_context(language_frame):
                # Process all files for this language
                for file_path, raw_nodes in files.items():
                    # Check if file already processed
                    if file_path not in self.context.processed_files:
                        self._build_file_hierarchy(file_path, raw_nodes, language, language_frame)
                        self.context.processed_files.add(file_path)

        # Collect all edges created during the process
        all_edges = self.get_all_edges()

        return codebase_frame

    def _group_files_by_language(self, file_raw_nodes: Dict[str, List[RawNode]]) -> Dict[str, Dict[str, List[RawNode]]]:
        """Group files by detected language."""
        from .raw_extraction import LanguageParser

        language_files = {}
        parser = LanguageParser()

        for file_path, raw_nodes in file_raw_nodes.items():
            language = parser.detect_language(file_path)
            if language:
                if language not in language_files:
                    language_files[language] = {}
                language_files[language][file_path] = raw_nodes

        return language_files

    def _create_language_frame(self, language: str, codebase_frame: AstFrameBase) -> AstLanguageFrame:
        """
        Create language root frame.

        Checks for existing language frame to avoid duplicates.
        """
        language_name = f"{language}_root"

        # Check if language frame already exists
        existing_language_frame = codebase_frame.find_child_by_name(language_name)
        if existing_language_frame and existing_language_frame.type == FrameNodeType.LANGUAGE:
            return existing_language_frame

        # Create new language frame
        language_frame = AstLanguageFrame(
            id="temp",  # Temporary - will be computed immediately
            type=FrameNodeType.LANGUAGE,
            name=language_name,
            qualified_name=f"{codebase_frame.qualified_name}.{language_name}",
            language=language,
            confidence=1.0,
            provenance="parsed"
        )
        
        # Compute ID immediately so edges can reference it
        language_frame.compute_id()

        codebase_frame.add_child(language_frame)
        
        # Create CODEBASE→LANGUAGE edge for database export
        edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
            EdgeType.CONTAINS, codebase_frame.confidence, language_frame.confidence
        )
        self.context.frame_stack._create_edge(
            codebase_frame, language_frame, EdgeType.CONTAINS, edge_confidence
        )
        
        return language_frame

    def _build_file_hierarchy(
        self,
        file_path: str,
        raw_nodes: List[RawNode],
        language: str,
        language_frame: AstLanguageFrame
    ) -> None:
        """
        Build hierarchy for a single file.

        Creates package frames based on file path, then processes nodes.
        Children become direct descendants of PACKAGE or LANGUAGE (no FILE frame).
        """
        # Track this file as processed
        self.context.processed_files.add(file_path)

        # Create package hierarchy from file path
        package_frame = self._create_package_hierarchy(file_path, language_frame, language)

        # Push package context if one exists
        # If no package, we're already in language_frame context (from language_context())
        # so no need to push again
        if package_frame:
            with self.context.frame_stack.push_context(package_frame):
                self._process_raw_nodes(raw_nodes, language)
        else:
            # No package - process nodes directly in current context (language_frame)
            # Don't push language_frame again to avoid duplicate LANGUAGE on stack
            self._process_raw_nodes(raw_nodes, language)


    def _create_package_hierarchy(
        self,
        file_path: str,
        language_frame: AstLanguageFrame,
        language: str
    ) -> Optional[AstPackageFrame]:
        """
        Create package hierarchy from file path using language handler.

        Args:
            file_path: Path to source file
            language_frame: Language frame to attach packages to
            language: Programming language

        Returns:
            Deepest package frame in hierarchy or None
        """
        handler = language_registry.get_handler(language)
        if not handler:
            logging.getLogger(__name__).warning(f"No handler found for language: {language}")
            return None

        # Get package parts from handler
        package_parts = handler.extract_package_hierarchy_from_path(
            file_path,
            self.context.codebase_root
        )

        if not package_parts:
            return None

        # Language handlers return parts in correct order (base to leaf)
        # e.g., ['com', 'example', 'utils'] for com.example.utils
        # No reversal needed!

        # Create package hierarchy with registry-based deduplication
        current_frame = language_frame

        for part in package_parts:
            # Build qualified name for this package
            qualified_name = f"{current_frame.qualified_name}{handler.get_separator()}{part}"

            # Use package registry as single source of truth
            existing = self.context.package_registry.get(qualified_name)

            if existing and existing.type == FrameNodeType.PACKAGE:
                # Reuse existing package - only add parent relationship if it doesn't exist
                # This prevents duplicate CONTAINS edges from language_root to all packages
                if existing not in current_frame.children:
                    current_frame.add_child(existing)

                    # Create CONTAINS edge for parent→package relationship
                    edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
                        EdgeType.CONTAINS, current_frame.confidence, existing.confidence
                    )
                    self.context.frame_stack._create_edge(
                        current_frame, existing, EdgeType.CONTAINS, edge_confidence
                    )

                current_frame = existing
            else:
                package_frame = AstPackageFrame(
                    id="temp",  # Temporary - will be computed
                    type=FrameNodeType.PACKAGE,
                    name=part,
                    qualified_name=qualified_name,
                    language=language_frame.language,
                    confidence=1.0,
                    provenance="parsed",
                    file_path=file_path,  # Associate with source file
                    start_line=0,  # Package spans entire file
                    end_line=0,
                    start_byte=0,
                    end_byte=0
                )
                
                # Compute stable ID
                package_frame.compute_id()

                # Register first, then add to parent
                self.context.package_registry[qualified_name] = package_frame
                current_frame.add_child(package_frame)

                # Create CONTAINS edge for parent→package relationship
                edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
                    EdgeType.CONTAINS, current_frame.confidence, package_frame.confidence
                )
                self.context.frame_stack._create_edge(
                    current_frame, package_frame, EdgeType.CONTAINS, edge_confidence
                )

                current_frame = package_frame

        return current_frame

    def get_all_edges(self) -> List[AstEdge]:
        """
        Collect all edges created during graph building.

        This addresses the issue where 0 edges were being returned.
        FrameStack creates CONTAINS edges but they weren't being collected.
        """
        return self.context.frame_stack.edges.copy()

    def _process_raw_nodes(self, nodes_to_process: List[RawNode], language: str, all_raw_nodes: List[RawNode] = None, processed_indices: set = None, _depth: int = 0) -> None:
        """
        Process raw nodes and create semantic frames.

        This is where the business logic happens - determining which raw nodes
        should become frames based on FRAME_MAPPINGS.

        Args:
            nodes_to_process: Nodes to iterate through and process
            language: Programming language
            all_raw_nodes: Complete array that children_indices refer to (defaults to nodes_to_process)
            processed_indices: Set of indices already processed as children (for hierarchical nesting)
        """
        if all_raw_nodes is None:
            all_raw_nodes = nodes_to_process

        if processed_indices is None:
            processed_indices = set()

        mappings = self._get_frame_mappings(language)

        # Performance optimization: Create index map to avoid O(n²) with repeated index() calls
        node_to_index = {id(node): idx for idx, node in enumerate(all_raw_nodes)}

        for raw_node in nodes_to_process:
            # Find the actual index of this node in all_raw_nodes using precomputed map
            # processed_indices tracks indices in all_raw_nodes, not positions in nodes_to_process
            actual_index = node_to_index.get(id(raw_node))
            if actual_index is None:
                # Node not in all_raw_nodes (shouldn't happen, but be defensive)
                logging.getLogger(__name__).warning(f"Node {raw_node.node_type} at line {raw_node.start_line} not found in all_raw_nodes")
                continue

            # Skip if already processed as child of another frame
            if actual_index in processed_indices:
                continue
                
            # Decision 1: Should this raw node become a frame?
            frame_type = mappings.get(raw_node.node_type)
            if not frame_type:
                continue  # Skip non-semantic nodes

            # Create semantic frame
            frame = self._create_semantic_frame(raw_node, frame_type, language)

            # ALL frames become children of current context
            self.context.frame_stack.add_child_to_current(frame)

            # Decision 2: Should this frame create a new context scope?
            if self._should_push_to_stack(frame_type):
                # Push context for processing children
                with self.context.frame_stack.push_context(frame):
                    # CRITICAL: Always pass all_raw_nodes so children_indices remain valid
                    self._process_child_nodes(raw_node, all_raw_nodes, language, processed_indices, _depth)

    def _create_semantic_frame(self, raw_node: RawNode, frame_type: FrameNodeType, language: str) -> AstFrameBase:
        """
        Create semantic frame from raw node.
        
        Delegates to FrameFactory for instantiation, deduplication, and class selection.
        """
        from nabu.parsing.frame_factory import FrameFactory
        
        # Extract name
        name = self._extract_name_from_content(raw_node.content, frame_type, raw_node, language)

        # Calculate qualified name using frame stack context
        context_path = self.context.frame_stack.get_context_path()
        qualified_name = '.'.join(context_path + [name]) if name else None

        # Use factory to create frame with automatic deduplication
        # Frame ID is now computed internally based on content hash
        frame = FrameFactory.create_frame(
            frame_type=frame_type,
            name=name,
            qualified_name=qualified_name,
            raw_node=raw_node,
            language=language,
            context=self.context
        )

        return frame

    def _should_push_to_stack(self, frame_type: FrameNodeType) -> bool:
        """
        Determine if frame type should create a new context scope.
        
        Context-creating frames push a new level onto the frame stack,
        allowing their children to be nested within them. This affects:
        - Qualified name generation (children inherit parent's path)
        - Symbol resolution (children can access parent's scope)
        - Graph structure (children are descendants in the hierarchy)
        
        Structural frames (CLASS, CALLABLE, PACKAGE) create new contexts.
        Control flow frames (IF_BLOCK, FOR_LOOP, etc.) also create contexts for proper scope nesting.
        
        Non-context frames (if added in future): VARIABLE, PARAMETER, IMPORT, etc.
        These would become children but not create nested scopes.
        """
        return frame_type.creates_context()

    def _process_child_nodes(self, parent_raw_node: RawNode, all_raw_nodes: List[RawNode], language: str, processed_indices: Optional[set] = None, _depth: int = 0) -> None:
        """
        Process child nodes within parent context.

        Recursively process descendants BUT only those within parent's byte range.
        This correctly handles:
        1. Intermediate non-semantic nodes (like 'block') that aren't in FRAME_MAPPINGS
        2. Prevents sibling methods from being nested under __init__

        Example: class_definition (CppMangler) → block → function_definition (__init__)
                                                       → function_definition (mangle)
                                                       → function_definition (_generate_itanium_name)

        All methods are children of the block, which is a child of the class.
        We need to process all methods as children of CppMangler, not as children of __init__.

        Args:
            parent_raw_node: The parent raw node whose descendants we're processing
            all_raw_nodes: Complete list of all raw nodes in the file
            language: Programming language
            processed_indices: Set of indices that have been processed at parent level
            _depth: Internal recursion depth counter (for safety)
        """
        # Safety check: prevent infinite recursion
        if _depth > 1000:
            logging.getLogger(__name__).error(f"Maximum recursion depth exceeded in _process_child_nodes for {parent_raw_node.node_type} at line {parent_raw_node.start_line}")
            return

        if not parent_raw_node.children_indices:
            return

        if processed_indices is None:
            processed_indices = set()

        # Collect descendants that should be processed at this level
        # Strategy: Collect direct frame-candidate children, plus drill through non-semantic nodes
        # BUT: For each semantic node collected, DON'T collect ITS descendants (they'll be handled recursively)
        descendant_nodes = []
        collected_indices = set()  # Track what we've added to avoid duplicates
        
        def collect_children_smart(idx: int):
            """
            Recursively collect children, but stop descending at semantic nodes.

            This handles:
            - Passthrough nodes (block, etc): drill through to find semantic children
            - Semantic nodes: add them, but DON'T recurse into their children
            """
            if idx >= len(all_raw_nodes):
                return

            if idx in collected_indices:
                return

            if idx in processed_indices:
                return

            node = all_raw_nodes[idx]

            # Only include nodes within parent's byte range
            if not (node.start_byte >= parent_raw_node.start_byte and
                    node.end_byte <= parent_raw_node.end_byte):
                return
            
            # Check if this node maps to a frame type
            mappings = self._get_frame_mappings(language)
            is_semantic = node.node_type in mappings
            
            # Add this node
            descendant_nodes.append(node)
            collected_indices.add(idx)
            
            # If semantic: STOP - its children will be processed when it's pushed
            # If non-semantic: drill through to find semantic children
            if not is_semantic:
                for child_idx in node.children_indices:
                    collect_children_smart(child_idx)
        
        # Start collection from parent's direct children
        for child_idx in parent_raw_node.children_indices:
            collect_children_smart(child_idx)

        # Process all collected descendants
        # Non-semantic nodes (like 'block') will be skipped by FRAME_MAPPINGS check
        # But their descendants have been collected and will be processed
        # CRITICAL: Pass all_raw_nodes so children_indices remain valid when processing descendants
        # CRITICAL: Pass processed_indices (not a new set) so updates propagate to parent
        self._process_raw_nodes(descendant_nodes, language, all_raw_nodes, processed_indices, _depth + 1)

        # CRITICAL FIX: Mark all collected indices as processed in parent's tracking
        # This prevents the parent from reprocessing these nodes after we return
        # collected_indices contains indices relative to all_raw_nodes, which is what processed_indices tracks
        processed_indices.update(collected_indices)

    def _extract_name_from_content(self, content: str, frame_type: FrameNodeType, raw_node: RawNode, language: str) -> Optional[str]:
        """
        Extract name from raw content using language handler.

        Delegates to language-specific handlers for robust name extraction.

        Args:
            content: Raw source code content
            frame_type: Type of frame (CLASS, CALLABLE, PACKAGE, or control flow)
            raw_node: Raw node with metadata
            language: Programming language

        Returns:
            Extracted name or None if extraction fails
        """
        handler = language_registry.get_handler(language)
        if not handler:
            logging.getLogger(__name__).warning(f"No handler found for language: {language}")
            return None

        if not content or not content.strip():
            return None

        # Structural types: delegate to language-specific handler
        if frame_type.has_semantic_name():
            if frame_type == FrameNodeType.CLASS:
                return handler.extract_class_name(content, raw_node)
            elif frame_type == FrameNodeType.CALLABLE:
                return handler.extract_callable_name(content, raw_node)
            elif frame_type == FrameNodeType.PACKAGE:
                return handler.extract_package_name(content, raw_node)
        
        # Control flow frames: generate unique names using line+byte to avoid collisions
        # Multiple control flow statements at same line in different files need unique IDs
        if frame_type.is_control_flow() or frame_type == FrameNodeType.SCOPE:
            type_name = frame_type.value.lower()
            # Include byte position to distinguish control flow at same line in different contexts
            return f"{type_name}_line_{raw_node.start_line}_byte_{raw_node.start_byte}"

        return None



