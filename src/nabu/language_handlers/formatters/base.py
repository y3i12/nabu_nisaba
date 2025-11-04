"""Base class for language-specific skeleton formatters"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from nabu.language_handlers.base import LanguageHandler


@dataclass
class LanguageSyntax:
    """
    Language-specific syntax rules for skeleton formatting.

    Captures the syntactic differences between languages while
    keeping formatting logic unified in the base class.
    """
    # Brace handling
    uses_braces: bool  # True for C++/Java/Perl, False for Python
    auto_close_brace: bool = True  # Auto-add closing } for brace languages

    # Control flow keywords (for special handling)
    try_keyword: str = "try"
    except_block_format: str = "standard"  # "standard" or "perl_eval"


# Language syntax configuration registry
LANGUAGE_SYNTAX = {
    'python': LanguageSyntax(
        uses_braces=False,
        auto_close_brace=False,
    ),
    'cpp': LanguageSyntax(
        uses_braces=True,
    ),
    'java': LanguageSyntax(
        uses_braces=True,
    ),
    'perl': LanguageSyntax(
        uses_braces=True,
        except_block_format="perl_eval",
    ),
}


class BaseSkeletonFormatter(ABC):
    """
    Abstract base class for language-specific skeleton formatters.

    Each formatter is responsible for converting database frame metadata
    into formatted skeleton code for a specific programming language.

    The formatter has access to its language handler for language-specific
    operations like checking constructors, getting separators, etc.
    """

    def __init__(self, handler: 'LanguageHandler'):
        """
        Initialize formatter with its language handler.

        Args:
            handler: LanguageHandler instance for this language
        """
        self.handler = handler
        self.language = handler.language
        self.syntax = LANGUAGE_SYNTAX.get(handler.language, LANGUAGE_SYNTAX['python'])

    def format_show_structure(
        self,
        frame_data: Dict[str, Any],
        children: List[Dict[str, Any]],
        children_skeletons: List[Dict[str, Any]],
        control_flows: Dict[str, List[Dict[str, Any]]],
        detail_level: str,
        include_docstrings: bool,
        recursive: bool = False
    ) -> str:
        """
        Format skeleton for ANY frame type (dispatcher method).

        This is the main entry point for skeleton generation. It dispatches
        to the appropriate format_*_skeleton method based on frame_data["type"].

        Args:
            frame_data: Frame metadata (type, name, qualified_name, content, etc.)
            children: List of direct children metadata
            children_skeletons: List of already-formatted child skeletons (for recursive mode)
            control_flows: Dict mapping frame_id -> list of control flow frames
            detail_level: "minimal", "guards", or "structure"
            include_docstrings: Whether to include docstrings
            recursive: If True, use children_skeletons instead of re-querying

        Returns:
            Formatted skeleton string
        """
        frame_type = frame_data["type"]
        frame_id = frame_data["id"]

        if frame_type == "CLASS":
            # Dispatch to language-specific class formatter
            methods = [c for c in children if c["type"] == "CALLABLE"]
            return self.format_class_skeleton(
                class_data=frame_data,
                methods=methods,
                control_flows=control_flows,
                detail_level=detail_level,
                include_docstrings=include_docstrings
            )

        elif frame_type == "CALLABLE":
            # Dispatch to language-specific callable formatter
            cf = control_flows.get(frame_id, [])
            return self.format_callable_skeleton(
                callable_data=frame_data,
                control_flows=cf,
                detail_level=detail_level,
                include_docstrings=include_docstrings
            )

        elif frame_type == "PACKAGE":
            # Dispatch to language-specific package formatter
            cf = control_flows.get(frame_id, [])
            return self.format_package_skeleton(
                package_data=frame_data,
                children_skeletons=children_skeletons,
                control_flows=cf,
                detail_level=detail_level,
                include_docstrings=include_docstrings
            )

        else:
            raise ValueError(f"Frame type '{frame_type}' not supported for skeleton generation")

    @abstractmethod
    def format_class_skeleton(
        self,
        class_data: Dict[str, Any],
        methods: List[Dict[str, Any]],
        control_flows: Dict[str, List[Dict[str, Any]]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """
        Format complete class skeleton from database metadata.

        Args:
            class_data: Class metadata (name, fields, base_classes, content, etc.)
            methods: List of method metadata (name, parameters, return_type, content, etc.)
            control_flows: Dict mapping method_id -> list of control flow frames
            detail_level: "minimal", "guards", or "structure"
            include_docstrings: Whether to extract and include docstrings

        Returns:
            Formatted class skeleton as string
        """
        pass

    def format_callable_skeleton(
        self,
        callable_data: Dict[str, Any],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """
        Template method for callable skeleton formatting.

        Unifies common control flow iteration logic while delegating
        language-specific formatting (docstrings, placeholders, braces)
        to abstract methods.

        Args:
            callable_data: Callable metadata (name, parameters, return_type, content, etc.)
            control_flows: List of control flow frames within this callable
            detail_level: "minimal", "guards", or "structure"
            include_docstrings: Whether to extract and include docstrings

        Returns:
            Formatted callable skeleton
        """
        lines = []

        # 1. Language-specific docstring
        if include_docstrings and callable_data.get("content"):
            doc_lines = self._format_docstring(callable_data)
            lines.extend(doc_lines)

        # 2. Method signature (already delegated)
        signature = self.format_method_signature(callable_data)
        lines.append(signature)

        # 3. UNIFIED CONTROL FLOW LOGIC (eliminates duplication across languages)
        if detail_level != "minimal" and control_flows:
            for cf in control_flows:
                indent = cf.get("nesting_depth", 1)
                cf_hint = self.format_control_flow_hint(cf, detail_level, indent_level=indent)
                if cf_hint:
                    lines.append(cf_hint)
        else:
            lines.append(self._format_empty_body_placeholder())

        # 4. Optional closing brace (C-family languages)
        closing = self._get_closing_brace()
        if closing:
            lines.append(closing)

        return "\n".join(lines)

    @abstractmethod
    def _format_docstring(self, callable_data: Dict[str, Any]) -> List[str]:
        """
        Extract and format docstring in language-specific style.

        Args:
            callable_data: Callable metadata with 'content' field

        Returns:
            List of docstring lines (empty list if no docstring)

        Examples:
            Python: List with triple-quoted docstring indented
            C++/Java: Doxygen-style comment block with /** ... */
            Perl: POD-style documentation with =head2 ... =cut
        """
        pass

    @abstractmethod
    def _format_empty_body_placeholder(self) -> str:
        """
        Return language-specific empty body placeholder.

        Returns:
            Indented placeholder string

        Examples:
            Python: "    ..."
            C++/Java: "    // ..."
            Perl: "    # ..."
        """
        pass

    def _get_closing_brace(self) -> Optional[str]:
        """
        Return closing brace for C-family languages.

        Override in subclasses that use braces (C++, Java, Perl).
        Python does not use braces, so default is None.

        Returns:
            Closing brace string or None
        """
        return None

    @abstractmethod
    def format_package_skeleton(
        self,
        package_data: Dict[str, Any],
        children_skeletons: List[Dict[str, Any]],
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        include_docstrings: bool
    ) -> str:
        """
        Format package/module skeleton showing contained classes and functions.

        Args:
            package_data: Package metadata (name, qualified_name, file_path, etc.)
            children_skeletons: List of formatted child skeletons (classes, functions)
            control_flows: Package-level control flow blocks
            detail_level: "minimal", "guards", or "structure"
            include_docstrings: Whether to include docstrings

        Returns:
            Formatted package skeleton
        """
        pass

    @abstractmethod
    def format_method_signature(
        self,
        method: Dict[str, Any]
    ) -> str:
        """
        Format method/function signature from metadata.

        Args:
            method: Method metadata (name, parameters, return_type)

        Returns:
            Formatted method signature (e.g., "def foo(x: int) -> str:")
        """
        pass

    def format_control_flow_hint(
        self,
        control_flow: Dict[str, Any],
        detail_level: str,
        indent_level: int
    ) -> str:
        """
        Format a single control flow hint (UNIFIED across all languages).

        Language differences are handled via self.syntax configuration.

        Args:
            control_flow: Control flow frame metadata (type, content, start_line)
            detail_level: "minimal", "guards", or "structure"
            indent_level: Base indentation level for this control flow

        Returns:
            Formatted control flow hint (e.g., "    if condition:\n        ...")
        """
        cf_type = control_flow["type"]
        heading = control_flow.get("heading", "")
        first_line = heading.strip() if heading else "..."

        lines = []

        # For guards mode, show the condition but collapse body
        if detail_level == "guards":
            if cf_type in ["IF_BLOCK", "ELIF_BLOCK"]:
                lines.append(self.indent(first_line, indent_level))
                lines.append(self.indent("...", indent_level + 1))
                self._maybe_close_brace(lines, first_line, indent_level)

            elif cf_type == "TRY_BLOCK":
                # Perl special case: eval instead of try
                if self.syntax.except_block_format == "perl_eval":
                    lines.append(self.indent("eval {", indent_level))
                    lines.append(self.indent("...", indent_level + 1))
                    lines.append(self.indent("};", indent_level))
                else:
                    lines.append(self.indent(first_line, indent_level))
                    lines.append(self.indent("...", indent_level + 1))
                    self._maybe_close_brace(lines, first_line, indent_level)

            elif cf_type == "EXCEPT_BLOCK":
                # Perl special case: if ($@) instead of catch
                if self.syntax.except_block_format == "perl_eval":
                    lines.append(self.indent("if ($@) {", indent_level))
                    lines.append(self.indent("...", indent_level + 1))
                    lines.append(self.indent("}", indent_level))
                else:
                    lines.append(self.indent(first_line, indent_level))
                    lines.append(self.indent("...", indent_level + 1))
                    self._maybe_close_brace(lines, first_line, indent_level)

        # For structure mode, show all control flow
        elif detail_level == "structure":
            lines.append(self.indent(first_line, indent_level))
            lines.append(self.indent("...", indent_level + 1))
            self._maybe_close_brace(lines, first_line, indent_level)

        return "\n".join(lines)

    def _maybe_close_brace(
        self,
        lines: List[str],
        first_line: str,
        indent_level: int
    ) -> None:
        """
        Add closing brace for brace-based languages.

        This is where the Python vs C++/Java/Perl difference lives:
        - Python: do nothing (uses : and indentation)
        - C++/Java/Perl: add } if not already present in heading
        """
        if self.syntax.uses_braces and self.syntax.auto_close_brace:
            if not first_line.endswith('{'):
                lines.append(self.indent("}", indent_level))

    def _format_control_flows(
        self,
        control_flows: List[Dict[str, Any]],
        detail_level: str,
        base_indent: int = 2
    ) -> str:
        """
        Format multiple control flow hints (UNIFIED across all languages).

        Args:
            control_flows: List of control flow frames
            detail_level: "minimal", "guards", or "structure"
            base_indent: Base indentation level (default 2 for inside methods)

        Returns:
            Formatted control flow hints joined with newlines
        """
        lines = []

        for cf in control_flows:
            cf_hint = self.format_control_flow_hint(
                control_flow=cf,
                detail_level=detail_level,
                indent_level=base_indent
            )
            if cf_hint:
                lines.append(cf_hint)

        if not lines:
            lines.append(self.indent("...", base_indent))

        return "\n".join(lines)

    @abstractmethod
    def extract_docstring(
        self,
        content: str
    ) -> Optional[str]:
        """
        Extract docstring from source content.

        Args:
            content: Full source code content (class or method)

        Returns:
            Extracted docstring text without delimiters, or None if not found
        """
        pass

    def indent(self, text: str, level: int) -> str:
        """
        Indent text by specified level (4 spaces per level).

        This is language-agnostic and can be overridden if needed.

        Args:
            text: Text to indent
            level: Indentation level (0, 1, 2, ...)

        Returns:
            Indented text
        """
        indent_str = "    " * level
        return indent_str + text
