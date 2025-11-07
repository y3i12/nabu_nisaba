"""
Explore project markdown formatter.

Compact markdown formatter for explore_project tool output.
"""

from typing import Any, Dict
from pathlib import Path
from ..tool_base import BaseToolMarkdownFormatter


class ExploreProjectMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Compact markdown formatter for explore_project tool output.

    Implements token-efficient format with FQNs and frame IDs for querying.
    Achieves ~70% token reduction compared to generic formatting while
    maintaining full information content.
    """

    def _trim_qualified_name(self, qualified_name: str) -> str:
        """
        Remove verbose prefix from qualified names for readability.

        Example:
            nabu_nisaba.python_root.nabu.core.create_node_context_from_raw_node
            → nabu.core.create_node_context_from_raw_node
        """
        prefix = "nabu_nisaba.python_root."
        if qualified_name.startswith(prefix):
            return qualified_name[len(prefix):]

        # Also handle language-specific prefixes (cpp_root, java_root, perl_root)
        for lang_prefix in ["cpp_root::", "java_root.", "perl_root::"]:
            full_prefix = f"nabu_nisaba.{lang_prefix}"
            if qualified_name.startswith(full_prefix):
                return qualified_name[len("nabu_nisaba."):]

        return qualified_name

    def format(self, data: Dict[str, Any],) -> str:
        """Format explore_project output with stratified sampling."""
        project_stats = data.get("project_stats", {})
        languages = project_stats.get("languages", {})
        all_packages = data.get("top_packages", [])  # Now contains ALL packages
        entry_points = data.get("entry_points", [])
        all_classes = data.get("most_connected_classes", [])  # Now contains ALL classes

        lines = []

        # Header
        lines.append("# Project Overview")
        lines.append("")

        # Statistics - single line
        total_frames = project_stats.get("total_frames", 0)
        total_files = project_stats.get("total_files", 0)
        lang_count = project_stats.get("language_count", 0)
        lines.append("## Statistics")
        lines.append(f"Total Frames: {total_frames} | Files: {total_files} | Languages: {lang_count}")
        lines.append("")

        # Language Breakdown - compact inline
        lines.append("## Language Breakdown")
        if languages:
            lang_parts = []
            for lang, stats in languages.items():
                frames = stats.get("frames", 0)
                files = stats.get("files", 0)
                lang_display = lang if lang else "(unknown)"
                lang_parts.append(f"{lang_display} ({frames} frames, {files} files)")
            lines.append(" | ".join(lang_parts))
        else:
            lines.append("No language data")
        lines.append("")

        # Package Distribution (stratified)
        lines.append(f"## Package Distribution ({len(all_packages)} total packages)")
        lines.append("")
        if all_packages:
            # Define buckets
            large_pkgs = [p for p in all_packages if p.get("child_count", 0) >= 30]
            medium_pkgs = [p for p in all_packages if 10 <= p.get("child_count", 0) < 30]
            small_pkgs = [p for p in all_packages if p.get("child_count", 0) < 10]

            # Large packages
            if large_pkgs:
                lines.append("**Large (30+ children):**")
                sample = large_pkgs[:5]  # Show max 5
                names = [f"{p['name']} [{p['child_count']}]" for p in sample]
                if len(large_pkgs) > 5:
                    names.append(f"... ({len(large_pkgs) - 5} more)")
                lines.append(", ".join(names))
                lines.append("")

            # Medium packages
            if medium_pkgs:
                lines.append("**Medium (10-29 children):**")
                sample = medium_pkgs[:8]  # Show max 8
                names = [f"{p['name']} [{p['child_count']}]" for p in sample]
                if len(medium_pkgs) > 8:
                    names.append(f"... ({len(medium_pkgs) - 8} more)")
                lines.append(", ".join(names))
                lines.append("")

            # Small packages
            if small_pkgs:
                lines.append("**Small (<10 children):**")
                sample = small_pkgs[:5]  # Show max 5
                names = [f"{p['name']} [{p['child_count']}]" for p in sample]
                if len(small_pkgs) > 5:
                    names.append(f"... ({len(small_pkgs) - 5} more)")
                lines.append(", ".join(names))
                lines.append("")

            lines.append("*Tip: Explore with `show_structure(target='<package_name>')`*")
        else:
            lines.append("No packages found")
        lines.append("")

        # Entry Points (unchanged - keep top 10)
        lines.append("## Entry Points (key callables)")
        if entry_points:
            for entry in entry_points:
                name = entry.get("name", "unknown")
                location = entry.get("location", "unknown")

                # Show just module name for context if available
                module_name = Path(entry.get("file_path", "")).stem
                lines.append(f"{name} ({module_name}) @ {location}")
        else:
            lines.append("No entry points found")
        lines.append("")

        # Class Connectivity Distribution (stratified)
        lines.append(f"## Class Connectivity Distribution ({len(all_classes)} classes analyzed)")
        lines.append("")
        lines.append("*Format: [total:in/out] where in=incoming edges, out=outgoing edges*")
        lines.append("")
        if all_classes:
            # Define buckets
            highly_connected = [c for c in all_classes if c.get("total_connections", 0) >= 30]
            moderately_connected = [c for c in all_classes if 20 <= c.get("total_connections", 0) < 30]
            connected = [c for c in all_classes if 15 <= c.get("total_connections", 0) < 20]
            lightly_connected = [c for c in all_classes if 5 <= c.get("total_connections", 0) < 15]
            minimal = [c for c in all_classes if c.get("total_connections", 0) < 5]

            # Highly connected
            if highly_connected:
                lines.append("**Highly Connected (30+):**")
                sample = highly_connected[:5]
                names = [f"{c['name']} [{c['total_connections']}:{c['incoming_edges']}/{c['outgoing_edges']}]"
                         for c in sample]
                if len(highly_connected) > 5:
                    names.append(f"... ({len(highly_connected) - 5} more)")
                lines.append(", ".join(names))
                lines.append("")

            # Moderately connected
            if moderately_connected:
                lines.append("**Moderately Connected (20-29):**")
                sample = moderately_connected[:5]
                names = [f"{c['name']} [{c['total_connections']}:{c['incoming_edges']}/{c['outgoing_edges']}]"
                         for c in sample]
                if len(moderately_connected) > 5:
                    names.append(f"... ({len(moderately_connected) - 5} more)")
                lines.append(", ".join(names))
                lines.append("")

            # Connected
            if connected:
                lines.append("**Connected (15-19):**")
                sample = connected[:3]
                names = [f"{c['name']} [{c['total_connections']}:{c['incoming_edges']}/{c['outgoing_edges']}]"
                         for c in sample]
                if len(connected) > 3:
                    names.append(f"... ({len(connected) - 3} more)")
                lines.append(", ".join(names))
                lines.append("")

            # Summary for lightly/minimal (don't show all)
            lower_count = len(lightly_connected) + len(minimal)
            if lower_count > 0:
                lines.append(f"**Lightly Connected (<15):** {lower_count} classes")
                lines.append("")

            lines.append("*Tip: Deep-dive with `show_structure(target='<class_name>', include_relationships=True)`*")
        else:
            lines.append("No connected classes found")
        lines.append("")

        # Relationship Summary (new section)
        relationship_summary = data.get("relationship_summary", {})
        if relationship_summary:
            total_edges = sum(relationship_summary.values())
            lines.append(f"## Relationship Summary ({total_edges} total edges)")
            lines.append("")

            # Group by category
            structural = relationship_summary.get("CONTAINS", 0)
            behavioral = relationship_summary.get("CALLS", 0)
            dependencies = relationship_summary.get("IMPORTS", 0)
            inheritance = relationship_summary.get("INHERITS", 0)
            usage = relationship_summary.get("USES", 0)

            lines.append(f"**Structural**: {structural} CONTAINS edges (package→class→method hierarchy)")
            lines.append(f"**Behavioral**: {behavioral} CALLS edges (function invocations)")
            lines.append(f"**Dependencies**: {dependencies} IMPORTS edges (module imports)")
            lines.append(f"**Inheritance**: {inheritance} INHERITS edges (class inheritance)")
            lines.append(f"**Usage**: {usage} USES edges (field/variable usage)")
            lines.append("")

        return "\n".join(lines)
