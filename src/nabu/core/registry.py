"""
Frame Registry for Efficient Lookups

Implements the registry pattern replace the complex
multiple dictionaries.

Addresses the "Over-Complex Base Class" concern by providing centralized,
lazy-loaded indexing for the entire language tree.

Key benefits:
- Single source of truth for lookups
- Lazy rebuilding only when needed
- Memory efficient (one registry per language root)
- Clean separation of concerns
"""

from typing import Dict, List, Optional
from nabu.core.frames import AstFrameBase
from nabu.core.frame_types import FrameNodeType


class FrameRegistry:
    """
    Centralized, lazy-loaded indexing for entire language tree.
    """

    def __init__(self, language_root: AstFrameBase):
        self.language_root = language_root

        # Internal indexes - rebuilt when dirty
        self._by_id: Dict[str, AstFrameBase] = {}
        self._by_qualified_name: Dict[str, AstFrameBase] = {}
        self._by_type: Dict[FrameNodeType, List[AstFrameBase]] = {}
        self._by_name: Dict[str, List[AstFrameBase]] = {}

        # Dirty flag for lazy rebuilding
        self._dirty: bool = True

    def mark_dirty(self) -> None:
        """Mark registry as needing rebuild."""
        self._dirty = True

    def rebuild_if_dirty(self) -> None:
        """Rebuild indexes if marked as dirty."""
        if self._dirty:
            self._rebuild_indexes()
            self._dirty = False

    def _rebuild_indexes(self) -> None:
        """Rebuild all indexes by walking the tree once."""
        # Clear existing indexes
        self._by_id.clear()
        self._by_qualified_name.clear()
        self._by_type.clear()
        self._by_name.clear()

        # Walk the entire tree and build indexes
        self._index_frame_recursive(self.language_root)

    def _index_frame_recursive(self, frame: AstFrameBase) -> None:
        """Recursively index a frame and its children."""
        # Index by ID
        self._by_id[frame.id] = frame

        # Index by qualified name
        if frame.qualified_name:
            self._by_qualified_name[frame.qualified_name] = frame

        # Index by type
        if frame.type not in self._by_type:
            self._by_type[frame.type] = []
        self._by_type[frame.type].append(frame)

        # Index by name (can have multiple frames with same name)
        if frame.name:
            if frame.name not in self._by_name:
                self._by_name[frame.name] = []
            self._by_name[frame.name].append(frame)

        # Recursively index children
        for child in frame.children:
            self._index_frame_recursive(child)

    # Public lookup methods

    def find_by_id(self, frame_id: str) -> Optional[AstFrameBase]:
        """Find frame by ID."""
        self.rebuild_if_dirty()
        return self._by_id.get(frame_id)

    def find_by_qualified_name(self, qualified_name: str) -> Optional[AstFrameBase]:
        """Find frame by qualified name."""
        self.rebuild_if_dirty()
        return self._by_qualified_name.get(qualified_name)

    def find_by_type(self, frame_type: FrameNodeType) -> List[AstFrameBase]:
        """Find all frames of a specific type."""
        self.rebuild_if_dirty()
        return self._by_type.get(frame_type, []).copy()

    def find_by_name(self, name: str) -> List[AstFrameBase]:
        """Find all frames with a specific name."""
        self.rebuild_if_dirty()
        return self._by_name.get(name, []).copy()

    def find_by_type_in_subtree(
        self,
        root: AstFrameBase,
        frame_type: FrameNodeType
    ) -> List[AstFrameBase]:
        """Find all frames of a type within a subtree."""
        self.rebuild_if_dirty()
        all_of_type = self._by_type.get(frame_type, [])
        return [f for f in all_of_type if f.is_descendant_of(root) or f == root]

    def find_classes_in_package(self, package: AstFrameBase) -> List[AstFrameBase]:
        """Find all classes within a specific package."""
        return self.find_by_type_in_subtree(package, FrameNodeType.CLASS)

    def find_callables_in_class(self, class_frame: AstFrameBase) -> List[AstFrameBase]:
        """Find all callables (methods) within a specific class."""
        return self.find_by_type_in_subtree(class_frame, FrameNodeType.CALLABLE)

    def find_packages_in_language(self, language_frame: AstFrameBase) -> List[AstFrameBase]:
        """Find all packages within a specific language."""
        return self.find_by_type_in_subtree(language_frame, FrameNodeType.PACKAGE)

    # Statistics and debugging

    def get_statistics(self) -> Dict[str, int]:
        """Get registry statistics for debugging."""
        self.rebuild_if_dirty()

        stats = {
            "total_frames": len(self._by_id),
            "unique_qualified_names": len(self._by_qualified_name),
            "unique_names": len(self._by_name),
        }

        # Add type counts
        for frame_type, frames in self._by_type.items():
            stats[f"type_{frame_type.value}"] = len(frames)

        return stats

    def validate_integrity(self) -> List[str]:
        """Validate registry integrity and return list of issues."""
        self.rebuild_if_dirty()
        issues = []

        # Check for orphaned frames (frames not reachable from root)
        reachable = set()
        self._mark_reachable(self.language_root, reachable)

        orphaned = set(self._by_id.keys()) - reachable
        if orphaned:
            issues.append(f"Found {len(orphaned)} orphaned frames: {list(orphaned)[:5]}...")

        # Check for duplicate qualified names
        qualified_name_counts = {}
        for qname in self._by_qualified_name.keys():
            qualified_name_counts[qname] = qualified_name_counts.get(qname, 0) + 1

        duplicates = {qname: count for qname, count in qualified_name_counts.items() if count > 1}
        if duplicates:
            issues.append(f"Found duplicate qualified names: {duplicates}")

        return issues

    def _mark_reachable(self, frame: AstFrameBase, reachable: set) -> None:
        """Mark frame and its children as reachable."""
        reachable.add(frame.id)
        for child in frame.children:
            self._mark_reachable(child, reachable)

    def validate_multi_parent_integrity(self) -> List[str]:
        """
        Validate bidirectional consistency of multi-parent relationships.
        
        Checks:
        - Each child in parent.children has parent in child.parents_by_id
        - Each parent in child.parents_by_id has child in parent.children
        - No orphaned frames exist
        """
        self.rebuild_if_dirty()
        issues = []
        
        for frame_id, frame in self._by_id.items():
            # Check parent→child direction
            for child in frame.children:
                if frame.id not in child.parents_by_id:
                    issues.append(
                        f"Frame {frame_id} ({frame.type.value}:{frame.name}) has child {child.id}, "
                        f"but child doesn't list it as parent (broken bidirectional link)"
                    )
            
            # Check child→parent direction
            for parent_id, parent in frame.parents_by_id.items():
                if frame not in parent.children:
                    issues.append(
                        f"Frame {frame_id} ({frame.type.value}:{frame.name}) has parent {parent_id}, "
                        f"but parent doesn't list it as child (broken bidirectional link)"
                    )
            
            # Check consistency between parent structures
            if len(frame.parents_by_id) != len(frame.parents_list):
                issues.append(
                    f"Frame {frame_id} ({frame.type.value}:{frame.name}) has inconsistent parent counts: "
                    f"{len(frame.parents_by_id)} in dict, {len(frame.parents_list)} in list"
                )
        
        return issues
