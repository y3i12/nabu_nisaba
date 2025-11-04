"""
Stable ID Generation for AST Nodes

This module implements multiple strategies for generating stable identifiers
for tree-sitter AST nodes. The goal is to enable incremental updates by
maintaining stable IDs across parser runs.

Design Goals:
- Stability: Same node → same ID across parser runs
- Uniqueness: Different nodes → different IDs
- Sensitivity: Changed nodes → different IDs (for change detection)

Trade-offs:
- Positional IDs: High sensitivity, low stability (changes propagate)
- Content IDs: High stability, risk of collisions (identical code)
- Hybrid IDs: Balanced approach using semantic anchors
"""

import hashlib
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class IdStrategy(Enum):
    """Available ID generation strategies."""
    POSITIONAL = "positional"           # Based on byte position
    CONTENT_HASH = "content_hash"       # Based on source code content
    STRUCTURAL_HASH = "structural_hash" # Based on node structure
    HYBRID = "hybrid"                   # Semantic anchors + relative position
    HIERARCHICAL = "hierarchical"       # Tree path addressing


@dataclass
class NodeContext:
    """Context information needed for ID generation."""
    file_path: str
    node_type: str
    start_byte: int
    end_byte: int
    start_line: int
    end_line: int
    content: str
    children_types: List[str]           # Types of immediate children
    parent_type: Optional[str] = None
    semantic_anchor: Optional[str] = None  # e.g., "MyClass.my_method"
    tree_path: Optional[List[int]] = None  # [0, 2, 1] = child indices from root


class StableIdGenerator:
    """
    Generate stable IDs for AST nodes using various strategies.
    
    Usage:
        generator = StableIdGenerator(strategy=IdStrategy.HYBRID)
        node_id = generator.generate_id(node_context)
    """
    
    def __init__(self, strategy: IdStrategy = IdStrategy.HYBRID):
        self.strategy = strategy
        self._semantic_node_types = {
            'class_definition', 'class_declaration', 'class_specifier',
            'function_definition', 'function_declaration', 'method_declaration',
            'module', 'namespace_definition'
        }
    
    def generate_id(self, context: NodeContext) -> str:
        """
        Generate stable ID based on configured strategy.
        
        Args:
            context: Node context information
            
        Returns:
            Stable identifier string (16-64 chars)
        """
        if self.strategy == IdStrategy.POSITIONAL:
            return self._positional_id(context)
        elif self.strategy == IdStrategy.CONTENT_HASH:
            return self._content_hash_id(context)
        elif self.strategy == IdStrategy.STRUCTURAL_HASH:
            return self._structural_hash_id(context)
        elif self.strategy == IdStrategy.HYBRID:
            return self._hybrid_id(context)
        elif self.strategy == IdStrategy.HIERARCHICAL:
            return self._hierarchical_id(context)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")
    
    def _positional_id(self, context: NodeContext) -> str:
        """
        Strategy 1: Positional ID
        
        Based on: file_path + node_type + byte_position
        
        Stability: LOW (any edit above changes byte offsets)
        Uniqueness: HIGH (position is unique)
        Sensitivity: VERY HIGH (detects all changes)
        
        Use case: Maximum change detection, acceptable when full re-indexing
        """
        key = f"{context.file_path}::{context.node_type}::{context.start_byte}:{context.end_byte}"
        return self._hash_key(key, prefix="POS")
    
    def _content_hash_id(self, context: NodeContext) -> str:
        """
        Strategy 2: Content Hash
        
        Based on: normalized source code content
        
        Stability: VERY HIGH (same code → same ID even if moved)
        Uniqueness: MEDIUM (identical code gets same ID - collision risk)
        Sensitivity: LOW (only content changes detected, not moves)
        
        Use case: Tracking code snippets across moves/refactorings
        """
        # Normalize whitespace for stability
        normalized = self._normalize_content(context.content)
        key = f"{context.node_type}::{normalized}"
        return self._hash_key(key, prefix="CNT")
    
    def _structural_hash_id(self, context: NodeContext) -> str:
        """
        Strategy 3: Structural Hash
        
        Based on: file + position + immediate children structure
        
        Stability: MEDIUM (stable unless children structure changes)
        Uniqueness: HIGH (structure provides discrimination)
        Sensitivity: MEDIUM (detects structural changes)
        
        Use case: Balance between stability and change detection
        """
        # Include first 5 children types for structural signature
        children_sig = "_".join(context.children_types[:5])
        key = (
            f"{context.file_path}::{context.node_type}::"
            f"{context.start_byte}:{context.end_byte}::{children_sig}"
        )
        return self._hash_key(key, prefix="STR")
    
    def _hybrid_id(self, context: NodeContext) -> str:
        """
        Strategy 4: Hybrid (RECOMMENDED)
        
        Based on: semantic_anchor + relative_position OR absolute_position
        
        For semantic nodes (class, function):
            Use qualified name + node type
        For nested nodes:
            Use anchor + relative offset + node type
        For orphan nodes:
            Fall back to structural hash
        
        Stability: HIGH (edits within method don't affect other methods)
        Uniqueness: HIGH (semantic names + relative position)
        Sensitivity: MEDIUM-HIGH (detects meaningful changes)
        
        Use case: Best for incremental updates with semantic awareness
        """
        # Check if this is a semantic anchor node
        if context.node_type in self._semantic_node_types and context.semantic_anchor:
            # Top-level semantic node: use qualified name
            key = f"{context.file_path}::{context.semantic_anchor}"
            return self._hash_key(key, prefix="SEM")
        
        elif context.semantic_anchor:
            # Nested node: use anchor + relative position
            # This makes the ID stable within the semantic scope
            rel_offset = context.start_byte  # In real impl, subtract anchor's start_byte
            key = (
                f"{context.file_path}::{context.semantic_anchor}::"
                f"{context.node_type}::{rel_offset}"
            )
            return self._hash_key(key, prefix="HYB")
        
        else:
            # No semantic context: fall back to structural hash
            return self._structural_hash_id(context)
    
    def _hierarchical_id(self, context: NodeContext) -> str:
        """
        Strategy 5: Hierarchical Path
        
        Based on: tree path from root (child indices)
        
        Stability: LOW (any insertion changes sibling indices)
        Uniqueness: HIGH (path is unique in tree)
        Sensitivity: VERY HIGH (any structural change detected)
        
        Use case: Debugging, tree visualization, not recommended for incremental updates
        """
        if context.tree_path:
            path_str = ".".join(map(str, context.tree_path))
            key = f"{context.file_path}::{path_str}::{context.node_type}"
        else:
            # Fall back to positional if no path available
            key = f"{context.file_path}::{context.node_type}::{context.start_byte}"
        
        return self._hash_key(key, prefix="HIE")
    
    def _hash_key(self, key: str, prefix: str = "") -> str:
        """
        Hash a key string to create compact ID.
        
        Args:
            key: Input string to hash
            prefix: Optional prefix for strategy identification (3 chars)
            
        Returns:
            Hash string (prefix + 16 hex chars = 19 chars total)
        """
        hash_obj = hashlib.sha256(key.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()[:16]  # 16 chars for compactness
        
        if prefix:
            return f"{prefix}_{hash_hex}"
        return hash_hex
    
    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for stable hashing.
        
        Removes:
        - Leading/trailing whitespace per line
        - Empty lines
        - Reduces multiple spaces to single space
        
        This makes IDs stable across formatting changes.
        """
        lines = content.split('\n')
        normalized_lines = [
            ' '.join(line.split())  # Collapse whitespace
            for line in lines
            if line.strip()  # Skip empty lines
        ]
        return '\n'.join(normalized_lines)
    
    def is_semantic_node(self, node_type: str) -> bool:
        """Check if node type is a semantic anchor."""
        return node_type in self._semantic_node_types


class IdStabilityMetrics:
    """Track ID stability metrics across edits."""
    
    def __init__(self):
        self.total_nodes = 0
        self.stable_ids = 0
        self.changed_ids = 0
        self.new_nodes = 0
        self.deleted_nodes = 0
    
    def compute_metrics(
        self,
        old_ids: Dict[str, Any],
        new_ids: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Compare old and new ID sets to compute stability metrics.
        
        Args:
            old_ids: {node_id: node_info} before edit
            new_ids: {node_id: node_info} after edit
            
        Returns:
            Metrics dictionary with percentages
        """
        old_set = set(old_ids.keys())
        new_set = set(new_ids.keys())
        
        self.total_nodes = len(new_set)
        self.stable_ids = len(old_set & new_set)
        self.new_nodes = len(new_set - old_set)
        self.deleted_nodes = len(old_set - new_set)
        self.changed_ids = self.new_nodes + self.deleted_nodes
        
        return {
            'total_nodes': self.total_nodes,
            'stable_ids': self.stable_ids,
            'stable_percentage': (self.stable_ids / self.total_nodes * 100) if self.total_nodes > 0 else 0,
            'new_nodes': self.new_nodes,
            'deleted_nodes': self.deleted_nodes,
            'changed_ids': self.changed_ids,
            'churn_percentage': (self.changed_ids / self.total_nodes * 100) if self.total_nodes > 0 else 0
        }


def extract_semantic_anchor(ts_node, source_code: str) -> Optional[str]:
    """
    Extract semantic anchor (qualified name) for a tree-sitter node.
    
    This is a helper function that traverses up the tree to find
    the nearest semantic node (class, function) and constructs
    its qualified name.
    
    Args:
        ts_node: Tree-sitter node
        source_code: Source code string
        
    Returns:
        Qualified name like "MyClass.my_method" or None
    """
    semantic_types = {
        'class_definition', 'class_declaration', 'class_specifier',
        'function_definition', 'function_declaration', 'method_declaration',
    }
    
    # Traverse upward to find semantic ancestors
    current = ts_node
    parts = []
    
    while current:
        if current.type in semantic_types:
            # Extract name from this semantic node
            name = _extract_name_from_node(current, source_code)
            if name:
                parts.insert(0, name)
        
        current = current.parent
    
    return '.'.join(parts) if parts else None


def _extract_name_from_node(ts_node, source_code: str) -> Optional[str]:
    """
    Extract the name identifier from a semantic node.
    
    This is language-specific - different languages use different
    child nodes for names.
    """
    # Common patterns across languages
    name_types = {'identifier', 'name', 'class_name', 'function_name', 'type_identifier'}
    
    for child in ts_node.children:
        if child.type in name_types:
            start = child.start_byte
            end = child.end_byte
            return source_code[start:end]
    
    return None


# Example usage and testing helpers
def create_node_context_from_raw_node(raw_node, semantic_anchor: Optional[str] = None) -> NodeContext:
    """
    Helper to create NodeContext from RawNode.
    
    This bridges the existing RawNode structure to the new ID system.
    """
    from nabu.parsing.raw_extraction import RawNode
    
    # Extract children types from ts_node if available
    children_types = []
    if hasattr(raw_node, 'ts_node') and raw_node.ts_node:
        children_types = [child.type for child in raw_node.ts_node.children]
    
    return NodeContext(
        file_path=raw_node.file_path,
        node_type=raw_node.node_type,
        start_byte=raw_node.start_byte,
        end_byte=raw_node.end_byte,
        start_line=raw_node.start_line,
        end_line=raw_node.end_line,
        content=raw_node.content,
        children_types=children_types,
        semantic_anchor=semantic_anchor
    )
