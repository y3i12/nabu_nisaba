"""Python language handler implementation"""

import re
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

from .base import LanguageHandler, ImportStatement
from nabu.core.frames import AstFrameBase
from nabu.core.frame_types import FrameNodeType
from nabu.parsing.raw_extraction import RawNode


class PythonHandler(LanguageHandler):
    """Python-specific language handler"""

    def __init__(self):
        super().__init__("python")

    # ==================== FILE DISCOVERY ====================

    def get_file_extensions(self) -> List[str]:
        """Python file extensions"""
        return ['.py', '.pyi', '.pyw']

    # ==================== SEMANTIC MAPPING ====================

    def get_frame_mappings(self) -> Dict[str, FrameNodeType]:
        """Map Python tree-sitter node types to semantic frame types"""
        return {
            'function_definition': FrameNodeType.CALLABLE,
            'async_function_definition': FrameNodeType.CALLABLE,
            'class_definition': FrameNodeType.CLASS,
            # Control flow enabled
            'if_statement': FrameNodeType.IF_BLOCK,
            'elif_clause': FrameNodeType.ELIF_BLOCK,
            'else_clause': FrameNodeType.ELSE_BLOCK,
            'for_statement': FrameNodeType.FOR_LOOP,
            'while_statement': FrameNodeType.WHILE_LOOP,
            'try_statement': FrameNodeType.TRY_BLOCK,
            'except_clause': FrameNodeType.EXCEPT_BLOCK,
            'finally_clause': FrameNodeType.FINALLY_BLOCK,
            'with_statement': FrameNodeType.WITH_BLOCK,
            'match_statement': FrameNodeType.SWITCH_BLOCK,
            'case_clause': FrameNodeType.CASE_BLOCK,
        }

    # ==================== NAME EXTRACTION ====================

    def extract_class_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract class name from Python class definition.
        
        Examples:
            class MyClass:
            class MyClass(BaseClass):
            class MyClass(Base1, Base2):
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # Python: class MyClass(BaseClass):
        if 'class ' in first_line:
            parts = first_line.split()
            for i, part in enumerate(parts):
                if part == 'class' and i + 1 < len(parts):
                    name = parts[i + 1]
                    # Clean up: MyClass(BaseClass): -> MyClass
                    return self._clean_name(name, ['(', ':', '{', '<'])

        return None

    def extract_callable_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract function/method name from Python callable definition.
        
        Examples:
            def function_name(args):
            async def async_function(args):
            def __init__(self):
            def __private_method(self):
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # Python: def function_name(args):
        # Python: async def function_name(args):
        if 'def ' in first_line:
            parts = first_line.split()
            try:
                def_idx = parts.index('def')
                if def_idx + 1 < len(parts):
                    name = parts[def_idx + 1]
                    return self._clean_name(name, ['(', ':'])
            except ValueError:
                pass

        return None

    def extract_package_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract package name from Python import statement.
        
        Note: Python doesn't have explicit package declarations like Java.
        Package structure is inferred from directory structure.
        This method is here for completeness but returns None.
        """
        return None

    # ==================== QUALIFIED NAME GENERATION ====================

    def build_qualified_name(self, frame: AstFrameBase, parent_chain: List[AstFrameBase]) -> str:
        """
        Build fully qualified name with Python module path.
        
        Format: module.submodule.Class.method
        """
        if not parent_chain:
            return frame.name or ""

        # Build qualified name from parent chain
        parts = []
        for parent in parent_chain:
            if parent.type == FrameNodeType.CODEBASE:
                continue  # Skip codebase in qualified names
            if parent.name and parent.name != "unnamed":
                parts.append(parent.name)

        if frame.name and frame.name != "unnamed":
            parts.append(frame.name)

        return self.get_separator().join(parts)

    def get_separator(self) -> str:
        """Python uses dot notation"""
        return "."

    # ==================== PACKAGE HIERARCHY ====================

    def extract_package_hierarchy_from_path(self, file_path: str, codebase_root: str) -> List[str]:
        """
        Extract Python package path from file system path.
        
        Python packages are defined by directory structure:
        - Looks for 'src', 'lib', or 'python' directories
        - Extracts path from there to file
        - Excludes __pycache__ directories
        
        Example:
            /path/to/project/src/mypackage/subpackage/module.py
            -> ['mypackage', 'subpackage']
        """
        path = Path(file_path)
        parts = path.parts

        package_parts = []
        found_src = False

        for part in parts[:-1]:  # Exclude file name
            if part in ['src', 'lib', 'python']:
                found_src = True
                continue
            if found_src and part != '__pycache__':
                package_parts.append(part)

        return package_parts

    def extract_package_from_content(self, file_content: str) -> Optional[str]:
        """
        Python doesn't have package declarations in files.
        Package structure is purely directory-based.
        """
        return None

    # ==================== IMPORT RESOLUTION ====================

    def extract_imports(self, file_content: str) -> List[ImportStatement]:
        """
        Extract Python import statements.
        
        Handles:
            import module
            import module as alias
            from module import name
            from module import name as alias
            from . import relative
            from .. import relative
        """
        imports = []

        # Pattern 1: import module [as alias]
        for match in re.finditer(r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_.]*(?:\s*,\s*[a-zA-Z_][a-zA-Z0-9_.]*)*)', 
                                  file_content, re.MULTILINE):
            modules = match.group(1).split(',')
            for module in modules:
                module = module.strip()
                if ' as ' in module:
                    mod_name, alias = module.split(' as ')
                    imports.append(ImportStatement(
                        import_path=mod_name.strip(),
                        alias=alias.strip()
                    ))
                else:
                    imports.append(ImportStatement(import_path=module))

        # Pattern 2: from module import name [as alias]
        for match in re.finditer(r'^\s*from\s+([a-zA-Z_][a-zA-Z0-9_.]*|\.*[a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+(.+)',
                                  file_content, re.MULTILINE):
            module = match.group(1).strip()
            names = match.group(2).strip()
            
            # Check for wildcard import
            if names == '*':
                imports.append(ImportStatement(
                    import_path=module,
                    is_wildcard=True
                ))
            else:
                # Parse individual names
                for name in names.split(','):
                    name = name.strip()
                    if ' as ' in name:
                        import_name, alias = name.split(' as ')
                        imports.append(ImportStatement(
                            import_path=f"{module}.{import_name.strip()}",
                            alias=alias.strip()
                        ))
                    else:
                        imports.append(ImportStatement(
                            import_path=f"{module}.{name}"
                        ))

        return imports

    def resolve_import(self, import_path: str, current_package: str, language_frame: AstFrameBase) -> Optional[str]:
        """
        Resolve Python import to qualified name.
        
        Handles:
        - Absolute imports: import mypackage.module
        - Relative imports: from . import module
        - Aliased imports: import module as alias
        """
        # Handle relative imports
        if import_path.startswith('.'):
            # Count leading dots
            dots = len(import_path) - len(import_path.lstrip('.'))
            rest = import_path.lstrip('.')
            
            # Navigate up package hierarchy
            current_parts = current_package.split('.')
            if dots > len(current_parts):
                return None  # Invalid relative import
            
            base_parts = current_parts[:len(current_parts) - dots + 1]
            if rest:
                return '.'.join(base_parts + [rest])
            else:
                return '.'.join(base_parts)
        
        # Absolute import
        return import_path

    # ==================== INHERITANCE RESOLUTION ====================

    def extract_base_classes(self, class_content: str, ts_node=None) -> List[str]:
        """
        Extract base class names from Python class definition.
        
        Examples:
            class MyClass(BaseClass):
            class MyClass(Base1, Base2):
            class MyClass(pkg.module.BaseClass):
        
        Args:
            class_content: Class source code content
            ts_node: Optional tree-sitter node for accurate extraction
        """
        # Method 1: Use tree-sitter node if available (most accurate)
        if ts_node is not None:
            # Python: class_definition node structure:
            # - class_definition
            #   - 'class' keyword
            #   - name (identifier)
            #   - argument_list (optional) ← THIS CONTAINS BASE CLASSES
            #     - '('
            #     - argument (base class names)
            #     - ')'
            #   - ':'
            #   - block (body)
            
            for child in ts_node.children:
                if child.type == 'argument_list':
                    # Found base classes list - extract content between parentheses
                    arg_list_text = child.text.decode('utf-8') if isinstance(child.text, bytes) else str(child.text)
                    # Remove outer parentheses
                    if arg_list_text.startswith('(') and arg_list_text.endswith(')'):
                        bases_str = arg_list_text[1:-1]
                        # Split by comma and clean up
                        base_classes = [b.strip() for b in bases_str.split(',') if b.strip()]
                        # Filter out metaclass declarations
                        base_classes = [b for b in base_classes if not b.startswith('metaclass=')]
                        return base_classes
        
        # Method 2: Fallback to string parsing (existing implementation)
        if not class_content or not class_content.strip():
            return []

        lines = [line.strip() for line in class_content.strip().split('\n') if line.strip()]
        if not lines:
            return []

        first_line = lines[0]

        # Python: class MyClass(BaseClass):
        # Python: class MyClass(Base1, Base2):
        if 'class ' in first_line and '(' in first_line:
            # Extract content between parentheses
            match = re.search(r'class\s+\w+\s*\((.*?)\)', first_line)
            if match:
                base_classes_str = match.group(1)
                # Split by comma and clean up
                base_classes = [bc.strip() for bc in base_classes_str.split(',')]
                # Filter out empty strings and metaclass declarations
                base_classes = [bc for bc in base_classes 
                               if bc and not bc.startswith('metaclass=')]
                return base_classes

        return []

    # ==================== HELPER METHODS ====================

    def _extract_function_signature(self, callable_content: str) -> tuple:
        """
        Extract complete function signature handling multi-line definitions.
        
        Returns:
            (signature_params, return_type) tuple
            signature_params: everything between ( and )
            return_type: everything between -> and :, or empty string
        """
        if not callable_content:
            return "", ""
        
        # Find the opening parenthesis after 'def'
        def_match = re.search(r'def\s+(\w+)\s*\(', callable_content)
        if not def_match:
            return "", ""
        
        start_pos = def_match.end() - 1  # Position of opening '('
        
        # Scan for matching closing parenthesis
        paren_depth = 1
        pos = start_pos + 1
        signature_end = -1
        
        while pos < len(callable_content) and paren_depth > 0:
            char = callable_content[pos]
            
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    signature_end = pos
                    break
            
            pos += 1
        
        if signature_end == -1:
            # Malformed function - no closing paren found
            return "", ""
        
        # Extract parameter portion
        params_str = callable_content[start_pos + 1:signature_end]
        
        # Extract return type (after ) look for -> ... :)
        remainder = callable_content[signature_end:]
        return_match = re.search(r'\)\s*->\s*([^:]+):', remainder)
        return_type = return_match.group(1).strip() if return_match else ""
        
        return params_str, return_type

    def _split_parameters(self, params_str: str) -> List[str]:
        """
        Split parameter string by commas, respecting nested brackets.
        
        Example: "a: int, b: List[str, int], c = (1, 2)"
        Returns: ["a: int", "b: List[str, int]", "c = (1, 2)"]
        """
        param_parts = []
        current = []
        depth = 0
        
        for char in params_str + ',':
            if char in '([{':
                depth += 1
            elif char in ')]}':
                depth -= 1
            
            if char == ',' and depth == 0:
                param_parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        
        return [p for p in param_parts if p]  # Filter empty strings

    def _is_dataclass(self, class_content: str, ts_node=None) -> bool:
        """
        Check if class is a dataclass.
        
        If ts_node is provided, checks decorators via tree-sitter AST (accurate).
        Otherwise, uses heuristics on content string (fallback).
        
        Args:
            class_content: Class source code
            ts_node: Optional tree-sitter node for the class
            
        Returns:
            True if class is detected as a dataclass
        """
        # Method 1: Use tree-sitter AST (most accurate)
        if ts_node is not None:
            # For Python, decorated_definition node has decorators as children
            # Check if parent is decorated_definition with @dataclass
            parent = ts_node.parent
            if parent and parent.type == 'decorated_definition':
                for child in parent.children:
                    if child.type == 'decorator':
                        # Get decorator text
                        decorator_text = child.text.decode('utf-8') if isinstance(child.text, bytes) else str(child.text)
                        if 'dataclass' in decorator_text:
                            return True
        
        # Method 2: Check content string for decorator (if tree-sitter didn't work)
        lines = class_content.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('class '):
                # Check previous lines for decorator
                for j in range(max(0, i - 5), i):
                    if re.search(r'@\s*dataclass', lines[j]):
                        return True
                break
        
        # Method 3: Heuristics as fallback
        # Use of field(default_factory=...) is strong indicator
        content_str = '\n'.join(lines)
        if re.search(r'field\s*\(\s*default_factory\s*=', content_str):
            return True
        
        # Multiple consecutive type annotations (3+) suggests dataclass
        in_class_body = False
        consecutive_annotations = 0
        max_consecutive = 0
        
        for line in lines:
            if line.strip().startswith('class '):
                in_class_body = True
                continue
            
            if in_class_body:
                if re.match(r'\s+def ', line):
                    break
                
                if re.match(r'\s+\w+\s*:\s*', line) and not line.strip().startswith('#'):
                    consecutive_annotations += 1
                    max_consecutive = max(max_consecutive, consecutive_annotations)
                elif line.strip() and not line.strip().startswith('#'):
                    consecutive_annotations = 0
        
        return max_consecutive >= 3

    # ==================== FIELD/PARAMETER EXTRACTION ====================

    def extract_instance_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract instance fields from Python class.
        
        Handles both:
        1. Dataclass field declarations (name: Type = value at class level)
        2. Regular instance fields (self.field = value in methods)
        
        Args:
            class_content: Class source code
            ts_node: Optional tree-sitter node for accurate decorator detection
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        if not class_content:
            return fields
        
        # Check if this is a dataclass (with ts_node for accuracy)
        is_dataclass = self._is_dataclass(class_content, ts_node)
        
        lines = class_content.split('\n')
        
        # For dataclasses: extract class-level field declarations
        if is_dataclass:
            class_indent = None
            in_method = False
            method_indent = None
            
            for i, line in enumerate(lines, 1):
                # Find class definition to establish indent level
                if class_indent is None and line.strip().startswith('class '):
                    class_indent = len(line) - len(line.lstrip())
                    continue
                
                if class_indent is None:
                    continue
                
                # Track method boundaries
                method_match = re.match(r'(\s+)def ', line)
                if method_match:
                    in_method = True
                    method_indent = len(method_match.group(1))
                    continue
                
                # Exit method when indentation returns to class level
                if in_method and line.strip():
                    line_indent = len(line) - len(line.lstrip())
                    if line_indent <= class_indent:
                        in_method = False
                        method_indent = None
                
                # Skip if inside method
                if in_method:
                    continue
                
                # Skip if not at class body level
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= class_indent:
                    continue
                
                # Match dataclass field: name: Type OR name: Type = value
                # Must have type annotation (that's what makes it a dataclass field)
                match = re.match(r'\s+(\w+)\s*:\s*([^=]+)(?:\s*=\s*(.+))?', line)
                if match:
                    field_name = match.group(1)
                    type_hint = match.group(2).strip()
                    
                    # Skip special names (__xxx__)
                    if field_name.startswith('__') and field_name.endswith('__'):
                        continue
                    
                    # Skip if it looks like a method annotation (ends with ->)
                    if type_hint.endswith('->'):
                        continue
                    
                    fields.append(FieldInfo(
                        name=field_name,
                        declared_type=type_hint,
                        line=i,
                        confidence=0.95,  # High confidence for dataclass fields
                        is_static=False
                    ))
        
        # For all classes: also check for self.field = value patterns
        for i, line in enumerate(lines, 1):
            # Match: self.field_name = ... or self.field_name: Type = ...
            match = re.match(r'\s*self\.(\w+)\s*(?::\s*([^=]+))?\s*=', line)
            if match:
                field_name = match.group(1)
                type_hint = match.group(2).strip() if match.group(2) else None
                
                # Avoid duplicates (dataclass fields already added)
                if not any(f.name == field_name for f in fields):
                    fields.append(FieldInfo(
                        name=field_name,
                        declared_type=type_hint,
                        line=i,
                        confidence=0.9 if type_hint else 0.7,
                        is_static=False
                    ))
        
        return fields

    def extract_static_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract class-level variables from Python class.
        
        Distinguishes between:
        - Dataclass field declarations (skip these - they're instance fields)
        - Actual static/class variables (capture these)
        
        Args:
            class_content: Class source code
            ts_node: Optional tree-sitter node for accurate decorator detection
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        if not class_content:
            return fields
        
        # Check if this is a dataclass (with ts_node for accuracy)
        is_dataclass = self._is_dataclass(class_content, ts_node)
        
        lines = class_content.split('\n')
        in_method = False
        class_indent = None
        method_indent = None
        
        for i, line in enumerate(lines, 1):
            # Determine indentation levels
            if class_indent is None and line.strip().startswith('class '):
                class_indent = len(line) - len(line.lstrip())
                continue
            
            if class_indent is None:
                continue
            
            # Track method boundaries
            method_match = re.match(r'(\s+)def ', line)
            if method_match:
                in_method = True
                method_indent = len(method_match.group(1))
                continue
            
            # Exit method when indentation returns to class level or less
            if in_method and line.strip():
                line_indent = len(line) - len(line.lstrip())
                if line_indent <= class_indent:
                    in_method = False
                    method_indent = None
            
            # Skip if inside method
            if in_method:
                continue
            
            # Match class-level assignments
            line_indent = len(line) - len(line.lstrip())
            if line_indent <= class_indent:
                continue  # Not inside class body
            
            # Pattern: name: Type = value OR name = value
            match = re.match(r'\s+(\w+)\s*(?::\s*([^=]+))?\s*=\s*(.+)', line)
            if not match:
                continue
            
            field_name = match.group(1)
            type_hint = match.group(2)
            value = match.group(3)
            
            # Skip special names (__xxx__)
            if field_name.startswith('__') and field_name.endswith('__'):
                continue
            
            # If dataclass, skip field declarations with type hints
            # (these are dataclass instance fields, not class variables)
            if is_dataclass and type_hint:
                continue
            
            # Capture as static field
            confidence = 0.8 if type_hint else 0.6
            
            fields.append(FieldInfo(
                name=field_name,
                declared_type=type_hint.strip() if type_hint else None,
                line=i,
                confidence=confidence,
                is_static=True
            ))
        
        return fields

    def extract_parameters(self, callable_content: str, ts_node=None) -> List['ParameterInfo']:
        """
        Extract parameters from Python function/method signature.
        
        Handles both single-line and multi-line signatures:
            def foo(a, b: int, c: str = "default"):
            
            def bar(
                self, 
                x: List[str], 
                *, 
                kwarg: int = 5
            ):
        """
        from nabu.core.field_info import ParameterInfo
        
        params = []
        if not callable_content:
            return params
        
        # Extract full signature using helper
        params_str, _ = self._extract_function_signature(callable_content)
        if not params_str:
            return params
        
        # Clean up whitespace/newlines (replace with single space)
        params_str = re.sub(r'\s+', ' ', params_str).strip()
        
        # Split by comma, respecting nested brackets/parens
        param_parts = self._split_parameters(params_str)
        
        # Parse each parameter
        for pos, param in enumerate(param_parts):
            if not param or param in ('*', '**'):
                continue
            
            # Skip 'self' and 'cls'
            if param.strip() in ('self', 'cls'):
                continue
            
            # Parse: [*|**]name[: type][= default]
            match = re.match(r'(\*\*?)?(\w+)(?:\s*:\s*([^=]+))?(?:\s*=\s*(.+))?', param)
            if match:
                prefix, name, type_hint, default = match.groups()
                
                params.append(ParameterInfo(
                    name=name,
                    declared_type=type_hint.strip() if type_hint else None,
                    default_value=default.strip() if default else None,
                    position=pos
                ))
        
        return params

    def extract_return_type(self, callable_content: str) -> Optional[str]:
        """
        Extract return type annotation from Python function.
        
        Handles both single-line and multi-line signatures:
            def foo() -> int:
            
            def bar(
                x: int
            ) -> List[str]:
        """
        if not callable_content:
            return None
        
        # Use the signature helper
        _, return_type = self._extract_function_signature(callable_content)
        
        return return_type if return_type else None

    # ==================== SPECIAL CASES ====================

    def is_constructor(self, callable_name: str, parent_class_name: str) -> bool:
        """Python constructors are named __init__"""
        return callable_name == '__init__'

    def is_destructor(self, callable_name: str) -> bool:
        """Python destructors are named __del__"""
        return callable_name == '__del__'

    def normalize_callable_name(self, name: str, parent_class: Optional[str]) -> str:
        """
        Python name normalization handles private name mangling.
        
        Private names starting with __ (but not ending with __) are mangled:
        __method in class MyClass becomes _MyClass__method
        """
        if name and name.startswith('__') and not name.endswith('__') and parent_class:
            return f"_{parent_class}{name}"
        return name

    def extract_call_sites(
        self, 
        callable_content: str,
        callable_node: Any
    ) -> List[Tuple[str, int]]:
        """
        Extract function/method call sites from Python callable.
        
        Handles:
        - Simple calls: foo()
        - Method calls: obj.method()
        - Chained calls: obj.method1().method2()
        - Nested calls: outer(inner())
        - Constructor calls: MyClass()
        """
        if not callable_content or not callable_node:
            return []
        
        call_sites = []
        
        def extract_callee_name(call_node) -> Optional[str]:
            """Extract the name being called from a call node."""
            function_node = call_node.child_by_field_name('function')
            if not function_node:
                return None
            
            # Handle different call patterns
            if function_node.type == 'identifier':
                # Simple call: foo()
                return function_node.text.decode('utf-8')
            
            elif function_node.type == 'attribute':
                # Method call: obj.method() or module.func()
                # Get the full chain: obj.attr1.attr2
                parts = []
                current = function_node
                while current and current.type == 'attribute':
                    attr = current.child_by_field_name('attribute')
                    if attr:
                        parts.insert(0, attr.text.decode('utf-8'))
                    current = current.child_by_field_name('object')
                
                # Add the base object/module
                if current and current.type == 'identifier':
                    parts.insert(0, current.text.decode('utf-8'))
                
                return '.'.join(parts) if parts else None
            
            return None
        
        def traverse_for_calls(node):
            """Recursively find all call expressions."""
            if node.type == 'call':
                callee_name = extract_callee_name(node)
                if callee_name:
                    # Line number is 0-indexed in tree-sitter, convert to 1-indexed
                    line_number = node.start_point[0] + 1
                    call_sites.append((callee_name, line_number))
            
            # Recurse into children
            for child in node.children:
                traverse_for_calls(child)
        
        # Start traversal from the callable node
        traverse_for_calls(callable_node)
        
        return call_sites

    def extract_field_usages(
        self, 
        callable_content: str,
        callable_node: Any,
        parent_class_fields: List[str]
    ) -> List[Tuple[str, int, str, str]]:
        """
        Extract field usage sites from Python callable.
        
        Patterns detected:
        - self.field_name (instance field access)
        - cls.field_name (class field access)
        
        Args:
            callable_content: Source code of the callable
            callable_node: Tree-sitter node for the callable
            parent_class_fields: List of field names from parent CLASS frame
                                 (combined instance_fields + static_fields)
        
        Returns:
            List of (field_name, line_number, access_type, pattern_type) tuples
            access_type: "read", "write", or "both"
            pattern_type: "explicit" for self.field and cls.field
        """
        if not callable_content or not callable_node:
            return []
        
        if not parent_class_fields:
            return []  # No fields to check
        
        field_usages = []
        field_set = set(parent_class_fields)  # For O(1) lookup
        
        def determine_access_type(attr_node) -> str:
            """
            Determine if field access is read, write, or both.
            
            Heuristic:
            - If attribute is on LEFT side of assignment → write
            - If in augmented assignment (+=, -=) → both
            - Otherwise → read
            """
            # Check parent node for assignment context
            parent = attr_node.parent
            if not parent:
                return "read"
            
            # Check for assignment (attribute = ...)
            if parent.type == 'assignment':
                left_node = parent.child_by_field_name('left')
                if left_node and left_node == attr_node:
                    return "write"
            
            # Check for augmented assignment (attribute += ...)
            elif parent.type == 'augmented_assignment':
                left_node = parent.child_by_field_name('left')
                if left_node and left_node == attr_node:
                    return "both"
            
            return "read"
        
        def traverse_for_attributes(node):
            """Recursively find all attribute access nodes."""
            if node.type == 'attribute':
                # Extract object and attribute
                obj = node.child_by_field_name('object')
                attr = node.child_by_field_name('attribute')
                
                if obj and attr:
                    obj_text = obj.text.decode('utf-8')
                    attr_text = attr.text.decode('utf-8')
                    
                    # Check if object is 'self' or 'cls'
                    if obj_text in ['self', 'cls']:
                        # Check if attribute is in parent class fields
                        if attr_text in field_set:
                            line_number = node.start_point[0] + 1
                            access_type = determine_access_type(node)
                            field_usages.append((attr_text, line_number, access_type, "explicit"))
            
            # Recurse into children
            for child in node.children:
                traverse_for_attributes(child)
        
        # Start traversal from the callable node
        traverse_for_attributes(callable_node)
        
        return field_usages
