"""
Metrics collection for incremental updates.

Tracks update operations to provide insights into:
- Stability trends over time
- Performance characteristics
- Edge repair effectiveness
- Error patterns

Usage:
    collector = UpdateMetricsCollector()
    
    # After each update
    collector.record_update(result)
    
    # Get statistics
    stats = collector.get_statistics()
    print(f"Average stability: {stats['avg_stability']:.1f}%")
    
    # Export for analysis
    collector.export_to_json("metrics.json")
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
import statistics


@dataclass
class UpdateMetric:
    """Single update operation metric."""
    timestamp: float
    file_path: str
    success: bool
    
    # Frame changes
    frames_deleted: int
    frames_added: int
    frames_stable: int
    stability_percentage: float
    
    # Edge changes
    edges_deleted: int
    edges_added: int
    
    # Performance
    parse_time_ms: float
    diff_time_ms: float
    database_time_ms: float
    total_time_ms: float
    
    # Errors/warnings
    error_count: int
    warning_count: int


class UpdateMetricsCollector:
    """
    Collect and analyze incremental update metrics.
    
    Thread-safe for single-process usage.
    Not designed for multi-process scenarios.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history
        self.metrics: List[UpdateMetric] = []
        self._file_metrics: Dict[str, List[UpdateMetric]] = {}
    
    def record_update(self, result) -> None:
        """
        Record an update result.
        
        Args:
            result: UpdateResult from IncrementalUpdater
        """
        metric = UpdateMetric(
            timestamp=time.time(),
            file_path=result.file_path,
            success=result.success,
            frames_deleted=result.frames_deleted,
            frames_added=result.frames_added,
            frames_stable=result.frames_stable,
            stability_percentage=result.stability_percentage,
            edges_deleted=result.edges_deleted,
            edges_added=result.edges_added,
            parse_time_ms=result.parse_time_ms,
            diff_time_ms=result.diff_time_ms,
            database_time_ms=result.database_time_ms,
            total_time_ms=result.total_time_ms,
            error_count=len(result.errors) if result.errors else 0,
            warning_count=len(result.warnings) if result.warnings else 0
        )
        
        # Add to global history
        self.metrics.append(metric)
        
        # Add to per-file history
        if result.file_path not in self._file_metrics:
            self._file_metrics[result.file_path] = []
        self._file_metrics[result.file_path].append(metric)
        
        # Trim if exceeds max history
        if len(self.metrics) > self.max_history:
            oldest = self.metrics[0]
            self.metrics.pop(0)
            
            # Also trim from file metrics
            if oldest.file_path in self._file_metrics:
                file_list = self._file_metrics[oldest.file_path]
                if file_list and file_list[0].timestamp == oldest.timestamp:
                    file_list.pop(0)
    
    def get_statistics(self) -> Dict:
        """
        Get aggregated statistics across all updates.
        
        Returns:
            Dictionary with statistics
        """
        if not self.metrics:
            return {
                'total_updates': 0,
                'success_rate': 0.0,
                'avg_stability': 0.0,
                'avg_time_ms': 0.0
            }
        
        successful = [m for m in self.metrics if m.success]
        
        stats = {
            'total_updates': len(self.metrics),
            'successful_updates': len(successful),
            'failed_updates': len(self.metrics) - len(successful),
            'success_rate': (len(successful) / len(self.metrics)) * 100,
            
            # Stability metrics (successful only)
            'avg_stability': statistics.mean(m.stability_percentage for m in successful) if successful else 0.0,
            'median_stability': statistics.median(m.stability_percentage for m in successful) if successful else 0.0,
            'min_stability': min(m.stability_percentage for m in successful) if successful else 0.0,
            'max_stability': max(m.stability_percentage for m in successful) if successful else 0.0,
            
            # Performance metrics (successful only)
            'avg_time_ms': statistics.mean(m.total_time_ms for m in successful) if successful else 0.0,
            'median_time_ms': statistics.median(m.total_time_ms for m in successful) if successful else 0.0,
            'p95_time_ms': self._percentile([m.total_time_ms for m in successful], 95) if successful else 0.0,
            'p99_time_ms': self._percentile([m.total_time_ms for m in successful], 99) if successful else 0.0,
            
            # Frame change metrics
            'avg_frames_changed': statistics.mean(
                m.frames_deleted + m.frames_added for m in successful
            ) if successful else 0.0,
            
            # Edge repair metrics
            'total_edges_added': sum(m.edges_added for m in successful),
            'total_edges_deleted': sum(m.edges_deleted for m in successful),
            'avg_edges_per_update': statistics.mean(m.edges_added for m in successful) if successful else 0.0,
            
            # Error metrics
            'total_errors': sum(m.error_count for m in self.metrics),
            'total_warnings': sum(m.warning_count for m in self.metrics),
        }
        
        return stats
    
    def get_file_statistics(self, file_path: str) -> Optional[Dict]:
        """
        Get statistics for a specific file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Statistics dict or None if file not found
        """
        if file_path not in self._file_metrics:
            return None
        
        metrics = self._file_metrics[file_path]
        if not metrics:
            return None
        
        successful = [m for m in metrics if m.success]
        
        return {
            'file_path': file_path,
            'update_count': len(metrics),
            'avg_stability': statistics.mean(m.stability_percentage for m in successful) if successful else 0.0,
            'avg_time_ms': statistics.mean(m.total_time_ms for m in successful) if successful else 0.0,
            'last_updated': max(m.timestamp for m in metrics),
        }
    
    def get_stability_trend(self, window: int = 10) -> List[float]:
        """
        Get stability percentage trend over recent updates.
        
        Args:
            window: Number of recent updates to include
            
        Returns:
            List of stability percentages (most recent first)
        """
        recent = [m for m in self.metrics[-window:] if m.success]
        return [m.stability_percentage for m in reversed(recent)]
    
    def get_performance_trend(self, window: int = 10) -> List[float]:
        """
        Get performance (total time) trend over recent updates.
        
        Args:
            window: Number of recent updates to include
            
        Returns:
            List of total_time_ms values (most recent first)
        """
        recent = [m for m in self.metrics[-window:] if m.success]
        return [m.total_time_ms for m in reversed(recent)]
    
    def get_most_frequently_updated_files(self, top_n: int = 10) -> List[tuple]:
        """
        Get most frequently updated files.
        
        Args:
            top_n: Number of files to return
            
        Returns:
            List of (file_path, update_count) tuples
        """
        file_counts = {
            file_path: len(metrics)
            for file_path, metrics in self._file_metrics.items()
        }
        
        sorted_files = sorted(
            file_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_files[:top_n]
    
    def get_slowest_updates(self, top_n: int = 10) -> List[UpdateMetric]:
        """
        Get slowest update operations.
        
        Args:
            top_n: Number of updates to return
            
        Returns:
            List of UpdateMetric sorted by total_time_ms descending
        """
        successful = [m for m in self.metrics if m.success]
        sorted_metrics = sorted(
            successful,
            key=lambda m: m.total_time_ms,
            reverse=True
        )
        return sorted_metrics[:top_n]
    
    def get_least_stable_updates(self, top_n: int = 10) -> List[UpdateMetric]:
        """
        Get updates with lowest stability.
        
        Args:
            top_n: Number of updates to return
            
        Returns:
            List of UpdateMetric sorted by stability_percentage ascending
        """
        successful = [m for m in self.metrics if m.success]
        sorted_metrics = sorted(
            successful,
            key=lambda m: m.stability_percentage
        )
        return sorted_metrics[:top_n]
    
    def export_to_json(self, file_path: str) -> None:
        """
        Export metrics to JSON file.
        
        Args:
            file_path: Output file path
        """
        data = {
            'exported_at': time.time(),
            'total_metrics': len(self.metrics),
            'metrics': [asdict(m) for m in self.metrics],
            'statistics': self.get_statistics()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_json(self, file_path: str) -> None:
        """
        Load metrics from JSON file.
        
        Args:
            file_path: Input file path
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.metrics = [
            UpdateMetric(**metric_dict)
            for metric_dict in data['metrics']
        ]
        
        # Rebuild file metrics index
        self._file_metrics.clear()
        for metric in self.metrics:
            if metric.file_path not in self._file_metrics:
                self._file_metrics[metric.file_path] = []
            self._file_metrics[metric.file_path].append(metric)
    
    def print_summary(self) -> None:
        """Print human-readable summary to stdout."""
        stats = self.get_statistics()
        
        print("Incremental Update Metrics Summary")
        print("=" * 60)
        print(f"Total updates:      {stats['total_updates']}")
        print(f"Success rate:       {stats['success_rate']:.1f}%")
        print()
        print("Stability:")
        print(f"  Average:          {stats['avg_stability']:.1f}%")
        print(f"  Median:           {stats['median_stability']:.1f}%")
        print(f"  Range:            {stats['min_stability']:.1f}% - {stats['max_stability']:.1f}%")
        print()
        print("Performance:")
        print(f"  Average time:     {stats['avg_time_ms']:.1f}ms")
        print(f"  Median time:      {stats['median_time_ms']:.1f}ms")
        print(f"  95th percentile:  {stats['p95_time_ms']:.1f}ms")
        print(f"  99th percentile:  {stats['p99_time_ms']:.1f}ms")
        print()
        print("Edge Repair:")
        print(f"  Total edges added: {stats['total_edges_added']}")
        print(f"  Avg per update:    {stats['avg_edges_per_update']:.1f}")
        print()
        
        if stats['total_errors'] > 0 or stats['total_warnings'] > 0:
            print("Issues:")
            print(f"  Errors:           {stats['total_errors']}")
            print(f"  Warnings:         {stats['total_warnings']}")
    
    @staticmethod
    def _percentile(values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


# Global instance for convenience
_global_collector: Optional[UpdateMetricsCollector] = None


def get_global_collector() -> UpdateMetricsCollector:
    """Get or create global metrics collector."""
    global _global_collector
    if _global_collector is None:
        _global_collector = UpdateMetricsCollector()
    return _global_collector


def record_update(result) -> None:
    """Convenience function to record update in global collector."""
    get_global_collector().record_update(result)


def get_statistics() -> Dict:
    """Convenience function to get statistics from global collector."""
    return get_global_collector().get_statistics()


def print_summary() -> None:
    """Convenience function to print summary from global collector."""
    get_global_collector().print_summary()
