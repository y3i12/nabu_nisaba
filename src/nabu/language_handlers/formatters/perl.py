"""Perl-specific skeleton formatter"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import re
from .base import BaseSkeletonFormatter


class PerlSkeletonFormatter(BaseSkeletonFormatter):
    """Perl-specific skeleton formatter"""

    def format_class_skeleton(
        self,
        class_data: Dict[str, Any],
        methods: List[Dict[str, Any]],
        control_flows: Dict[str, List[Dict[str, Any]]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format Perl package skeleton from components."""
        lines = []

        # Package declaration
        package_name = class_data["name"]
        content = class_data.get("content", "")

        # Add POD documentation if requested
        if include_docstrings and content:
            pod = self.extract_docstring(content)
            if pod:
                lines.append("=head1 NAME")
                lines.append("")
                lines.append(f"{package_name}")
                lines.append("")
                lines.append("=head1 DESCRIPTION")
                lines.append("")
                for doc_line in pod.split('\n'):
                    lines.append(doc_line if doc_line.strip() else "")
                lines.append("")
                lines.append("=cut")
                lines.append("")

        # Package declaration
        lines.append(f"package {package_name};")
        lines.append("")

        # Inheritance (use parent is modern Perl)
        base_classes = class_data.get("base_classes", [])
        if base_classes:
            if len(base_classes) == 1:
                lines.append(f"use parent '{base_classes[0]}';")
            else:
                bases_str = " ".join([f"'{bc}'" for bc in base_classes])
                lines.append(f"use parent qw({bases_str});")
            lines.append("")

        # Static fields (package variables)
        static_fields = class_data.get("static_fields", [])
        if static_fields:
            lines.append("# Package variables")
            for field in static_fields:
                field_name = field.get("name", "")
                lines.append(f"our ${field_name};")
            lines.append("")

        # Instance fields comment (Perl doesn't declare these outside constructors)
        instance_fields = class_data.get("instance_fields", [])
        if instance_fields:
            lines.append("# Instance fields (typically set in constructor):")
            for field in instance_fields:
                field_name = field.get("name", "")
                lines.append(f"# - {field_name}")
            lines.append("")

        # Methods (subroutines)
        if not methods:
            lines.append("# Empty package")
        else:
            for i, method in enumerate(methods):
                if i > 0:  # Add blank line between methods
                    lines.append("")
                method_skeleton = self._format_method_skeleton(
                    method=method,
                    control_flows=control_flows.get(method["id"], []),
                    detail_level=detail_level,
                    include_docstrings=include_docstrings,
                    package_name=package_name
                )
                lines.append(method_skeleton)

        # Perl module must return true value
        lines.append("")
        lines.append("1;")

        return "\n".join(lines)

    def format_method_signature(
        self,
        method: Dict[str, Any],
        package_name: Optional[str] = None
    ) -> str:
        """Format Perl subroutine signature from metadata."""
        name = method["name"]
        parameters = method.get("parameters", [])

        # Check if constructor or destructor
        is_constructor = False
        is_destructor = False

        if package_name and self.handler.is_constructor(name, package_name):
            is_constructor = True
        if self.handler.is_destructor(name):
            is_destructor = True

        # Build parameter unpacking line
        param_names = []
        for param in parameters:
            param_name = param.get("name", "")
            if param_name and param_name not in ['self', 'class']:
                param_names.append(f"${param_name}")

        # Subroutine declaration
        sig_lines = []
        sig_lines.append(f"sub {name} {{")

        # Parameter unpacking (most common Perl pattern)
        if is_constructor or (parameters and parameters[0].get("name") in ["self", "class"]):
            # Has $self or $class as first param
            if param_names:
                sig_lines.append(f"    my ($self, {', '.join(param_names)}) = @_;")
            else:
                sig_lines.append("    my ($self) = @_;")
        elif param_names:
            # No self, just regular params
            sig_lines.append(f"    my ({', '.join(param_names)}) = @_;")
        else:
            # No parameters
            sig_lines.append("    my ($self) = @_;")  # Assume $self by convention

        return "\n".join(sig_lines)

    def extract_docstring(
        self,
        content: str
    ) -> Optional[str]:
        """
        Extract Perl documentation (POD or comments).

        Supports:
        - POD (Plain Old Documentation): =head1 ... =cut
        - Comment blocks: # ...
        """
        if not content:
            return None

        lines = content.strip().split('\n')

        # Try to extract POD first
        pod_lines = []
        in_pod = False
        found_description = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('=head1') or stripped.startswith('=head2'):
                in_pod = True
                # Check if this is a description/synopsis section
                if any(keyword in stripped.lower() for keyword in ['description', 'synopsis', 'overview']):
                    found_description = True
                continue
            elif stripped == '=cut':
                if found_description and pod_lines:
                    break
                in_pod = False
                found_description = False
                pod_lines = []  # Reset if we haven't found description yet
                continue
            elif in_pod and found_description:
                # Skip empty POD directives
                if stripped.startswith('='):
                    continue
                pod_lines.append(stripped)

        if pod_lines:
            return "\n".join(pod_lines).strip()

        # Fall back to leading comment blocks
        comment_lines = []
        in_comment_block = False

        for line in lines:
            stripped = line.strip()

            # Stop at package declaration
            if stripped.startswith('package '):
                break

            if stripped.startswith('#'):
                in_comment_block = True
                comment_text = stripped[1:].strip()
                if comment_text:  # Skip empty comment lines
                    comment_lines.append(comment_text)
            elif in_comment_block and not stripped:
                # Empty line continues comment block
                continue
            elif in_comment_block and stripped:
                # Non-comment line ends the block
                break

        if comment_lines:
            return "\n".join(comment_lines).strip()

        return None

    # ==================== PRIVATE HELPER METHODS ====================

    def _format_method_skeleton(
        self,
        method: Dict[str, Any],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool,
        package_name: str
    ) -> str:
        """Format a single Perl subroutine skeleton."""
        lines = []

        # POD documentation for method
        if include_docstrings and method.get("content"):
            pod = self._extract_method_docstring(method["content"])
            if pod:
                lines.append("=head2 " + method["name"])
                lines.append("")
                for doc_line in pod.split('\n'):
                    lines.append(doc_line if doc_line.strip() else "")
                lines.append("")
                lines.append("=cut")
                lines.append("")

        # Method signature with parameter unpacking
        signature = self.format_method_signature(method, package_name)
        lines.append(signature)

        # Control flow (for guards/structure modes)
        if detail_level != "minimal" and control_flows:
            control_flow_lines = self._format_control_flows(
                control_flows,
                detail_level,
                base_indent=1
            )
            lines.append(control_flow_lines)
        else:
            # Just placeholder
            lines.append(self.indent("...", 1))

        # Close subroutine
        lines.append("}")

        return "\n".join(lines)

    def _format_docstring(self, callable_data: Dict[str, Any]) -> List[str]:
        """Extract Perl POD documentation."""
        pod = self.extract_docstring(callable_data["content"])
        if not pod:
            return []
        return [
            f"=head2 {callable_data['name']}",
            "",
            pod,
            "",
            "=cut",
            ""
        ]

    def _format_empty_body_placeholder(self) -> str:
        """Return Perl comment placeholder."""
        return self.indent("# ...", 1)

    def _get_closing_brace(self) -> str:
        """Perl uses closing brace."""
        return "}"

    def format_package_skeleton(
        self,
        package_data: Dict[str, Any],
        children_skeletons: List[Dict[str, Any]],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format Perl package skeleton."""
        lines = []

        # Package declaration
        package_name = package_data["name"]
        file_path = package_data.get("file_path", "")

        # POD documentation
        if include_docstrings and package_data.get("content"):
            pod = self._extract_module_pod(package_data["content"])
            if pod:
                lines.append("=head1 NAME")
                lines.append("")
                lines.append(package_name)
                lines.append("")
                lines.append("=head1 DESCRIPTION")
                lines.append("")
                lines.append(pod)
                lines.append("")
                lines.append("=cut")
                lines.append("")

        lines.append(f"# Package: {package_name}")
        lines.append(f"# File: {Path(file_path).name}")
        lines.append("")
        lines.append(f"package {package_name};")
        lines.append("")

        # Separate children by type
        classes = [c for c in children_skeletons if c["frame_type"] == "CLASS"]
        callables = [c for c in children_skeletons if c["frame_type"] == "CALLABLE"]

        # Show classes (packages in Perl context)
        if classes:
            lines.append("# ==================== PACKAGES ====================")
            lines.append("")
            for class_skeleton in classes:
                lines.append(class_skeleton["skeleton"])
                lines.append("")

        # Show subroutines
        if callables:
            lines.append("# ==================== SUBROUTINES ====================")
            lines.append("")
            for callable_skeleton in callables:
                lines.append(callable_skeleton["skeleton"])
                lines.append("")

        # Package-level control flow
        if control_flows and detail_level != "minimal":
            lines.append("# ==================== MAIN CODE ====================")
            lines.append("")
            for cf in control_flows:
                # Package-level control flows
                indent = max(0, cf.get("nesting_depth", 1) - 1)
                cf_hint = self.format_control_flow_hint(cf, detail_level, indent_level=indent)
                if cf_hint:
                    lines.append(cf_hint)
            lines.append("")

        # Perl module must return true value
        lines.append("1;")

        return "\n".join(lines)

    def _extract_module_pod(self, content: str) -> Optional[str]:
        """Extract module-level POD documentation."""
        lines = content.split('\n')
        
        # Look for POD blocks (=head1 NAME or =head1 DESCRIPTION)
        in_pod = False
        pod_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped.startswith('=head1 DESCRIPTION'):
                in_pod = True
                continue
            elif stripped.startswith('=') and in_pod:
                # Another POD directive, stop collecting
                break
            elif stripped == '=cut':
                break
            elif in_pod and stripped:
                pod_lines.append(line)
        
        if pod_lines:
            return '\n'.join(pod_lines).strip()
        
        return None

    def _extract_method_docstring(self, content: str) -> Optional[str]:
        """Extract POD or comments specifically for a method."""
        if not content:
            return None

        lines = content.strip().split('\n')

        # Look for POD before sub declaration
        pod_lines = []
        in_pod = False

        for line in lines:
            stripped = line.strip()

            # Stop at sub declaration
            if stripped.startswith('sub '):
                break

            if stripped.startswith('=head2') or stripped.startswith('=item'):
                in_pod = True
                continue
            elif stripped == '=cut':
                break
            elif in_pod:
                # Skip empty POD directives
                if stripped.startswith('='):
                    continue
                pod_lines.append(stripped)

        if pod_lines:
            return "\n".join(pod_lines).strip()

        # Fall back to comments
        comment_lines = []
        for line in lines:
            stripped = line.strip()

            # Stop at sub declaration
            if stripped.startswith('sub '):
                break

            if stripped.startswith('#'):
                comment_text = stripped[1:].strip()
                if comment_text:
                    comment_lines.append(comment_text)
            elif comment_lines and not stripped:
                continue
            elif comment_lines and stripped:
                break

        if comment_lines:
            return "\n".join(comment_lines).strip()

        return None
