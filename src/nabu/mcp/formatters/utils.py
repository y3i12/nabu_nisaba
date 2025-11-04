"""
Formatter utilities.

Helper functions for formatting tool outputs.
"""

from typing import Any, Dict


def format_resolution_alternatives(
    metadata: Dict[str, Any],
    target_name: str
) -> str:
    """
    Format resolution alternatives for markdown output.

    Used when FTS fuzzy resolution returns multiple candidates.
    Provides transparency about ambiguous matches and actionable suggestions.

    Args:
        metadata: Resolution metadata with alternatives
        target_name: Original target query

    Returns:
        Formatted markdown string, or empty if no alternatives
    """
    if not metadata or metadata.get('strategy') != 'fts_fuzzy':
        return ""

    lines = [
        f"\n**Multiple matches for \"{target_name}\"** (using best match)\n",
    ]

    alternatives = metadata.get('alternatives', [])
    if alternatives:
        lines.append("**Alternatives:**")
        for alt in alternatives:
            lines.append(
                f"- {alt['qualified_name']} @ {alt['location']}"
            )
            lines.append(
                f"  → Use: `show_structure(target=\"{alt['qualified_name']}\")`\n"
            )

    other_matches = metadata.get('other_matches', [])
    if other_matches:
        lines.append(f"\n**Other matches:** {', '.join(other_matches[:5])}")
        if len(other_matches) > 5:
            lines.append(f" (+{len(other_matches) - 5} more)")

    return '\n'.join(lines)
