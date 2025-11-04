"""Java skeleton formatter implementation"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from nabu.language_handlers.formatters.base import BaseSkeletonFormatter


class JavaSkeletonFormatter(BaseSkeletonFormatter):
    """Java-specific skeleton formatter"""

    def format_class_skeleton(
        self,
        class_data: Dict[str, Any],
        methods: List[Dict[str, Any]],
        control_flows: Dict[str, List[Dict[str, Any]]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format Java class/interface/enum skeleton from components."""
        lines = []

        # Extract class declaration from content
        content = class_data.get("content", "")
        class_type = self._extract_class_type(content)

        # Extract class declaration line (skip annotations)
        declaration_line = self._extract_declaration_line(content)

        # Add javadoc if requested
        if include_docstrings and content:
            javadoc = self.extract_docstring(content)
            if javadoc:
                lines.append("/**")
                for doc_line in javadoc.split('\n'):
                    lines.append(f" * {doc_line}" if doc_line.strip() else " *")
                lines.append(" */")

        # Add class/interface/enum declaration
        if declaration_line:
            lines.append(declaration_line)
        else:
            # Fallback: construct from metadata
            class_name = class_data["name"]
            base_classes = class_data.get("base_classes", [])

            if class_type == "interface":
                if base_classes:
                    lines.append(f"public interface {class_name} extends {', '.join(base_classes)} {{")
                else:
                    lines.append(f"public interface {class_name} {{")
            elif class_type == "enum":
                lines.append(f"public enum {class_name} {{")
            else:  # class
                decl_parts = [f"public class {class_name}"]
                # Separate extends and implements
                extends = []
                implements = []
                for base in base_classes:
                    # Heuristic: if base looks like interface (common suffixes/patterns)
                    # This is imperfect but reasonable for skeleton
                    if any(suffix in base for suffix in ['able', 'Listener', 'Interface']):
                        implements.append(base)
                    else:
                        extends.append(base)

                if extends:
                    decl_parts.append(f"extends {extends[0]}")  # Java allows single inheritance
                if implements:
                    decl_parts.append(f"implements {', '.join(implements)}")

                lines.append(" ".join(decl_parts) + " {")

        # Add enum constants placeholder if enum
        if class_type == "enum":
            lines.append(self.indent("// Enum constants", 1))
            lines.append(self.indent("...", 1))
            lines.append("")

        # Static fields
        static_fields = class_data.get("static_fields", [])
        if static_fields:
            lines.append("")
            lines.append(self.indent("// Static fields", 1))
            for field in static_fields:
                field_name = field.get("name", "")
                field_type = field.get("declared_type", "Object")
                # Format: public static final Type NAME; (common pattern)
                lines.append(self.indent(f"public static final {field_type} {field_name};", 1))

        # Instance fields
        instance_fields = class_data.get("instance_fields", [])
        if instance_fields:
            lines.append("")
            lines.append(self.indent("// Instance fields", 1))
            for field in instance_fields:
                field_name = field.get("name", "")
                field_type = field.get("declared_type", "Object")
                # Format: private Type name; (common pattern for instance fields)
                lines.append(self.indent(f"private {field_type} {field_name};", 1))

        # Methods
        if not methods and class_type != "enum":
            # Empty class (not enum)
            if not static_fields and not instance_fields:
                lines.append(self.indent("// Empty class", 1))
        else:
            for method in methods:
                lines.append("")
                method_skeleton = self._format_method_skeleton(
                    method=method,
                    control_flows=control_flows.get(method["id"], []),
                    detail_level=detail_level,
                    include_docstrings=include_docstrings,
                    class_name=class_data["name"]
                )
                lines.append(method_skeleton)

        # Close class
        lines.append("}")

        return "\n".join(lines)

    def format_method_signature(
        self,
        method: Dict[str, Any],
        class_name: Optional[str] = None
    ) -> str:
        """Format Java method signature from metadata."""
        name = method["name"]
        parameters = method.get("parameters", [])
        return_type = method.get("return_type")
        content = method.get("content", "")

        # Check if constructor
        is_constructor = False
        if class_name and self.handler.is_constructor(name, class_name):
            is_constructor = True

        # Extract modifiers and signature from content for accuracy
        signature_line = self._extract_declaration_line(content)

        if signature_line:
            # Use extracted signature, but ensure it ends with proper syntax
            # Remove opening brace if present
            signature_line = signature_line.rstrip().rstrip('{').rstrip()
            if not signature_line.endswith(';'):
                signature_line += ";"
            return signature_line

        # Fallback: construct from metadata
        # Default modifiers
        modifiers = ["public"]

        # Build parameter list
        param_strs = []
        for param in parameters:
            param_name = param.get("name", "arg")
            param_type = param.get("declared_type", "Object")
            param_strs.append(f"{param_type} {param_name}")

        params_str = ", ".join(param_strs)

        # Build signature
        if is_constructor:
            # Constructor: public ClassName(params)
            return f"{' '.join(modifiers)} {name}({params_str});"
        else:
            # Regular method: public ReturnType methodName(params)
            ret_type = return_type if return_type else "void"
            return f"{' '.join(modifiers)} {ret_type} {name}({params_str});"

    def extract_docstring(
        self,
        content: str
    ) -> Optional[str]:
        """Extract Javadoc (/** ... */) from Java source."""
        if not content:
            return None

        lines = content.strip().split('\n')

        # Look for /** ... */ pattern
        in_javadoc = False
        javadoc_lines = []

        for line in lines:
            stripped = line.strip()

            if not in_javadoc:
                if stripped.startswith('/**'):
                    in_javadoc = True
                    # Check if single-line javadoc: /** text */
                    if stripped.endswith('*/') and len(stripped) > 5:
                        # Single line javadoc
                        content = stripped[3:-2].strip()
                        # Remove leading * if present
                        if content.startswith('*'):
                            content = content[1:].strip()
                        return content
                    # Multi-line javadoc starting
                    if len(stripped) > 3:
                        # Has content on same line: /** content
                        content = stripped[3:].strip()
                        if content.startswith('*'):
                            content = content[1:].strip()
                        if content:
                            javadoc_lines.append(content)
            else:
                # Inside javadoc
                if stripped.endswith('*/'):
                    # End of javadoc
                    content = stripped[:-2].strip()
                    if content.startswith('*'):
                        content = content[1:].strip()
                    if content:
                        javadoc_lines.append(content)
                    break
                else:
                    # Middle line of javadoc
                    if stripped.startswith('*'):
                        content = stripped[1:].strip()
                    else:
                        content = stripped
                    javadoc_lines.append(content)

        if javadoc_lines:
            return "\n".join(javadoc_lines).strip()

        return None

    # ==================== PRIVATE HELPER METHODS ====================

    def _format_method_skeleton(
        self,
        method: Dict[str, Any],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool,
        class_name: str
    ) -> str:
        """Format a single Java method skeleton."""
        lines = []

        # Javadoc
        if include_docstrings and method.get("content"):
            javadoc = self.extract_docstring(method["content"])
            if javadoc:
                lines.append(self.indent("/**", 1))
                for doc_line in javadoc.split('\n'):
                    lines.append(self.indent(f" * {doc_line}" if doc_line.strip() else " *", 1))
                lines.append(self.indent(" */", 1))

        # Method signature
        signature = self.format_method_signature(method, class_name)

        # Check if this is an abstract method or interface method
        content = method.get("content", "")
        is_abstract = 'abstract' in content or not '{' in content

        if is_abstract:
            # Abstract methods have no body
            lines.append(self.indent(signature, 1))
        else:
            # Regular method with body
            # Remove semicolon if present and add opening brace
            sig_line = signature.rstrip(';').rstrip()
            lines.append(self.indent(sig_line + " {", 1))

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

            # Close method
            lines.append(self.indent("}", 1))

        return "\n".join(lines)

    def _extract_class_type(self, content: str) -> str:
        """
        Extract whether this is a class, interface, or enum.

        Returns:
            "class", "interface", or "enum"
        """
        if not content:
            return "class"

        lines = content.strip().split('\n')

        # Find first non-annotation, non-comment line
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('@') or stripped.startswith('//') or stripped.startswith('/*'):
                continue

            # Check for keywords
            if ' interface ' in stripped or stripped.startswith('interface '):
                return "interface"
            elif ' enum ' in stripped or stripped.startswith('enum '):
                return "enum"
            elif ' class ' in stripped or stripped.startswith('class '):
                return "class"

        # Default
        return "class"

    def _extract_declaration_line(self, content: str) -> Optional[str]:
        """
        Extract the complete declaration line from content.

        Handles multi-line declarations by concatenating until we find '{'

        Returns:
            Complete declaration line or None
        """
        if not content:
            return None

        lines = content.strip().split('\n')

        # Find first non-annotation line
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith('@') and not stripped.startswith('//'):
                start_idx = i
                break

        # Collect lines until we find opening brace
        declaration_parts = []
        for line in lines[start_idx:]:
            stripped = line.strip()
            if stripped.startswith('//'):
                continue  # Skip comments

            declaration_parts.append(stripped)

            # Stop at opening brace
            if '{' in line:
                break

        if not declaration_parts:
            return None

        # Join and clean up
        declaration = ' '.join(declaration_parts)
        # Normalize whitespace
        declaration = re.sub(r'\s+', ' ', declaration).strip()

        return declaration

    def _format_docstring(self, callable_data: Dict[str, Any]) -> List[str]:
        """Extract Javadoc comment."""
        javadoc = self.extract_docstring(callable_data["content"])
        if not javadoc:
            return []
        lines = ["/**"]
        for doc_line in javadoc.split('\n'):
            lines.append(f" * {doc_line}" if doc_line.strip() else " *")
        lines.append(" */")
        return lines

    def _format_empty_body_placeholder(self) -> str:
        """Return Java comment placeholder."""
        return self.indent("// ...", 1)

    def _get_closing_brace(self) -> str:
        """Java uses closing brace."""
        return "}"

    def format_package_skeleton(
        self,
        package_data: Dict[str, Any],
        children_skeletons: List[Dict[str, Any]],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format Java package skeleton."""
        lines = []

        # Package declaration
        package_name = package_data["name"]
        qualified_name = package_data.get("qualified_name", "")
        file_path = package_data.get("file_path", "")

        # Extract actual Java package from qualified name if possible
        # Java packages usually follow pattern: projectname.java_root.actual.package.name
        java_package = qualified_name.split(".java_root.")[-1] if ".java_root." in qualified_name else package_name

        lines.append(f"// Package: {java_package}")
        lines.append(f"// File: {Path(file_path).name}")
        lines.append("")
        lines.append(f"package {java_package};")
        lines.append("")

        # Separate children by type
        classes = [c for c in children_skeletons if c["frame_type"] == "CLASS"]
        callables = [c for c in children_skeletons if c["frame_type"] == "CALLABLE"]

        # Show classes
        if classes:
            lines.append("// ==================== CLASSES ====================")
            lines.append("")
            for class_skeleton in classes:
                lines.append(class_skeleton["skeleton"])
                lines.append("")

        # Show top-level methods (rare in Java but possible in some contexts)
        if callables:
            lines.append("// ==================== STATIC METHODS ====================")
            lines.append("")
            for callable_skeleton in callables:
                lines.append(callable_skeleton["skeleton"])
                lines.append("")

        # Package-level control flow is not typical in Java, but include if present
        if control_flows and detail_level != "minimal":
            lines.append("// ==================== INITIALIZATION ====================")
            lines.append("")
            for cf in control_flows:
                # Static initialization blocks at class level
                indent = max(0, cf.get("nesting_depth", 1) - 1)
                cf_hint = self.format_control_flow_hint(cf, detail_level, indent_level=indent)
                if cf_hint:
                    lines.append(cf_hint)

        return "\n".join(lines)
