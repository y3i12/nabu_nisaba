"""
Codebase Context - Centralized State Management

This module provides the CodebaseContext class which centralizes shared state
across parsing passes (GraphBuilder, SymbolResolver, etc.).

Key responsibilities:
- Unified ID generation (frame_id, edge_id) to prevent collisions
- Shared FrameStack for consistent hierarchy access
- Centralized registries for deduplication
- Edge collection across parsing phases
- Confidence tracking

Addresses architectural issues where state was duplicated across parsers.
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field

from nabu.core.frame_stack import FrameStack
from nabu.core.frames import AstFrameBase, AstLanguageFrame, AstEdge
from nabu.core.registry import FrameRegistry
from nabu.core.confidence import ConfidenceContext


@dataclass
class CodebaseContext:
    """
    Centralized context for codebase parsing and analysis.
    
    This class is instantiated once per parsing session and shared across
    all parsing components (GraphBuilder, SymbolResolver, etc.).
    
    Design principles:
    - Single source of truth for IDs (prevents collisions)
    - Shared FrameStack (enables cross-component hierarchy access)
    - Centralized registries (enables deduplication)
    - Unified edge collection (simplifies graph assembly)
    """
    
    # Shared frame stack - THE KEY
    frame_stack: Optional[FrameStack] = None
    
    # Unified ID generation - prevents collisions
    edge_id_counter: int = 0
    
    # Language-specific registries
    # Maps language name -> FrameRegistry for that language
    registries: Dict[str, FrameRegistry] = field(default_factory=dict)
    
    # Language root frames
    # Maps language name -> AstLanguageFrame
    language_frames: Dict[str, AstLanguageFrame] = field(default_factory=dict)
    
    # Type-specific registries for fast lookups
    processed_files: Set[str] = field(default_factory=set)  # Track processed file paths
    package_registry: Dict[str, AstFrameBase] = field(default_factory=dict)  # qualified_name -> frame
    class_registry: Dict[str, AstFrameBase] = field(default_factory=dict)  # qualified_name -> frame
    callable_registry: Dict[str, AstFrameBase] = field(default_factory=dict)  # qualified_name -> frame
    control_flow_registry: Dict[str, AstFrameBase] = field(default_factory=dict)  # location_key -> frame
    
    # Edge tracking across parsing phases
    hierarchy_edges: List[AstEdge] = field(default_factory=list)  # from GraphBuilder
    symbol_edges: List[AstEdge] = field(default_factory=list)  # from SymbolResolver
    
    # External/unresolved frames (not part of containment hierarchy)
    external_frames: List[AstFrameBase] = field(default_factory=list)  # from SymbolResolver
    
    # Confidence tracking
    confidence_context: ConfidenceContext = field(default_factory=ConfidenceContext)
    
    # Processing state (processed_files already defined above in registries section)
    codebase_root: str = ""  # Root path for relative path calculation
    
    
    def next_edge_id(self) -> int:
        """Generate next unique edge ID."""
        self.edge_id_counter += 1
        return self.edge_id_counter
    
    def get_all_edges(self) -> List[AstEdge]:
        """
        Get all edges from all sources.
        
        Combines:
        - FrameStack edges (CONTAINS relationships)
        - Hierarchy edges (from GraphBuilder)
        - Symbol edges (from SymbolResolver)
        """
        all_edges = []
        
        # Edges from FrameStack
        if self.frame_stack:
            all_edges.extend(self.frame_stack.edges)
        
        # Edges from parsing phases
        all_edges.extend(self.hierarchy_edges)
        all_edges.extend(self.symbol_edges)
        
        return all_edges

    def get_all_frames(self) -> List[AstFrameBase]:
        """
        Get all unique frames from the frame hierarchy.
        
        Registries only contain FILE, PACKAGE, CLASS, CALLABLE frames.
        Most frames (control flow, variables, etc.) are not registered.
        
        Solution: Start from codebase root and collect all frames via BFS,
        using a visited set to handle multi-parent relationships correctly.
        
        This is different from the exporter's tree traversal bug because:
        - We collect ALL frames into a set first
        - We don't stop recursion when we see a visited frame
        - We only skip adding duplicates to the result list
        """
        if not self.frame_stack or not self.frame_stack.root_frame:
            # Fallback to registry-only collection if no root available
            frames_by_id: Dict[int, AstFrameBase] = {}
            

            for frame in self.package_registry.values():
                frames_by_id[frame.id] = frame
            for frame in self.class_registry.values():
                frames_by_id[frame.id] = frame
            for frame in self.callable_registry.values():
                frames_by_id[frame.id] = frame
            for lang_frame in self.language_frames.values():
                frames_by_id[lang_frame.id] = lang_frame
            
            # Include external frames that are not part of containment hierarchy
            for ext_frame in self.external_frames:
                frames_by_id[ext_frame.id] = ext_frame
                
            return list(frames_by_id.values())
        
        # Correct approach: BFS from root, collecting all unique frames
        frames_by_id: Dict[int, AstFrameBase] = {}
        queue = [self.frame_stack.root_frame]
        
        while queue:
            frame = queue.pop(0)
            
            # Add to collection if not already present
            if frame.id not in frames_by_id:
                frames_by_id[frame.id] = frame
                
                # Add all children to queue (will be deduplicated by ID check)
                queue.extend(frame.children)
        
        # Include external frames that are not part of containment hierarchy
        for ext_frame in self.external_frames:
            if ext_frame.id not in frames_by_id:
                frames_by_id[ext_frame.id] = ext_frame
        
        return list(frames_by_id.values())
    
    def initialize_frame_stack(self, root_frame: AstFrameBase) -> None:
        """
        Initialize the shared FrameStack with the codebase root frame.
        
        This should be called once at the beginning of graph building.
        The FrameStack will use this context's edge ID generator and
        will have access to the package registry for lookups.
        """
        self.frame_stack = FrameStack(root_frame, edge_id_generator=self.next_edge_id)
        # Give FrameStack access to package_registry for global lookups
        self.frame_stack._package_registry = self.package_registry
        # Give FrameStack access to context for external_frames list
        self.frame_stack._context_ref = self
    
    def reset(self) -> None:
        """
        Reset context for a new parsing session.
        
        Warning: This clears all state. Use with caution.
        """
        self.frame_stack = None
        self.edge_id_counter = 0
        self.registries.clear()
        self.language_frames.clear()
        self.processed_files.clear()
        self.package_registry.clear()
        self.class_registry.clear()
        self.callable_registry.clear()
        self.hierarchy_edges.clear()
        self.symbol_edges.clear()
        self.external_frames.clear()
        self.confidence_context = ConfidenceContext()
        self.processed_files.clear()
        self.codebase_root = ""
