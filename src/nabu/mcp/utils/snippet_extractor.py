"""Snippet extraction utility for FTS results."""

from typing import Any, Dict, List


def extract_snippets(
    content: str,
    keywords: str,
    context_lines: int = 2,
    max_snippets: int = 3
) -> List[Dict[str, Any]]:
    """
    Extract context windows around keyword matches in content.
    
    Args:
        content: Full text content to search
        keywords: Space-separated keywords to search for
        context_lines: Number of lines to show before/after each match
        max_snippets: Maximum number of snippets to return per content
        
    Returns:
        List of snippet dictionaries with line_start and context
        Example: [{"line_start": 75, "context": ["line1", "→ matched", "line3"]}]
    """
    if not content or not keywords:
        return []
    
    lines = content.split('\n')
    keyword_list = [kw.lower() for kw in keywords.split() if kw]
    
    if not keyword_list:
        return []
    
    snippets = []
    matched_lines = set()
    
    # Find all lines containing keywords
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in keyword_list):
            matched_lines.add(i)
    
    # Convert to sorted list and merge nearby matches
    if not matched_lines:
        return []
    
    sorted_matches = sorted(matched_lines)
    
    # Group nearby matches to avoid overlapping snippets
    groups = []
    current_group = [sorted_matches[0]]
    
    for match in sorted_matches[1:]:
        # If this match is within 2*context_lines of previous, add to current group
        if match - current_group[-1] <= (2 * context_lines + 1):
            current_group.append(match)
        else:
            groups.append(current_group)
            current_group = [match]
    groups.append(current_group)
    
    # Extract snippets for each group
    for group in groups[:max_snippets]:
        # Calculate window bounds
        start_line = max(0, min(group) - context_lines)
        end_line = min(len(lines), max(group) + context_lines + 1)
        
        # Build context with markers
        context = []
        for j in range(start_line, end_line):
            prefix = "→ " if j in matched_lines else "  "
            context.append(prefix + lines[j])
        
        snippets.append({
            "line_start": start_line + 1,  # 1-indexed for human readability
            "line_end": end_line,
            "context": context
        })
    
    return snippets
