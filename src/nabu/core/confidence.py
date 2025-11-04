"""
Confidence System for Uncertain Symbol Resolution

This enables building an imperfect but useful system.

Addresses the need for handling:
- Import resolution uncertainty
- Type inference confidence
- Parse failure graceful degradation
- Cross-reference resolution quality
"""

from typing import Dict, Any, Optional
from nabu.core.frame_types import EdgeType, ConfidenceTier
from nabu.core.frames import AstFrameBase


class ConfidenceCalculator:
    """
    Calculates confidence based on resolution context.
    """

    @staticmethod
    def calculate_frame_confidence(
        frame: AstFrameBase,
        resolution_pass: int,
        provenance: str,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate confidence for a frame based on how it was created.

        Confidence levels:
        - Direct parsing: 1.0
        - Import resolution: 0.8
        - Type inference: 0.3-0.6
        - Fuzzy resolution: 0.1-0.3
        - Parse failures: 0.1
        """
        if resolution_pass == 1:  # Direct parsing
            if provenance == "parsed":
                return 1.0  # Directly parsed from AST
            elif provenance == "imported":
                return 0.9  # Created from import/declaration
            elif provenance == "parse_failed":
                return 0.1  # Minimal frame created on failure

        elif resolution_pass == 2:  # Cross-reference resolution
            if provenance == "imported":
                return 0.8  # Import statement found
            elif provenance == "inferred":
                return 0.6  # Type inference with good evidence
            elif provenance == "external":
                return 0.7  # External library (known)

        elif resolution_pass == 3:  # Fuzzy resolution
            if provenance == "inferred":
                return 0.3  # Best guess based on patterns
            elif provenance == "unknown_import":
                return 0.2  # Unknown module import

        elif resolution_pass >= 4:  # Speculative resolution
            return 0.1  # Last resort guessing

        return 0.1  # Default minimum confidence

    @staticmethod
    def calculate_edge_confidence(
        type: EdgeType,
        source_confidence: float,
        target_confidence: float
    ) -> float:
        """
        Calculate edge confidence based on source and target confidence.

        Edge confidence = min(source, target) * type_multiplier
        Chain is only as strong as the weakest link.
        """
        base_confidence = min(source_confidence, target_confidence)

        # Edge type multipliers
        multipliers = {
            EdgeType.CONTAINS: 1.0,      # Direct containment - highest confidence
            EdgeType.INHERITS: 0.95,     # Inheritance - very high if found
            EdgeType.IMPORTS: 0.9,       # Import - high confidence if detected
            EdgeType.CALLS: 0.85,        # Function calls - good confidence
            EdgeType.IMPLEMENTS: 0.9,    # Interface implementation
            EdgeType.USES: 0.80,         # Field usage - heuristic-based detection
        }

        multiplier = multipliers.get(type, 0.7)  # Default for unknown types
        return base_confidence * multiplier

    @staticmethod
    def calculate_tier(confidence: float) -> ConfidenceTier:
        """Convert confidence value to tier for simpler queries."""
        if confidence >= 0.8:
            return ConfidenceTier.HIGH
        elif confidence >= 0.5:
            return ConfidenceTier.MEDIUM
        elif confidence >= 0.2:
            return ConfidenceTier.LOW
        else:
            return ConfidenceTier.SPECULATIVE

    @staticmethod
    def adjust_confidence_for_scope_distance(
        base_confidence: float,
        scope_distance: int
    ) -> float:
        """
        Adjust confidence based on scope distance.

        Symbol resolution becomes less certain as we traverse up the scope chain.
        Used in enhanced frame stack for symbol resolution.
        """
        # Confidence decreases by 5% per scope level
        decay_factor = 0.95 ** scope_distance
        return base_confidence * decay_factor


class ConfidenceContext:
    """
    Context for tracking confidence during parsing.

    Manages the current resolution pass and provides context
    for confidence calculations.
    """

    def __init__(self):
        self.current_pass: int = 1
        self.context_data: Dict[str, Any] = {}

    def set_pass(self, pass_number: int) -> None:
        """Set the current resolution pass."""
        self.current_pass = pass_number

    def add_context(self, key: str, value: Any) -> None:
        """Add context information for confidence calculations."""
        self.context_data[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context information."""
        return self.context_data.get(key, default)