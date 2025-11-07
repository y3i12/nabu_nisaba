"""
Query markdown formatter.

Adaptive compact markdown formatter for query tool output.
"""

from typing import Any, Dict, List
from pathlib import Path
from ..tool_base import BaseToolMarkdownFormatter

class QueryMarkdownFormatter(BaseToolMarkdownFormatter):
    """
    Adaptive compact markdown formatter for query tool output.

    Detects query patterns and formats accordingly:
    - Simple queries (≤3 cols): Pipe-separated inline
    - Frame queries: Compact frame notation
    - Aggregations: Inline key-value
    - Complex queries: Bulleted lists

    Achieves ~60% token reduction for typical queries.
    """

    def format(self, data: Dict[str, Any],) -> str:
        """Format query output in adaptive compact style."""
        rows = data.get("rows", [])
        row_count = data.get("row_count", 0)
        columns = data.get("columns", [])

        lines = []

        # Header
        lines.append("# Query Results")

        if row_count == 0:
            lines.append("*No results returned*")
            lines.append("*Tip: CALLS edges come from CALLABLE frames (methods), not CLASS frames.*")
            return "\n".join(lines)

        # Detect pattern and format accordingly
        pattern = self._detect_pattern(columns, row_count, rows)

        if pattern == "aggregation":
            # Pattern D: Single row with numeric values - inline format
            row = rows[0]
            parts = [f"{k}: {v}" for k, v in row.items()]
            lines.append(" | ".join(parts))
            lines.append("")

        elif pattern == "frame":
            # Pattern B: Frame query with standard columns
            col_list = ", ".join(columns)
            lines.append(f"Columns: {col_list} | Rows: {row_count}")
            lines.append("")
            lines.append("## Results `name (type) [location] {{id}}`")

            for row in rows:
                name = row.get("name") or row.get("c.name") or row.get("f.name") or "unknown"
                frame_type = row.get("type") or row.get("c.type") or row.get("f.type") or "unknown"
                frame_id = row.get("id") or row.get("c.id") or row.get("f.id") or "unknown"

                # Build location string
                file_path = row.get("file_path") or row.get("c.file_path") or row.get("f.file_path") or ""
                start_line = row.get("start_line") or row.get("c.start_line") or row.get("f.start_line")
                end_line = row.get("end_line") or row.get("c.end_line") or row.get("f.end_line")

                if file_path and start_line and end_line:
                    filename = Path(file_path).name
                    location = f"{filename}:{start_line}-{end_line}"
                else:
                    location = "unknown"

                lines.append(f"{name} ({frame_type}) [{location}] {{{frame_id}}}")
            lines.append("")

        elif pattern == "simple":
            # Pattern A: Simple columns - pipe-separated inline
            col_list = ", ".join(columns)
            lines.append(f"Columns: {col_list} | Rows: {row_count}")
            lines.append("")

            # Header with column names
            header = " | ".join(columns)
            lines.append(f"## Results `{header}`")

            for row in rows:
                values = [str(row.get(col, "")) for col in columns]
                lines.append(" | ".join(values))
            lines.append("")

        else:
            # Pattern C: Complex - bulleted lists per row
            col_list = ", ".join(columns)
            lines.append(f"Columns: {col_list} | Rows: {row_count}")
            lines.append("")

            for i, row in enumerate(rows):
                lines.append(f"## Row {i + 1}")
                for col in columns:
                    value = row.get(col, "")
                    lines.append(f"- **{col}:** {value}")
                lines.append("")

        return "\n".join(lines)

    def _detect_pattern(self, columns: List[str], row_count: int, rows: List[Dict]) -> str:
        """
        Detect query pattern for adaptive formatting.

        Returns:
            "aggregation" - Single row with numeric values
            "frame" - Frame query with id, name, type, file_path columns
            "simple" - ≤3 columns
            "complex" - >3 columns
        """
        if row_count == 0:
            return "simple"

        # Pattern D: Single row aggregation
        if row_count == 1:
            all_numeric = all(
                isinstance(v, (int, float, bool)) or v is None
                for v in rows[0].values()
            )
            if all_numeric:
                return "aggregation"

        # Pattern B: Frame query - check for frame-like columns
        # Look for columns with or without prefixes (f., c., etc.)
        col_set = set(columns)

        # Check direct columns
        frame_cols = {"id", "name", "type", "file_path"}
        if frame_cols.issubset(col_set):
            return "frame"

        # Check prefixed columns (f.id, c.name, etc.)
        for prefix in ["f.", "c.", "n.", "p."]:
            prefixed_cols = {f"{prefix}{col}" for col in frame_cols}
            if prefixed_cols.issubset(col_set):
                return "frame"

        # Pattern A: Simple columns
        if len(columns) <= 3:
            return "simple"

        # Pattern C: Complex
        return "complex"

