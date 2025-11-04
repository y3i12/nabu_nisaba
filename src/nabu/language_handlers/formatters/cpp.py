"""C++ skeleton formatter implementation"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from nabu.language_handlers.formatters.base import BaseSkeletonFormatter


class CppSkeletonFormatter(BaseSkeletonFormatter):
    """C++-specific skeleton formatter"""

    def format_class_skeleton(
        self,
        class_data: Dict[str, Any],
        methods: List[Dict[str, Any]],
        control_flows: Dict[str, List[Dict[str, Any]]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format C++ class/struct/union/enum skeleton from components."""
        lines = []

        # Extract class type and declaration from content
        content = class_data.get("content", "")
        class_type = self._extract_class_type(content)

        # Extract class declaration line
        declaration_line = self._extract_declaration_line(content)

        # Add documentation if requested
        if include_docstrings and content:
            doc = self.extract_docstring(content)
            if doc:
                # Format as C++ comment block
                lines.append("/**")
                for doc_line in doc.split('\n'):
                    lines.append(f" * {doc_line}" if doc_line.strip() else " *")
                lines.append(" */")

        # Add class/struct/union/enum declaration
        if declaration_line:
            lines.append(declaration_line)
        else:
            # Fallback: construct from metadata
            class_name = class_data["name"]
            base_classes = class_data.get("base_classes", [])

            if class_type == "struct":
                if base_classes:
                    lines.append(f"struct {class_name} : {', '.join(base_classes)} {{")
                else:
                    lines.append(f"struct {class_name} {{")
            elif class_type == "union":
                lines.append(f"union {class_name} {{")
            elif class_type == "enum":
                lines.append(f"enum {class_name} {{")
            else:  # class (default)
                if base_classes:
                    # Format with inheritance
                    inheritance = ', '.join(base_classes)
                    lines.append(f"class {class_name} : {inheritance} {{")
                else:
                    lines.append(f"class {class_name} {{")

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
                field_type = field.get("declared_type", "auto")
                lines.append(self.indent(f"static {field_type} {field_name};", 1))

        # Instance fields
        instance_fields = class_data.get("instance_fields", [])
        if instance_fields:
            lines.append("")
            lines.append(self.indent("// Instance fields", 1))
            for field in instance_fields:
                field_name = field.get("name", "")
                field_type = field.get("declared_type", "auto")
                lines.append(self.indent(f"{field_type} {field_name};", 1))

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

        # Close class with semicolon (C++ requirement)
        lines.append("};")

        return "\n".join(lines)

    def format_method_signature(
        self,
        method: Dict[str, Any],
        class_name: Optional[str] = None
    ) -> str:
        """Format C++ method signature from metadata."""
        name = method["name"]
        parameters = method.get("parameters", [])
        return_type = method.get("return_type")
        content = method.get("content", "")

        # Check if constructor
        is_constructor = False
        if class_name and self.handler.is_constructor(name, class_name):
            is_constructor = True

        # Check if destructor
        is_destructor = self.handler.is_destructor(name)

        # Try to extract full signature from content for accuracy
        signature_line = self._extract_declaration_line(content)

        if signature_line:
            # Use extracted signature
            # For inline implementations, remove the body { ... }
            if '{' in signature_line:
                # Find the opening brace and remove everything from there
                brace_pos = signature_line.find('{')
                signature_line = signature_line[:brace_pos].rstrip()

            if not signature_line.endswith(';'):
                signature_line += ";"
            return signature_line

        # Fallback: construct from metadata
        # Build parameter list
        param_strs = []
        for param in parameters:
            param_name = param.get("name", "arg")
            param_type = param.get("declared_type", "auto")
            default_val = param.get("default_value")

            if default_val:
                param_strs.append(f"{param_type} {param_name} = {default_val}")
            else:
                param_strs.append(f"{param_type} {param_name}")

        params_str = ", ".join(param_strs)

        # Build signature based on type
        if is_destructor:
            # Destructor: virtual ~ClassName()
            return f"virtual {name}();"
        elif is_constructor:
            # Constructor: ClassName(params)
            return f"{name}({params_str});"
        else:
            # Regular method: ReturnType methodName(params) [const]
            ret_type = return_type if return_type else "void"

            # Check for const qualifier in content
            is_const = "const" in content and content.split('(')[0].count('const') != content.count('const')
            const_qual = " const" if is_const else ""

            return f"{ret_type} {name}({params_str}){const_qual};"

    def extract_docstring(
        self,
        content: str
    ) -> Optional[str]:
        """
        Extract C++ documentation comments (Doxygen-style or standard).

        Supports:
        - /** ... */ (Doxygen block)
        - /// ... (Doxygen line)
        - /* ... */ (standard block)
        - // ... (standard line)
        """
        if not content:
            return None

        lines = content.strip().split('\n')

        # Look for Doxygen-style /** ... */ or /** brief */
        in_block_comment = False
        doc_lines = []
        found_declaration = False

        for line in lines:
            stripped = line.strip()

            # Stop if we hit the actual declaration
            if not found_declaration:
                if any(keyword in stripped for keyword in ['class ', 'struct ', 'union ', 'enum ', 'void ', 'int ', 'auto ', 'template<']):
                    if not stripped.startswith('//') and not stripped.startswith('/*'):
                        found_declaration = True
                        break

            # Process block comments
            if not in_block_comment:
                if stripped.startswith('/**') or stripped.startswith('/*'):
                    in_block_comment = True
                    # Check if single-line comment: /** text */
                    if stripped.endswith('*/') and len(stripped) > 4:
                        # Single line
                        if stripped.startswith('/**'):
                            content_text = stripped[3:-2].strip()
                        else:
                            content_text = stripped[2:-2].strip()
                        # Remove leading * if present
                        if content_text.startswith('*'):
                            content_text = content_text[1:].strip()
                        return content_text if content_text else None
                    # Multi-line starting
                    if len(stripped) > 3:
                        start_content = stripped[3:].strip() if stripped.startswith('/**') else stripped[2:].strip()
                        if start_content.startswith('*'):
                            start_content = start_content[1:].strip()
                        if start_content:
                            doc_lines.append(start_content)
                elif stripped.startswith('///'):
                    # Doxygen single-line comment
                    comment_text = stripped[3:].strip()
                    doc_lines.append(comment_text)
                elif stripped.startswith('//'):
                    # Regular single-line comment
                    comment_text = stripped[2:].strip()
                    doc_lines.append(comment_text)
            else:
                # Inside block comment
                if stripped.endswith('*/'):
                    # End of block comment
                    content_text = stripped[:-2].strip()
                    if content_text.startswith('*'):
                        content_text = content_text[1:].strip()
                    if content_text:
                        doc_lines.append(content_text)
                    in_block_comment = False
                    break
                else:
                    # Middle line of block comment
                    if stripped.startswith('*'):
                        content_text = stripped[1:].strip()
                    else:
                        content_text = stripped
                    doc_lines.append(content_text)

        if doc_lines:
            return "\n".join(doc_lines).strip()

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
        """Format a single C++ method skeleton."""
        lines = []

        # Documentation
        if include_docstrings and method.get("content"):
            doc = self.extract_docstring(method["content"])
            if doc:
                lines.append(self.indent("/**", 1))
                for doc_line in doc.split('\n'):
                    lines.append(self.indent(f" * {doc_line}" if doc_line.strip() else " *", 1))
                lines.append(self.indent(" */", 1))

        # Method signature
        signature = self.format_method_signature(method, class_name)

        # Check if this is a pure virtual, inline, or declaration-only method
        content = method.get("content", "")
        is_pure_virtual = '= 0' in content
        # Inline implementations in class body end with }
        is_inline_implementation = content.strip().endswith('}') if content else False
        is_declaration_only = not '{' in content or is_pure_virtual or is_inline_implementation

        if is_declaration_only:
            # Declaration only methods (pure virtual, or forward declarations)
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
        Extract whether this is a class, struct, union, or enum.

        Returns:
            "class", "struct", "union", or "enum"
        """
        if not content:
            return "class"

        lines = content.strip().split('\n')

        # Find first non-comment line
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('/*'):
                continue

            # Check for keywords
            if ' struct ' in stripped or stripped.startswith('struct '):
                return "struct"
            elif ' union ' in stripped or stripped.startswith('union '):
                return "union"
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

        # Find first non-comment line
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith('//') and not stripped.startswith('/*'):
                start_idx = i
                break

        # Collect lines until we find opening brace or semicolon
        declaration_parts = []
        for line in lines[start_idx:]:
            stripped = line.strip()
            if stripped.startswith('//'):
                continue  # Skip line comments

            declaration_parts.append(stripped)

            # Stop at opening brace or semicolon
            if '{' in line or ';' in line:
                break

        if not declaration_parts:
            return None

        # Join and clean up
        declaration = ' '.join(declaration_parts)
        # Normalize whitespace
        declaration = re.sub(r'\s+', ' ', declaration).strip()

        return declaration

    def _format_docstring(self, callable_data: Dict[str, Any]) -> List[str]:
        """Extract C++ Doxygen comment."""
        doc = self.extract_docstring(callable_data["content"])
        if not doc:
            return []
        lines = ["/**"]
        for doc_line in doc.split('\n'):
            lines.append(f" * {doc_line}" if doc_line.strip() else " *")
        lines.append(" */")
        return lines

    def _format_empty_body_placeholder(self) -> str:
        """Return C++ comment placeholder."""
        return self.indent("// ...", 1)

    def _get_closing_brace(self) -> str:
        """C++ uses closing brace."""
        return "}"

    def format_package_skeleton(
        self,
        package_data: Dict[str, Any],
        children_skeletons: List[Dict[str, Any]],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """Format C++ namespace skeleton."""
        lines = []

        # Namespace info
        package_name = package_data["name"]
        file_path = package_data.get("file_path", "")

        lines.append(f"// Namespace: {package_name}")
        lines.append(f"// File: {Path(file_path).name}")
        lines.append("")
        lines.append(f"namespace {package_name} {{")
        lines.append("")

        # Separate children by type
        classes = [c for c in children_skeletons if c["frame_type"] == "CLASS"]
        callables = [c for c in children_skeletons if c["frame_type"] == "CALLABLE"]

        # Show classes
        if classes:
            lines.append("// ==================== CLASSES ====================")
            lines.append("")
            for class_skeleton in classes:
                # Indent class content
                indented_lines = []
                for line in class_skeleton["skeleton"].split('\n'):
                    indented_lines.append(self.indent(line, 1) if line.strip() else "")
                lines.append('\n'.join(indented_lines))
                lines.append("")

        # Show functions
        if callables:
            lines.append("// ==================== FUNCTIONS ====================")
            lines.append("")
            for callable_skeleton in callables:
                # Indent function content
                indented_lines = []
                for line in callable_skeleton["skeleton"].split('\n'):
                    indented_lines.append(self.indent(line, 1) if line.strip() else "")
                lines.append('\n'.join(indented_lines))
                lines.append("")

        # Namespace-level control flow (rare but possible in some contexts)
        if control_flows and detail_level != "minimal":
            lines.append("// ==================== INITIALIZATION ====================")
            lines.append("")
            for cf in control_flows:
                # Class-level initialization blocks, adjust for class scope
                indent = cf.get("nesting_depth", 1)
                cf_hint = self.format_control_flow_hint(cf, detail_level, indent_level=indent)
                if cf_hint:
                    lines.append(cf_hint)

        lines.append("}  // namespace " + package_name)

        return "\n".join(lines)
