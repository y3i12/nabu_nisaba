"""
Pattern-based confidence adjustments for field usage detection.

Different detection patterns have different reliability levels.
These multipliers are applied AFTER the base USES edge confidence (0.80).
"""

FIELD_USAGE_PATTERN_ADJUSTMENTS = {
    # High confidence - explicit self/this reference
    "explicit": 1.0,                 # 0.80 * 1.0 = 0.80 (HIGH tier)
    
    # Medium-low confidence - uppercase heuristic for static fields
    "uppercase_heuristic": 0.85,     # 0.80 * 0.85 = 0.68 (MEDIUM tier)
    
    # Low confidence - qualified identifier without class verification
    "qualified_static": 0.70,        # 0.80 * 0.70 = 0.56 (MEDIUM tier)
    
    # Medium confidence - regex-based extraction
    "regex_based": 0.88,             # 0.80 * 0.88 = 0.70 (MEDIUM tier)
}


def adjust_field_usage_confidence(base_confidence: float, pattern_type: str) -> float:
    """
    Adjust confidence based on field usage detection pattern.
    
    Args:
        base_confidence: Base USES edge confidence (typically 0.80)
        pattern_type: Pattern used to detect field usage
        
    Returns:
        Adjusted confidence value
    """
    multiplier = FIELD_USAGE_PATTERN_ADJUSTMENTS.get(pattern_type, 1.0)
    return base_confidence * multiplier
