from typing import List, Optional, Iterator, Tuple, Dict
from contextlib import contextmanager

from nabu.core.frames import AstFrameBase, AstEdge
from nabu.core.frame_types import FrameNodeType, EdgeType
from nabu.core.confidence import ConfidenceCalculator, ConfidenceContext


class FrameStack:
    """
    Multi-frame stack with confidence system.

    BREAKING CHANGE: Stack now supports multiple frames at each level via Dict[FrameNodeType, AstFrameBase].
    This allows operations like:
        with self.frame_stack.push_context(package=package_frame, file=file_frame):
            # Both package and file are active - add_child() adds to BOTH

    Based on the sophisticated FrameStack in src/nabu/core/frame_stack.py
    but integrated with the confidence system and multi-frame support.
    """

    def __init__(self, root_frame: Optional[AstFrameBase] = None, edge_id_generator=None):
        """
        Initialize FrameStack.
        
        Args:
            root_frame: Optional root frame to initialize stack with
            edge_id_generator: Optional callable that returns unique edge IDs.
                             If None, uses internal counter.
        """
        # Stack now holds Dict[FrameNodeType, AstFrameBase] per level
        self.stack: List[Dict[FrameNodeType, AstFrameBase]] = []
        self.confidence_context: ConfidenceContext = ConfidenceContext()
        self.edges: List[AstEdge] = []
        self._edge_id_counter: int = 0
        self._edge_id_generator = edge_id_generator  # Optional external ID generator

        if root_frame:
            self.stack.append({root_frame.type: root_frame})

    @property
    def depth(self) -> int:
        """Current stack depth."""
        return len(self.stack)

    @property
    def is_empty(self) -> bool:
        """Whether the stack is empty."""
        return len(self.stack) == 0

    @property
    def current_frame(self) -> Optional[AstFrameBase]:
        """
        Get the current (top) frame without popping.

        Resolution order: CALLABLE > CLASS > PACKAGE > FILE > LANGUAGE > CODEBASE
        Returns the most semantically specific frame from the current stack level.
        """
        if not self.stack:
            return None

        current_level = self.stack[-1]

        # Priority order for frame types
        priority_order = [
            FrameNodeType.CALLABLE,
            FrameNodeType.CLASS,
            FrameNodeType.PACKAGE,
            FrameNodeType.LANGUAGE,
            FrameNodeType.CODEBASE
        ]

        for frame_type in priority_order:
            if frame_type in current_level:
                return current_level[frame_type]

        # Fallback: return any frame from the dict
        return next(iter(current_level.values()), None)

    @property
    def current_frames(self) -> Dict[FrameNodeType, AstFrameBase]:
        """Get all frames at the current stack level."""
        return self.stack[-1] if self.stack else {}

    @property
    def root_frame(self) -> Optional[AstFrameBase]:
        """Get the root (bottom) frame."""
        if not self.stack:
            return None
        root_level = self.stack[0]
        return next(iter(root_level.values()), None)

    def get_frame_by_type(self, frame_type: FrameNodeType) -> Optional[AstFrameBase]:
        """Get specific frame type from current stack level."""
        if not self.stack:
            return None
        return self.stack[-1].get(frame_type)

    def push_frame_with_confidence(
        self,
        frame: AstFrameBase,
        confidence: float,
        provenance: str
    ) -> None:
        """
        Push single frame with confidence system integration (backward compat).

        For new code, prefer push_multi_context() which accepts multiple frames.
        """
        # Set confidence properties
        frame.confidence = confidence
        frame.provenance = provenance
        frame.resolution_pass = self.confidence_context.current_pass
        frame.confidence_tier = ConfidenceCalculator.calculate_tier(confidence)

        # Add frame as child to ALL frames in current stack level
        # EXCEPT for PACKAGE frames - their hierarchy is already established by _create_package_hierarchy
        if self.stack and frame.type != FrameNodeType.PACKAGE:
            current_level = self.stack[-1]
            for parent_frame in current_level.values():
                if frame not in parent_frame.children:
                    parent_frame.add_child(frame)

                    # Create CONTAINS edge with calculated confidence
                    edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
                        EdgeType.CONTAINS, parent_frame.confidence, frame.confidence
                    )
                    self._create_edge(parent_frame, frame, EdgeType.CONTAINS, edge_confidence)

        # Push as new stack level with single frame
        self.stack.append({frame.type: frame})

    def add_child_to_current(self, child: AstFrameBase) -> None:
        """
        Add child to ALL frames in current stack level.

        This is THE KEY METHOD for multi-parent support.
        When file and package are both stacked, child is added to BOTH.
        """
        if not self.stack:
            return

        current_level = self.stack[-1]
        for parent_frame in current_level.values():
            if child not in parent_frame.children:
                parent_frame.add_child(child)

                # Create CONTAINS edge with calculated confidence
                edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
                    EdgeType.CONTAINS, parent_frame.confidence, child.confidence
                )
                self._create_edge(parent_frame, child, EdgeType.CONTAINS, edge_confidence)

    def pop_frame(self) -> Dict[FrameNodeType, AstFrameBase]:
        """Pop the top stack level (dict of frames)."""
        return self.stack.pop() if self.stack else {}

    def resolve_symbol_with_confidence(self, name: str) -> Tuple[Optional[AstFrameBase], float]:
        """
        Symbol resolution with confidence across multi-frame stack.

        Searches through stack levels in reverse order (innermost to outermost).
        Within each level, checks frames in priority order: CALLABLE > CLASS > PACKAGE > FILE.
        """
        priority_order = [
            FrameNodeType.CALLABLE,
            FrameNodeType.CLASS,
            FrameNodeType.PACKAGE,
            FrameNodeType.LANGUAGE
        ]

        for i, stack_level in enumerate(reversed(self.stack)):
            # Try frames in priority order
            for frame_type in priority_order:
                frame = stack_level.get(frame_type)
                if frame:
                    symbol = frame.find_child_by_name(name)
                    if symbol:
                        # Calculate confidence based on scope distance
                        scope_distance = i  # Distance from current scope
                        confidence = ConfidenceCalculator.adjust_confidence_for_scope_distance(
                            symbol.confidence, scope_distance
                        )
                        return symbol, confidence

        return None, 0.0

    def resolve_relative_import(self, import_path: str) -> Optional[AstFrameBase]:
        """
        Handle relative imports using frame stack navigation.

        Example: from ..utils import helper
        -> Navigate up the stack to find the target package
        """
        if not import_path.startswith('.'):
            return None  # Not a relative import

        # Count dots to determine how many levels to go up
        dots = len(import_path) - len(import_path.lstrip('.'))
        remaining_path = import_path.lstrip('.')

        # Find current package in stack (search through all levels)
        current_package = None
        for stack_level in reversed(self.stack):
            package_frame = stack_level.get(FrameNodeType.PACKAGE)
            if package_frame:
                current_package = package_frame
                break

        if not current_package:
            return self._create_unknown_import_frame(import_path, confidence=0.3)

        # Navigate up the required number of levels
        target_package = current_package
        for _ in range(dots - 1):  # -1 because we're already at package level
            parent = target_package.get_primary_parent()
            if parent and parent.type == FrameNodeType.PACKAGE:
                target_package = parent
            else:
                # Can't navigate up far enough - create with low confidence
                return self._create_unknown_import_frame(import_path, confidence=0.2)

        # Parse the remaining path using language-specific separator
        # (e.g., "utils.helper" for Python, "utils::helper" for C++)
        from nabu.language_handlers import language_registry

        language = target_package.language
        handler = language_registry.get_handler(language) if language else None
        separator = handler.get_separator() if handler else '.'  # Fallback to '.' if no handler

        path_parts = remaining_path.split(separator) if remaining_path else []
        current = target_package

        for part in path_parts:
            child = current.find_child_by_name(part)
            if not child:
                # Create the missing part with medium confidence
                child = self._create_package_frame(
                    name=part,
                    parent=current,
                    confidence=0.6,
                    provenance="relative_import"
                )
                current.add_child(child)
            current = child

        return current

    # Context managers

    @contextmanager
    def push_context(self, frame: AstFrameBase) -> Iterator[AstFrameBase]:
        """Single-frame context manager (backward compatibility)."""
        self.push_frame_with_confidence(
            frame,
            frame.confidence,
            frame.provenance
        )
        try:
            yield frame
        finally:
            self.pop_frame()

    @contextmanager
    def push_multi_context(
        self, 
        skip_redundant_edges: bool = False,
        **frames: AstFrameBase
    ) -> Iterator[Dict[FrameNodeType, AstFrameBase]]:
        """
        Multi-frame context manager - THE KEY METHOD for simultaneous frame activation.

        Usage:
            with self.frame_stack.push_multi_context(
                package=package_frame,
                file=file_frame,
                skip_redundant_edges=True
            ):
                # Both package and file are active
                # add_child_to_current() will add to BOTH
                # skip_redundant_edges prevents re-adding existing children
        
        Args:
            skip_redundant_edges: If True, don't create CONTAINS edges 
                                when frame is already a child of parent
            **frames: Named frames to push (e.g., file=file_frame, package=pkg_frame)
        """
        if not frames:
            raise ValueError("push_multi_context requires at least one frame")

        # Build stack level dict
        stack_level: Dict[FrameNodeType, AstFrameBase] = {}
        for frame in frames.values():
            stack_level[frame.type] = frame

            # Add each frame as child to ALL frames in current stack level
            if self.stack:
                current_level = self.stack[-1]
                for parent_frame in current_level.values():
                    # Smart duplicate detection
                    # If skip_redundant_edges=True, don't add if:
                    # 1. Frame is already a child of this parent, OR
                    # 2. Frame already has parents (indicating pre-established hierarchy)
                    should_skip = (
                        skip_redundant_edges and
                        (frame in parent_frame.children or len(frame.parents_list) > 0)
                    )

                    if not should_skip and frame not in parent_frame.children:
                        parent_frame.add_child(frame)

                        # Create CONTAINS edge
                        edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
                            EdgeType.CONTAINS, parent_frame.confidence, frame.confidence
                        )
                        self._create_edge(parent_frame, frame, EdgeType.CONTAINS, edge_confidence)

        # Push the new level
        self.stack.append(stack_level)
        try:
            yield stack_level
        finally:
            self.pop_frame()

    @contextmanager
    def language_context(self, language_frame: AstFrameBase) -> Iterator[AstFrameBase]:
        """Context manager for language frames."""
        with self.push_context(language_frame) as frame:
            yield frame

    @contextmanager
    def package_context(self, package_frame: AstFrameBase) -> Iterator[AstFrameBase]:
        """Context manager for package frames."""
        with self.push_context(package_frame) as frame:
            yield frame

    @contextmanager
    def class_context(self, class_frame: AstFrameBase) -> Iterator[AstFrameBase]:
        """Context manager for class frames."""
        with self.push_context(class_frame) as frame:
            yield frame

    @contextmanager
    def function_context(self, function_frame: AstFrameBase) -> Iterator[AstFrameBase]:
        """Context manager for function frames."""
        with self.push_context(function_frame) as frame:
            yield frame

    def get_context_path(self) -> List[str]:
        """
        Get hierarchical path for name mangling.

        Extracts names from semantic frames only (CALLABLE, CLASS, PACKAGE).
        Uses qualified_name for PACKAGE to avoid collisions between packages
        with same name in different parent packages (e.g., nabu.core vs nabu.core).
        """
        path = []
        semantic_types = [FrameNodeType.CALLABLE, FrameNodeType.CLASS, FrameNodeType.PACKAGE]
        
        for stack_level in self.stack:
            for frame_type in semantic_types:
                frame = stack_level.get(frame_type)
                if frame:
                    # Use qualified_name for PACKAGE to avoid collisions
                    if frame_type == FrameNodeType.PACKAGE and frame.qualified_name:
                        path.append(frame.qualified_name)
                        break
                    elif frame.name:
                        path.append(frame.name)
                        break
        
        return path

    # Helper methods

    def _create_edge(
        self,
        subject: AstFrameBase,
        object_frame: AstFrameBase,
        type: EdgeType,
        confidence: float
    ) -> AstEdge:
        """Create an edge with confidence."""
        # Use external generator if provided, otherwise use internal counter
        if self._edge_id_generator:
            edge_id = self._edge_id_generator()
        else:
            edge_id = self._edge_id_counter
            self._edge_id_counter += 1
        
        edge = AstEdge(
            id=edge_id,
            subject_frame=subject,
            object_frame=object_frame,
            type=type,
            confidence=confidence
        )
        self.edges.append(edge)
        return edge

    def _create_unknown_import_frame(self, import_path: str, confidence: float) -> AstFrameBase:
        """Create frame for unknown imports."""
        from .frames import AstPackageFrame

        frame = AstPackageFrame(
            id="temp",  # Temporary - will be computed
            type=FrameNodeType.PACKAGE,  # Will be overridden by __post_init__
            name=import_path,
            qualified_name=import_path,
            confidence=confidence,
            provenance="unknown_import",
            file_path="<external_or_unresolved>"  # Mark as external
        )
        
        # Compute stable ID
        frame.compute_id()
        
        # Track in external frames if context is available
        if hasattr(self, '_context_ref') and self._context_ref:
            self._context_ref.external_frames.append(frame)
        
        return frame

    def _create_package_frame(
        self,
        name: str,
        parent: AstFrameBase,
        confidence: float,
        provenance: str
    ) -> AstFrameBase:
        """Create a package frame."""
        from .frames import AstPackageFrame

        frame = AstPackageFrame(
            id="temp",  # Temporary - will be computed
            type=FrameNodeType.PACKAGE,  # Will be overridden by __post_init__
            name=name,
            qualified_name=f"{parent.qualified_name}.{name}" if parent.qualified_name else name,
            confidence=confidence,
            provenance=provenance,
            language=parent.language,
            file_path="<external_or_unresolved>"  # Mark as external
        )
        
        # Compute stable ID
        frame.compute_id()
        
        # Establish parent relationship
        parent.add_child(frame)
        
        return frame
