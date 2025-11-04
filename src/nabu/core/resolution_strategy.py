"""
Resolution Strategy Abstraction

Provides pluggable backend for symbol resolution, supporting both
in-memory (during initial parse) and database-backed (during incremental updates)
resolution strategies.

This eliminates code duplication between SymbolResolver (in-memory) and
RelationshipRepairer (database-backed) by extracting the common resolution
algorithm into a Strategy Pattern.
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
import logging

from nabu.core.frame_types import FrameNodeType


logger = logging.getLogger(__name__)


@dataclass
class ResolutionResult:
    """Result of a symbol resolution operation."""
    frame_id: str
    qualified_name: str
    confidence: float

    @classmethod
    def from_frame(cls, frame) -> 'ResolutionResult':
        """
        Create from AstFrameBase instance.

        Args:
            frame: AstFrameBase instance

        Returns:
            ResolutionResult with frame's id, qualified_name, and confidence
        """
        return cls(
            frame_id=frame.id,
            qualified_name=frame.qualified_name,
            confidence=frame.confidence
        )


class ResolutionStrategy(ABC):
    """
    Abstract strategy for resolving symbol names to frames.

    Supports two implementations:
    - MemoryResolutionStrategy: Uses in-memory registries (initial parse)
    - DatabaseResolutionStrategy: Uses KuzuDB queries (incremental updates)

    The 3-strategy resolution pattern:
    1. Exact match on qualified name
    2. Context-based match (using package context)
    3. Partial match (last resort, lowest confidence)
    """

    @abstractmethod
    def resolve_callable_exact(self, qualified_name: str) -> Optional[ResolutionResult]:
        """
        Resolve callable by exact qualified name match.

        Args:
            qualified_name: Full qualified name (e.g., 'nabu.core.FrameStack.push')

        Returns:
            ResolutionResult if found, None otherwise
        """
        pass

    @abstractmethod
    def resolve_callable_with_context(
        self,
        simple_name: str,
        package_context: str
    ) -> Optional[ResolutionResult]:
        """
        Resolve callable using package context.

        Args:
            simple_name: Simple callable name (e.g., 'push')
            package_context: Package qualified name (e.g., 'nabu.core.FrameStack')

        Returns:
            ResolutionResult if found, None otherwise
        """
        pass

    @abstractmethod
    def resolve_callable_partial(self, simple_name: str) -> Optional[ResolutionResult]:
        """
        Resolve callable by partial match (last resort, lowest confidence).

        Args:
            simple_name: Simple callable name (e.g., 'push')

        Returns:
            ResolutionResult for shortest matching qualified name, None if not found
        """
        pass

    @abstractmethod
    def resolve_class_exact(self, qualified_name: str) -> Optional[ResolutionResult]:
        """
        Resolve class by exact qualified name match.

        Args:
            qualified_name: Full qualified name (e.g., 'nabu.core.AstFrameBase')

        Returns:
            ResolutionResult if found, None otherwise
        """
        pass

    @abstractmethod
    def resolve_class_partial(self, simple_name: str) -> Optional[ResolutionResult]:
        """
        Resolve class by partial match (shortest qualified name).

        Args:
            simple_name: Simple class name (e.g., 'AstFrameBase')

        Returns:
            ResolutionResult for shortest matching qualified name, None if not found
        """
        pass

    @abstractmethod
    def get_package_qualified_name(self, frame_id: str) -> Optional[str]:
        """
        Get package qualified name for a frame.

        Args:
            frame_id: Frame identifier

        Returns:
            Package qualified name or None
        """
        pass


class MemoryResolutionStrategy(ResolutionStrategy):
    """
    Resolution strategy using in-memory registries.

    Used during initial parse when all frames are in memory via CodebaseContext.
    """

    def __init__(self, context):
        """
        Initialize with CodebaseContext.

        Args:
            context: CodebaseContext containing callable_registry, class_registry, etc.
        """
        self.context = context

    def resolve_callable_exact(self, qualified_name: str) -> Optional[ResolutionResult]:
        """Lookup in context.callable_registry."""
        frame = self.context.callable_registry.get(qualified_name)
        return ResolutionResult.from_frame(frame) if frame else None

    def resolve_callable_with_context(
        self,
        simple_name: str,
        package_context: str
    ) -> Optional[ResolutionResult]:
        """Build potential qualified name and lookup."""
        potential_qname = f"{package_context}.{simple_name}"
        frame = self.context.callable_registry.get(potential_qname)
        return ResolutionResult.from_frame(frame) if frame else None

    def resolve_callable_partial(self, simple_name: str) -> Optional[ResolutionResult]:
        """Iterate registry, find shortest match."""
        for qname, frame in self.context.callable_registry.items():
            if qname.endswith(f".{simple_name}") or qname == simple_name:
                # Found a potential match - return it
                # Note: In production might want to rank by confidence
                return ResolutionResult.from_frame(frame)
        return None

    def resolve_class_exact(self, qualified_name: str) -> Optional[ResolutionResult]:
        """Lookup in context.class_registry."""
        frame = self.context.class_registry.get(qualified_name)
        return ResolutionResult.from_frame(frame) if frame else None

    def resolve_class_partial(self, simple_name: str) -> Optional[ResolutionResult]:
        """Iterate class_registry, find shortest match."""
        matches = []
        for qname, frame in self.context.class_registry.items():
            if qname.endswith(f".{simple_name}") or qname == simple_name:
                matches.append((qname, frame))

        if matches:
            # Return shortest qualified name
            shortest = min(matches, key=lambda x: len(x[0]))
            return ResolutionResult.from_frame(shortest[1])
        return None

    def get_package_qualified_name(self, frame_id: str) -> Optional[str]:
        """
        Walk up frame_stack to find parent PACKAGE.

        Args:
            frame_id: ID of frame to find package for

        Returns:
            Package qualified name or None
        """
        frame = self._find_frame_by_id(frame_id)
        if not frame:
            return None

        # Walk up hierarchy looking for PACKAGE
        current = frame.parent  # Use frame.parent property instead of frame_stack.get_parent()
        visited = set()  # Avoid infinite loops

        while current:
            # Prevent infinite loops in multi-parent graphs
            if id(current) in visited:
                break
            visited.add(id(current))

            if current.type == FrameNodeType.PACKAGE:
                return current.qualified_name

            # Move to next parent
            current = current.parent

        return None

    def _find_frame_by_id(self, frame_id: str):
        """
        Helper to find frame by ID across all registries.

        Args:
            frame_id: Frame ID to search for

        Returns:
            AstFrameBase if found, None otherwise
        """
        # Check callable_registry
        for frame in self.context.callable_registry.values():
            if frame.id == frame_id:
                return frame
        # Check class_registry
        for frame in self.context.class_registry.values():
            if frame.id == frame_id:
                return frame
        return None


class DatabaseResolutionStrategy(ResolutionStrategy):
    """
    Resolution strategy using KuzuDB queries.

    Used during incremental updates when frames are in database.
    """

    def __init__(self, conn):
        """
        Initialize with KuzuDB connection.

        Args:
            conn: kuzu.Connection instance
        """
        self.conn = conn

    def resolve_callable_exact(self, qualified_name: str) -> Optional[ResolutionResult]:
        """Query database for exact match."""
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {type: 'CALLABLE', qualified_name: $qname})
                RETURN f.id, f.qualified_name, f.confidence
                LIMIT 1
            """, {'qname': qualified_name})

            rows = list(result)
            if rows:
                return ResolutionResult(
                    frame_id=rows[0][0],
                    qualified_name=rows[0][1],
                    confidence=rows[0][2]
                )
        except Exception as e:
            logger.debug(f"Exact callable match query failed: {e}")
        return None

    def resolve_callable_with_context(
        self,
        simple_name: str,
        package_context: str
    ) -> Optional[ResolutionResult]:
        """Build potential qualified name and query."""
        potential_qname = f"{package_context}.{simple_name}"
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {type: 'CALLABLE', qualified_name: $qname})
                RETURN f.id, f.qualified_name, f.confidence
                LIMIT 1
            """, {'qname': potential_qname})

            rows = list(result)
            if rows:
                return ResolutionResult(
                    frame_id=rows[0][0],
                    qualified_name=rows[0][1],
                    confidence=rows[0][2]
                )
        except Exception as e:
            logger.debug(f"Context-based callable match query failed: {e}")
        return None

    def resolve_callable_partial(self, simple_name: str) -> Optional[ResolutionResult]:
        """Query with ENDS WITH clause, return shortest."""
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {type: 'CALLABLE'})
                WHERE f.qualified_name ENDS WITH $suffix
                RETURN f.id, f.qualified_name, f.confidence
            """, {'suffix': f".{simple_name}"})

            rows = list(result)
            if rows:
                # Sort by qualified_name length (shortest first)
                sorted_rows = sorted(rows, key=lambda r: len(r[1]))
                return ResolutionResult(
                    frame_id=sorted_rows[0][0],
                    qualified_name=sorted_rows[0][1],
                    confidence=sorted_rows[0][2]
                )
        except Exception as e:
            logger.debug(f"Partial callable match query failed: {e}")
        return None

    def resolve_class_exact(self, qualified_name: str) -> Optional[ResolutionResult]:
        """Query database for exact class match."""
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {type: 'CLASS', qualified_name: $qname})
                RETURN f.id, f.qualified_name, f.confidence
                LIMIT 1
            """, {'qname': qualified_name})

            rows = list(result)
            if rows:
                return ResolutionResult(
                    frame_id=rows[0][0],
                    qualified_name=rows[0][1],
                    confidence=rows[0][2]
                )
        except Exception as e:
            logger.debug(f"Exact class match query failed: {e}")
        return None

    def resolve_class_partial(self, simple_name: str) -> Optional[ResolutionResult]:
        """Query with ENDS WITH, return shortest."""
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {type: 'CLASS'})
                WHERE f.qualified_name ENDS WITH $suffix
                RETURN f.id, f.qualified_name, f.confidence
            """, {'suffix': f".{simple_name}"})

            rows = list(result)
            if rows:
                sorted_rows = sorted(rows, key=lambda r: len(r[1]))
                return ResolutionResult(
                    frame_id=sorted_rows[0][0],
                    qualified_name=sorted_rows[0][1],
                    confidence=sorted_rows[0][2]
                )
        except Exception as e:
            logger.debug(f"Partial class match query failed: {e}")
        return None

    def get_package_qualified_name(self, frame_id: str) -> Optional[str]:
        """Query database to find parent PACKAGE."""
        try:
            result = self.conn.execute("""
                MATCH (f:Frame {id: $fid})<-[:Edge* {type: 'CONTAINS'}]-(pkg:Frame {type: 'PACKAGE'})
                RETURN pkg.qualified_name
                LIMIT 1
            """, {'fid': frame_id})

            rows = list(result)
            if rows:
                return rows[0][0]
        except Exception as e:
            logger.debug(f"Package qualified name query failed: {e}")
        return None
