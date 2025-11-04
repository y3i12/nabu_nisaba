"""
Data structures for variable/field/parameter information.

These structures represent semantic information about fields and parameters
that are stored as STRUCT properties in KuzuDB rather than as separate nodes.
This avoids graph explosion while maintaining queryability.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FieldInfo:
    """
    Instance or static field information.

    Used for class member variables (instance fields, static fields, etc.)
    Stores as STRUCT in KuzuDB for efficient querying without node explosion.
    """
    name: str
    declared_type: Optional[str] = None
    line: int = 0
    confidence: float = 1.0
    is_static: bool = False  # Distinguish instance vs. class fields

    def to_dict(self):
        """
        Convert to dict for KuzuDB STRUCT.

        Empty strings used for None values to match STRUCT schema.
        """
        return {
            'name': self.name,
            'declared_type': self.declared_type or '',
            'line': self.line,
            'confidence': self.confidence
        }


@dataclass
class ParameterInfo:
    """
    Function/method parameter information.

    Used for callable parameters with type hints and default values.
    Stores as STRUCT in KuzuDB for efficient querying without node explosion.
    """
    name: str
    declared_type: Optional[str] = None
    default_value: Optional[str] = None
    position: int = 0

    def to_dict(self):
        """
        Convert to dict for KuzuDB STRUCT.

        Empty strings used for None values to match STRUCT schema.
        """
        return {
            'name': self.name,
            'declared_type': self.declared_type or '',
            'default_value': self.default_value or '',
            'position': self.position
        }
