"""
Stable ID difference calculator for incremental updates.

Compares old frames (from database) vs new frames (from parser) to determine
which frames were deleted, added, or remained stable.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Any, Optional
from nabu.core.frames import AstFrameBase


@dataclass
class FrameDiff:
    """
    Result of comparing old vs new frames by id.
    
    Attributes:
        deleted_ids: Frames removed from code (in old, not in new)
        added_frames: New frames in code (not in old, in new)
        stable_ids: Unchanged frames (in both old and new)
        
        old_id_to_frame_data: Mapping from id to database frame data
        new_id_to_frame: Mapping from id to parsed frame object
        
        total_old: Count of frames in old version
        total_new: Count of frames in new version
        stability_percentage: Percentage of frames that remained stable
    """
    deleted_ids: Set[str]
    added_frames: List[AstFrameBase]
    stable_ids: Set[str]
    
    old_id_to_frame_data: Dict[str, dict]
    new_id_to_frame: Dict[str, AstFrameBase]
    
    total_old: int
    total_new: int
    stability_percentage: float
    
    @property
    def deleted_count(self) -> int:
        """Number of deleted frames."""
        return len(self.deleted_ids)
    
    @property
    def added_count(self) -> int:
        """Number of added frames."""
        return len(self.added_frames)
    
    @property
    def stable_count(self) -> int:
        """Number of stable (unchanged) frames."""
        return len(self.stable_ids)
    
    @property
    def churn_percentage(self) -> float:
        """Percentage of frames that changed (deleted + added)."""
        if self.total_new == 0:
            return 0.0
        return ((self.deleted_count + self.added_count) / self.total_new) * 100.0


class StableDiffCalculator:
    """
    Calculate differences between old and new frames using stable_id.
    
    The diff algorithm compares stable_ids to determine:
    - Which frames were deleted (removed from code)
    - Which frames were added (new in code)
    - Which frames are stable (unchanged)
    
    This enables selective database updates instead of full re-parsing.
    """
    
    def compute_diff(
        self,
        old_frames_data: List[Dict[str, Any]],
        new_frames: List[AstFrameBase]
    ) -> FrameDiff:
        """
        Compute diff between old and new frames by id.
        
        Args:
            old_frames_data: Frame data from database (dicts with id)
            new_frames: Parsed frames from updated file
            
        Returns:
            FrameDiff with deleted, added, and stable frame sets
            
        Algorithm:
            1. Build old_map: {id: frame_data}
            2. Build new_map: {id: frame}
            3. Compute set operations (deleted = old - new, etc.)
            4. Calculate stability metrics
        """
        # Build mapping from old frames (database)
        old_id_to_frame_data: Dict[str, dict] = {}
        for frame_data in old_frames_data:
            frame_id = frame_data.get('id')
            if frame_id:
                old_id_to_frame_data[frame_id] = frame_data
        
        # Build mapping from new frames (parsed)
        new_id_to_frame: Dict[str, AstFrameBase] = {}
        for frame in new_frames:
            if frame.id:
                new_id_to_frame[frame.id] = frame
        
        # Compute set operations
        old_ids = set(old_id_to_frame_data.keys())
        new_ids = set(new_id_to_frame.keys())
        
        deleted_ids = old_ids - new_ids
        added_ids = new_ids - old_ids
        stable_ids = old_ids & new_ids
        
        # Extract added frames
        added_frames = [new_id_to_frame[fid] for fid in added_ids]
        
        # Calculate metrics
        total_old = len(old_ids)
        total_new = len(new_ids)
        stability_percentage = (len(stable_ids) / total_new * 100.0) if total_new > 0 else 0.0
        
        return FrameDiff(
            deleted_ids=deleted_ids,
            added_frames=added_frames,
            stable_ids=stable_ids,
            old_id_to_frame_data=old_id_to_frame_data,
            new_id_to_frame=new_id_to_frame,
            total_old=total_old,
            total_new=total_new,
            stability_percentage=stability_percentage
        )
    
    def collect_all_frames(self, root_frame: AstFrameBase) -> List[AstFrameBase]:
        """
        Collect all frames from hierarchy (DFS traversal).
        
        Args:
            root_frame: Root of frame hierarchy (e.g., codebase frame)
            
        Returns:
            Flat list of all frames in hierarchy
            
        Note:
            Uses visited set to handle multi-parent graphs (same frame
            appearing as child of multiple parents).
            
            Filters out external frames (provenance='external') to prevent
            including imported/referenced frames from other files.
        """
        all_frames: List[AstFrameBase] = []
        visited: Set[int] = set()
        
        def traverse(frame: AstFrameBase):
            if frame.id in visited:
                return
            visited.add(frame.id)
            
            # Filter out external frames - they belong to other files
            if frame.provenance != 'external':
                all_frames.append(frame)
            
            for child in frame.children:
                traverse(child)
        
        traverse(root_frame)
        return all_frames
