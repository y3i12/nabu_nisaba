"""Python skeleton formatter implementation"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from nabu.language_handlers.formatters.base import BaseSkeletonFormatter


class PythonSkeletonFormatter(BaseSkeletonFormatter):
    """Python-specific skeleton formatter"""

    def format_class_skeleton(
        self,
        class_data: Dict[str, Any],
        methods: List[Dict[str, Any]],
        control_flows: Dict[str, List[Dict[str, Any]]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format Python class skeleton from components."""
        lines = []

        # Class declaration
        class_name = class_data["name"]
        base_classes = class_data.get("base_classes", [])

        if base_classes:
            bases_str = ", ".join(base_classes)
            lines.append(f"class {class_name}({bases_str}):")
        else:
            lines.append(f"class {class_name}:")

        # Extract class docstring from content if available
        if include_docstrings and class_data.get("content"):
            class_docstring = self.extract_docstring(class_data["content"])
            if class_docstring:
                lines.append(self.indent(f'"""{class_docstring}"""', 1))

        # Instance fields
        instance_fields = class_data.get("instance_fields", [])
        if instance_fields:
            lines.append("")
            for field in instance_fields:
                field_name = field.get("name", "")
                field_type = field.get("declared_type", "")
                if field_type:
                    lines.append(self.indent(f"{field_name}: {field_type}", 1))
                else:
                    lines.append(self.indent(f"{field_name}", 1))

        # Methods
        if not methods:
            lines.append(self.indent("pass", 1))
        else:
            for method in methods:
                lines.append("")
                method_skeleton = self._format_method_skeleton(
                    method=method,
                    control_flows=control_flows.get(method["id"], []),
                    detail_level=detail_level,
                    include_docstrings=include_docstrings
                )
                lines.append(method_skeleton)

        return "\n".join(lines)

    def format_method_signature(
        self,
        method: Dict[str, Any]
    ) -> str:
        """Format Python method signature from metadata."""
        name = method["name"]
        parameters = method.get("parameters", [])
        return_type = method.get("return_type")

        # Format parameters
        param_strs = []
        for param in parameters:
            param_name = param.get("name", "")
            param_type = param.get("declared_type", "")
            default_value = param.get("default_value", "")

            if param_type and default_value:
                param_strs.append(f"{param_name}: {param_type} = {default_value}")
            elif param_type:
                param_strs.append(f"{param_name}: {param_type}")
            elif default_value:
                param_strs.append(f"{param_name}={default_value}")
            else:
                param_strs.append(param_name)

        params_str = ", ".join(param_strs)

        # Build signature
        if return_type:
            return f"def {name}({params_str}) -> {return_type}:"
        else:
            return f"def {name}({params_str}):"

    def extract_docstring(
        self,
        content: str
    ) -> Optional[str]:
        """Extract Python triple-quote docstring."""
        lines = content.strip().split('\n')

        # Look for docstring (triple quotes)
        in_docstring = False
        docstring_lines = []
        quote_char = None

        for line in lines[1:]:  # Skip first line (def/class)
            stripped = line.strip()

            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    quote_char = stripped[:3]
                    in_docstring = True
                    # Check if single-line docstring
                    if stripped.endswith(quote_char) and len(stripped) > 6:
                        return stripped[3:-3].strip()
                    docstring_lines.append(stripped[3:])
            else:
                if stripped.endswith(quote_char):
                    docstring_lines.append(stripped[:-3])
                    break
                docstring_lines.append(line.strip())

        if docstring_lines:
            return "\n".join(docstring_lines).strip()
        return None

    # ==================== PRIVATE HELPER METHODS ====================

    def _format_method_skeleton(
        self,
        method: Dict[str, Any],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format a single Python method skeleton."""
        lines = []

        # Method signature
        signature = self.format_method_signature(method)
        lines.append(self.indent(signature, 1))

        # Docstring
        if include_docstrings and method.get("content"):
            docstring = self.extract_docstring(method["content"])
            if docstring:
                lines.append(self.indent(f'"""{docstring}"""', 2))

        # Control flow (for guards/structure modes)
        if detail_level != "minimal" and control_flows:
            control_flow_lines = self._format_control_flows(
                control_flows,
                detail_level
            )
            lines.append(control_flow_lines)
        else:
            # Just placeholder
            lines.append(self.indent("...", 2))

        return "\n".join(lines)

    def _format_docstring(self, callable_data: Dict[str, Any]) -> List[str]:
        """Extract Python docstring."""
        docstring = self.extract_docstring(callable_data["content"])
        if docstring:
            return [self.indent(f'"""{docstring}"""', 1)]
        return []

    def _format_empty_body_placeholder(self) -> str:
        """Return Python ellipsis."""
        return self.indent("...", 1)

    def format_package_skeleton(
        self,
        package_data: Dict[str, Any],
        children_skeletons: List[Dict[str, Any]],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format Python package/module skeleton."""
        lines = []

        # Module docstring (extract from content if available)
        if include_docstrings and package_data.get("content"):
            content = package_data["content"]
            module_doc = self._extract_module_docstring(content)
            if module_doc:
                lines.append(f'"""{module_doc}"""')
                lines.append("")

        # Package/module header comment
        package_name = package_data["name"]
        file_path = package_data.get("file_path", "")
        lines.append(f"# Package: {package_name}")
        lines.append(f"# File: {Path(file_path).name}")
        lines.append("")

        # Separate children by type
        classes = [c for c in children_skeletons if c["frame_type"] == "CLASS"]
        callables = [c for c in children_skeletons if c["frame_type"] == "CALLABLE"]

        # Show classes
        if classes:
            lines.append("# ==================== CLASSES ====================")
            lines.append("")
            for class_skeleton in classes:
                lines.append(class_skeleton["skeleton"])
                lines.append("")

        # Show top-level functions
        if callables:
            lines.append("# ==================== FUNCTIONS ====================")
            lines.append("")
            for callable_skeleton in callables:
                lines.append(callable_skeleton["skeleton"])
                lines.append("")

        # Show package-level control flow (e.g., if __name__ == "__main__")
        if control_flows and detail_level != "minimal":
            lines.append("# ==================== MAIN BLOCK ====================")
            lines.append("")
            for cf in control_flows:
                # For packages, control flows are at top level (depth starts at 0)
                indent = max(0, cf.get("nesting_depth", 1) - 1)
                cf_hint = self.format_control_flow_hint(cf, detail_level, indent_level=indent)
                if cf_hint:
                    lines.append(cf_hint)

        return "\n".join(lines)

    def _extract_module_docstring(self, content: str) -> Optional[str]:
        """Extract module-level docstring (first string literal in file)."""
        lines = content.strip().split('\n')

        # Skip shebang and encoding declarations
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#') or not stripped:
                start_idx = i + 1
            else:
                break

        # Check if first non-comment line is a docstring
        if start_idx < len(lines):
            first_line = lines[start_idx].strip()
            if first_line.startswith('"""') or first_line.startswith("'''"):
                # Use existing extract_docstring logic but on content from first docstring position
                docstring_start = content.find(first_line)
                if docstring_start >= 0:
                    return self.extract_docstring(content[docstring_start:])

        return None
