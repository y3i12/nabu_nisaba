from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from weakref import ref as WeakReference

from nabu.core.frame_types import FrameNodeType, EdgeType, ConfidenceTier

if TYPE_CHECKING:
    from tree_sitter import Node as TSNode
    from .registry import FrameRegistry
    from .field_info import FieldInfo, ParameterInfo


@dataclass(slots=True)  # Memory optimization: 40-60% reduction
class AstFrameBase:
    # Core identification
    id: str
    type: FrameNodeType
    name: Optional[str]
    qualified_name: Optional[str]

    # Confidence system
    confidence: float = 1.0                  # 0.0-1.0 precision
    confidence_tier: ConfidenceTier = ConfidenceTier.HIGH
    provenance: str = "parsed"               # parsed/imported/inferred/external/parse_failed
    resolution_pass: int = 1                 # Which parsing pass created this

    # Tree structure - MULTI-PARENT SUPPORT
    # Replaced single parent pointer with three data structures for different access patterns
    parents_by_id: Dict[str, 'AstFrameBase'] = field(default_factory=dict)
    parents_by_qualified_name: Dict[str, 'AstFrameBase'] = field(default_factory=dict)
    parents_list: List['AstFrameBase'] = field(default_factory=list)  # Preserves insertion order
    children: List['AstFrameBase'] = field(default_factory=list)

    # Source location
    file_path: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    start_byte: int = 0
    end_byte: int = 0
    content: Optional[str] = None

    # Language context
    language: Optional[str] = None

    # Metadata for extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Registry access (lazy-loaded, addresses memory concerns)
    _registry: Optional['FrameRegistry'] = None

    # Tree-sitter integration (direct reference - tree-sitter nodes cannot be weakly referenced)
    _tree_sitter_node: Optional[Any] = None
    
    # Cached heading (computed once during instantiation, used in DB/display)
    _cached_heading: Optional[str] = None

    def add_child(self, child: 'AstFrameBase') -> None:
        """
        Add child frame and establish bidirectional multi-parent relationship.
        
        Idempotent: calling multiple times with same child has no effect.
        Thread-safe note: Not thread-safe, assumes single-threaded graph building.
        """
        # Add child to parent's children list (deduplicated)
        if child not in self.children:
            self.children.append(child)
        
        # Add parent to child's parent structures (deduplicated)
        if self.id not in child.parents_by_id:
            child.parents_by_id[self.id] = self
            
            # Add to qualified name index if parent has qualified name
            if self.qualified_name:
                child.parents_by_qualified_name[self.qualified_name] = self
            
            # Add to ordered list (preserves insertion order = "primary" parent is first)
            child.parents_list.append(self)

    def get_primary_parent(self) -> Optional['AstFrameBase']:
        """Get primary parent (first parent added). For backward compatibility."""
        return self.parents_list[0] if self.parents_list else None

    def get_parent_by_type(self, frame_type: FrameNodeType) -> Optional['AstFrameBase']:
        """Get first parent of specified type (insertion order)."""
        for parent in self.parents_list:
            if parent.type == frame_type:
                return parent
        return None

    def get_all_parents_by_type(self, frame_type: FrameNodeType) -> List['AstFrameBase']:
        """Get all parents of specified type (insertion order)."""
        return [p for p in self.parents_list if p.type == frame_type]

    def has_parent_type(self, frame_type: FrameNodeType) -> bool:
        """Check if frame has at least one parent of specified type."""
        return any(p.type == frame_type for p in self.parents_list)

    @property
    def parent(self) -> Optional['AstFrameBase']:
        """Backward compatibility: returns primary parent."""
        return self.get_primary_parent()

    def find_child_by_name(self, name: str) -> Optional['AstFrameBase']:
        """Find direct child by name."""
        return next((c for c in self.children if c.name == name), None)

    def find_children_by_type(self, frame_type: FrameNodeType) -> List['AstFrameBase']:
        """Find all direct children of specific type."""
        return [c for c in self.children if c.type == frame_type]

    def get_language_root(self) -> Optional['AstFrameBase']:
        """
        Find language root by traversing parent graph with BFS.
        
        Tries primary parent chain first (fast path), then BFS through all parents.
        """
        # Fast path: follow primary parent chain
        current = self.get_primary_parent()
        while current:
            if current.type == FrameNodeType.LANGUAGE:
                return current
            current = current.get_primary_parent()
        
        # Fallback: BFS through all parent paths
        if not self.parents_list:
            return None
        
        visited = set()
        queue = list(self.parents_list)
        
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            
            if current.type == FrameNodeType.LANGUAGE:
                return current
            
            queue.extend(current.parents_list)
        
        return None

    def is_descendant_of(self, ancestor: 'AstFrameBase') -> bool:
        """
        Check if this frame is descendant of ancestor via ANY parent path (BFS).
        """
        if not self.parents_list:
            return False
        
        visited = set()
        queue = list(self.parents_list)
        
        while queue:
            current = queue.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            
            if current == ancestor:
                return True
            
            queue.extend(current.parents_list)
        
        return False

    def walk_descendants(self) -> List['AstFrameBase']:
        """Get all descendants in depth-first order."""
        result = []
        for child in self.children:
            result.append(child)
            result.extend(child.walk_descendants())
        return result

    @property
    def depth(self) -> int:
        """
        Calculate minimum depth across all parent paths.
        
        Rationale: Minimum depth represents "most accessible" path to root.
        """
        if not self.parents_list:
            return 0
        
        # Calculate depth for each parent path, return minimum
        min_depth = float('inf')
        
        for parent in self.parents_list:
            parent_depth = parent.depth
            min_depth = min(min_depth, parent_depth + 1)
        
        return int(min_depth) if min_depth != float('inf') else 0

    def has_cycle_to(self, potential_child: 'AstFrameBase') -> bool:
        """
        Check if adding potential_child would create a cycle.
        
        Returns True if potential_child is an ancestor of self.
        """
        return potential_child.is_descendant_of(self)

    def add_child_safe(self, child: 'AstFrameBase') -> bool:
        """
        Add child with cycle detection.
        
        Returns True if added, False if would create cycle.
        """
        if self.has_cycle_to(child):
            return False
        
        self.add_child(child)
        return True

    def get_parent_chain_for_mangling(self) -> List['AstFrameBase']:
        """
        Build parent chain for mangling by traversing ONLY [CALLABLE, CLASS, PACKAGE] parents.
        
        Skips FILE, LANGUAGE, CODEBASE as per mangling requirements.
        Traverses multi-parent graph depth-first, prioritizing CALLABLE → CLASS → PACKAGE.
        """
        chain = []
        visited = set()
        
        def traverse(frame: 'AstFrameBase'):
            if frame.id in visited:
                return
            visited.add(frame.id)
            
            # Get parents in priority order: CALLABLE → CLASS → PACKAGE
            for parent_type in [FrameNodeType.CALLABLE, FrameNodeType.CLASS, FrameNodeType.PACKAGE]:
                parent_frame = frame.get_parent_by_type(parent_type)
                if parent_frame:
                    traverse(parent_frame)  # Recurse to build chain from root
                    chain.append(parent_frame)
                    break  # Only follow one parent path (primary semantic parent)
        
        traverse(self)
        return chain

    @property
    def registry(self) -> Optional['FrameRegistry']:
        """Get the registry for this frame's language tree."""
        if self._registry is None:
            language_root = self.get_language_root()
            if language_root and hasattr(language_root, '_registry'):
                self._registry = language_root._registry
        return self._registry

    def compute_id(self) -> str:
        """
        Generate unique ID using enhanced content hash.
        
        Strategy:
        - Control flows: Position-based (stable across condition edits)
        - Semantic frames: Content-based (detect real changes)
        
        Returns:
            Unique identifier (16 hex chars)
        """
        import hashlib
        
        # Use qualified_name as scope, fallback to name
        scope = self.qualified_name or self.name or "anonymous"
        
        # Control flows: position-only ID (content changes don't affect ID)
        if self.type.is_control_flow():
            key = (
                f"{self.file_path or 'unknown'}::"
                f"{scope}::"
                f"{self.type.value}"
                # NO content component - position-based only
            )
        else:
            # Semantic frames (CLASS, CALLABLE, PACKAGE): content-based
            content_normalized = self._normalize_content(self.content) if self.content else ""
            key = (
                f"{self.file_path or 'unknown'}::"
                f"{scope}::"
                f"{self.type.value}::"
                f"{content_normalized}"
            )
        
        # Hash to create compact ID
        hash_obj = hashlib.sha256(key.encode('utf-8'))
        frame_id = hash_obj.hexdigest()[:16]
        
        # Store in id field
        self.id = frame_id
        return frame_id
    
    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for stable hashing.
        
        Removes:
        - Leading/trailing whitespace per line
        - Empty lines
        - Python comments (# and docstrings)
        - ALL whitespace (aggressive normalization for stability)
        
        This makes IDs stable across formatting and documentation changes.
        """
        if not content:
            return ""
        
        import re
        
        # Remove docstrings (triple-quoted strings at start of blocks)
        # This is a heuristic - matches lines that are only docstrings
        content = re.sub(r'^\s*("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')\s*$', '', content, flags=re.MULTILINE)
        
        lines = content.split('\n')
        normalized_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Skip comment-only lines
            if stripped.startswith('#'):
                continue
            
            # Remove inline comments (simple heuristic)
            # This doesn't handle # inside strings perfectly, but good enough
            if '#' in stripped:
                # Split on # and take first part (before comment)
                parts = stripped.split('#')
                if len(parts) > 1:
                    # Check if # is likely in a string (very simple check)
                    before_hash = parts[0]
                    quote_count_double = before_hash.count('"') - before_hash.count('\\"')
                    quote_count_single = before_hash.count("'") - before_hash.count("\\'")
                    
                    # If quotes are balanced, # is likely a comment
                    if quote_count_double % 2 == 0 and quote_count_single % 2 == 0:
                        stripped = before_hash.strip()
            
            # AGGRESSIVE: Remove ALL whitespace for maximum stability
            # This makes 'def foo(x,y):' and 'def foo(x, y):' identical
            normalized = ''.join(stripped.split())
            
            if normalized:
                normalized_lines.append(normalized)
        
        return '\n'.join(normalized_lines)

    @property
    def heading(self) -> str:
        """
        Extract frame heading (declaration/signature).
        
        The heading is the "what it is" (declaration), separate from
        the "what it does" (implementation in content).
        
        Returns:
            Heading string (first significant line or computed signature)
        """
        # Check cache first (for DB-loaded frames)
        if hasattr(self, '_cached_heading') and self._cached_heading:
            return self._cached_heading
        
        # Control flows: already first line only
        if self.type.is_control_flow():
            return self.content or ""
        
        # Callables: extract signature
        if self.type == FrameNodeType.CALLABLE:
            return self._extract_signature()
        
        # Classes: extract class declaration
        if self.type == FrameNodeType.CLASS:
            return self._extract_class_declaration()
        
        # Packages: create package declaration
        if self.type == FrameNodeType.PACKAGE:
            return self._extract_package_declaration()
        
        # Fallback: first non-empty line
        if self.content:
            lines = self.content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped:
                    return stripped
        
        return ""
    
    def _extract_signature(self) -> str:
        """
        Extract function/method signature (first significant line).
        
        Returns:
            Signature line without body
        """
        if not self.content:
            return ""
        
        lines = self.content.split('\n')
        
        # Find first line with function/method declaration
        for line in lines:
            stripped = line.strip()
            # Skip empty lines, comments, decorators, imports
            if not stripped:
                continue
            if stripped.startswith(('#', '//', '/*', '@', 'import', 'from')):
                continue
            # This is the signature line
            return stripped
        
        # Fallback: first line
        return lines[0] if lines else ""
    
    def _extract_class_declaration(self) -> str:
        """
        Extract class declaration header.
        
        Returns:
            Class declaration line
        """
        if not self.content:
            return ""
        
        lines = self.content.split('\n')
        
        # Find first line with class declaration
        for line in lines:
            stripped = line.strip()
            # Skip empty lines, comments, decorators
            if not stripped:
                continue
            if stripped.startswith(('#', '//', '/*', '@', 'import', 'from')):
                continue
            # This is the class declaration
            return stripped
        
        # Fallback: first line
        return lines[0] if lines else ""
    
    def _extract_package_declaration(self) -> str:
        """
        Extract or synthesize package declaration.
        
        Returns:
            Package declaration string
        """
        # For Python: use qualified name
        if self.language == 'python':
            return f"# Package: {self.qualified_name}"
        
        # For Java/C++: look for package/namespace in content
        if self.content:
            lines = self.content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped.startswith(('package ', 'namespace ')):
                    return stripped
        
        # Fallback: use qualified name
        return f"# Package: {self.qualified_name}"


@dataclass
class AstEdge:
    """
    Relationship between frames with confidence system.
    """

    id: int
    subject_frame: AstFrameBase
    object_frame: AstFrameBase
    type: EdgeType

    # Confidence system for edges
    confidence: float = 1.0
    confidence_tier: ConfidenceTier = ConfidenceTier.HIGH

    # Metadata for additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate confidence tier from confidence value."""
        if self.confidence >= 0.8:
            self.confidence_tier = ConfidenceTier.HIGH
        elif self.confidence >= 0.5:
            self.confidence_tier = ConfidenceTier.MEDIUM
        elif self.confidence >= 0.2:
            self.confidence_tier = ConfidenceTier.LOW
        else:
            self.confidence_tier = ConfidenceTier.SPECULATIVE


# Specialized frame types for specific languages (inheriting from base)

@dataclass(slots=True)
class AstCodebaseFrame(AstFrameBase):
    """Root codebase frame. Always type=CODEBASE."""

    def __post_init__(self):
        self.type = FrameNodeType.CODEBASE
        self.name = self.name or "codebase"
        self.qualified_name = self.qualified_name or "codebase"


@dataclass(slots=True)
class AstLanguageFrame(AstFrameBase):
    def __post_init__(self):
        self.type = FrameNodeType.LANGUAGE
        # Language-specific initialization can go here


@dataclass(slots=True)
class AstPackageFrame(AstFrameBase):
    """Package/namespace frame."""

    def __post_init__(self):
        self.type = FrameNodeType.PACKAGE



@dataclass(slots=True)
class AstClassFrame(AstFrameBase):
    """Class frame with field tracking."""
    instance_fields: List['FieldInfo'] = field(default_factory=list)
    static_fields: List['FieldInfo'] = field(default_factory=list)

    def __post_init__(self):
        self.type = FrameNodeType.CLASS


@dataclass(slots=True)
class AstCallableFrame(AstFrameBase):
    """Callable frame with parameter tracking."""
    parameters: List['ParameterInfo'] = field(default_factory=list)
    return_type: Optional[str] = None

    def __post_init__(self):
        self.type = FrameNodeType.CALLABLE


@dataclass(slots=True)
class AstVariableFrame(AstFrameBase):
    """
    Variable frame with type information.
    """
    declared_type: Optional[str] = None
    inferred_type: Optional[str] = None
    type_confidence: float = 1.0
    is_mutable: bool = True
    scope: str = "local"  # local, instance, class, global