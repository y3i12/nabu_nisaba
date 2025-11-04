"""
Incremental update system for nabu.

Enables efficient file-level updates using stable_id for change detection.
Achieves 3-5x speedup by updating only changed frames (20-30%) instead of
re-parsing entire codebase.

Components:
- diff_calculator: Compute frame differences using stable_id
- db_mutator: Execute database updates (delete/insert/update)
- relationship_repairer: Repair CALLS and IMPORTS edges
- metrics: Track update performance and stability
- updater: Orchestrator for incremental update workflow

Usage:
    from nabu.incremental import IncrementalUpdater
    
    updater = IncrementalUpdater(db_path="nabu.kuzu")
    result = updater.update_file("src/foo.py")
    
    print(f"Updated {result.frames_added + result.frames_deleted} frames")
    print(f"Preserved {result.frames_stable} frames ({result.stability_percentage:.1f}%)")
"""

from nabu.incremental.diff_calculator import FrameDiff, StableDiffCalculator
from nabu.incremental.db_mutator import DatabaseMutator, DeleteResult, InsertResult, InsertEdgeResult
from nabu.incremental.relationship_repairer import RelationshipRepairer, RepairResult
from nabu.incremental.metrics import UpdateMetricsCollector, UpdateMetric
from nabu.incremental.updater import IncrementalUpdater, UpdateResult

__all__ = [
    'FrameDiff',
    'StableDiffCalculator',
    'DatabaseMutator',
    'DeleteResult',
    'InsertResult',
    'InsertEdgeResult',
    'RelationshipRepairer',
    'RepairResult',
    'IncrementalUpdater',
    'UpdateResult',
    'UpdateMetricsCollector',
    'UpdateMetric',
]
