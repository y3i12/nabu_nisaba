"""C++ language handler implementation"""

import re
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple, Any
from pathlib import Path

from .base import LanguageHandler, ImportStatement
from nabu.core.frames import AstFrameBase
from nabu.core.frame_types import FrameNodeType
from nabu.parsing.raw_extraction import RawNode

if TYPE_CHECKING:
    from nabu.core.field_info import FieldInfo, ParameterInfo

class CppHandler(LanguageHandler):
    """C++ specific language handler"""

    def __init__(self):
        super().__init__("cpp")

    # ==================== FILE DISCOVERY ====================

    def get_file_extensions(self) -> List[str]:
        """C++ file extensions"""
        return ['.c', '.h', '.cpp', '.cxx', '.cc', '.hpp', '.hh', '.hxx']

    # ==================== SEMANTIC MAPPING ====================

    def get_frame_mappings(self) -> Dict[str, FrameNodeType]:
        """Map C++ tree-sitter node types to semantic frame types"""
        return {
            'function_definition': FrameNodeType.CALLABLE,  # Includes constructors/destructors
            'struct_specifier': FrameNodeType.CLASS,
            'union_specifier': FrameNodeType.CLASS,
            'enum_specifier': FrameNodeType.CLASS,
            'class_specifier': FrameNodeType.CLASS,
            # Control flow enabled
            'if_statement': FrameNodeType.IF_BLOCK,
            'else_clause': FrameNodeType.ELSE_BLOCK,
            'while_statement': FrameNodeType.WHILE_LOOP,
            'for_statement': FrameNodeType.FOR_LOOP,
            'switch_statement': FrameNodeType.SWITCH_BLOCK,
            'case_statement': FrameNodeType.CASE_BLOCK,
            'try_statement': FrameNodeType.TRY_BLOCK,
        }

    # ==================== NAME EXTRACTION ====================

    def extract_class_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract class/struct/union/enum name from C++ definition.
        
        Examples:
            class MyClass {
            struct MyStruct {
            class MyClass : public BaseClass {
            template<typename T> class MyClass {
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # C++: class MyClass { or struct MyStruct {
        for keyword in ['class', 'struct', 'union', 'enum']:
            if f'{keyword} ' in first_line:
                parts = first_line.split()
                try:
                    idx = parts.index(keyword)
                    if idx + 1 < len(parts):
                        name = parts[idx + 1]
                        return self._clean_name(name, ['{', ':', '<', ';', 'final'])
                except ValueError:
                    pass

        return None

    def extract_callable_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract function/method/constructor/destructor name from C++ definition.
        
        Examples:
            void functionName(args) {
            Type Class::method(args) {
            Class::Class(args) : initializer {      // Constructor
            Class::~Class() {                       // Destructor
            virtual Type method() override {
            auto lambda = [](int x) { };           // Lambdas (may be unnamed)
            operator+(const T& other) {            // Operator overload
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # SPECIAL CASE 1: Destructor - ~ClassName
        if '~' in first_line and '(' in first_line:
            # Pattern: Class::~Class() or ~Class()
            match = re.search(r'~([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', first_line)
            if match:
                destructor_name = match.group(1)
                # Return with tilde prefix to identify as destructor
                return f"~{destructor_name}"

        # SPECIAL CASE 2: Operator overload
        if 'operator' in first_line and '(' in first_line:
            # Pattern: operator+(args) or operator[](args)
            match = re.search(r'operator\s*([+\-*/%&|^~!=<>]+|\[\]|\(\))\s*\(', first_line)
            if match:
                op = match.group(1)
                return f"operator{op}"

        # SPECIAL CASE 3: Constructor - ClassName::ClassName(args)
        if '::' in first_line and '(' in first_line:
            before_paren = first_line.split('(')[0].strip()
            # Check for scope resolution
            if '::' in before_paren:
                parts = before_paren.split('::')
                if len(parts) >= 2:
                    class_part = parts[-2].split()[-1]  # Get class name
                    method_part = parts[-1].split()[-1]  # Get method name
                    
                    # Constructor detection: class name == method name
                    if class_part == method_part:
                        return method_part  # Constructor
                    
                    # Regular method with scope resolution
                    return method_part

        # REGULAR CASE: Function/method name extraction
        if '(' in first_line:
            # Extract everything before the first (
            before_paren = first_line.split('(')[0].strip()
            parts = before_paren.split()

            if parts:
                # Handle C++ scope resolution: Class::method
                last_part = parts[-1]
                if '::' in last_part:
                    method_name = last_part.split('::')[-1]
                    if self._is_valid_identifier(method_name):
                        return method_name
                # Regular function/method name
                elif self._is_valid_identifier(last_part):
                    return last_part

        return None

    def extract_package_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract namespace name from C++ namespace definition.
        
        Examples:
            namespace MyNamespace {
            namespace nested::namespace {
            namespace {  // Anonymous namespace
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # C++: namespace MyNamespace {
        if 'namespace ' in first_line:
            parts = first_line.split()
            try:
                idx = parts.index('namespace')
                if idx + 1 < len(parts):
                    name = parts[idx + 1]
                    # Clean namespace name
                    cleaned = self._clean_name(name, ['{', '::', ';'])
                    # Anonymous namespace returns None
                    if cleaned:
                        return cleaned
            except ValueError:
                pass

        return None

    # ==================== QUALIFIED NAME GENERATION ====================

    def build_qualified_name(self, frame: AstFrameBase, parent_chain: List[AstFrameBase]) -> str:
        """
        Build fully qualified name with C++ namespace path.
        
        Format: namespace::subnamespace::Class::method
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
        """C++ uses :: notation"""
        return "::"

    # ==================== PACKAGE HIERARCHY ====================

    def extract_package_hierarchy_from_path(self, file_path: str, codebase_root: str) -> List[str]:
        """
        Extract C++ namespace path from file system path.
        
        C++ doesn't have enforced package structure, but common conventions:
        - include/namespace/subnamespace/file.h
        - src/namespace/subnamespace/file.cpp
        
        Example:
            /path/to/project/src/core/processing/module.cpp
            -> ['core', 'processing']
        """
        path = Path(file_path)
        parts = path.parts

        package_parts = []
        found_src = False

        for part in parts[:-1]:  # Exclude file name
            if part in ['src', 'include', 'lib']:
                found_src = True
                continue
            if found_src:
                package_parts.append(part)

        return package_parts

    def extract_package_from_content(self, file_content: str) -> Optional[str]:
        """
        Extract namespace from C++ file content.
        
        Looks for namespace declarations at the top of the file.
        """
        lines = file_content.split('\n')
        for line in lines[:50]:  # Check first 50 lines
            line = line.strip()
            if line.startswith('namespace ') and '{' in line:
                # Extract namespace name
                match = re.search(r'namespace\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*{', line)
                if match:
                    return match.group(1)
        
        return None

    # ==================== IMPORT RESOLUTION ====================

    def extract_imports(self, file_content: str) -> List[ImportStatement]:
        """
        C++ #include directives are preprocessor file inclusions, not semantic imports.
        
        Unlike Python/Java imports, C++ includes are textual file-level dependencies:
        - #include "pytypes.h" doesn't create a namespace
        - Real namespaces come from: namespace pybind11 { ... }
        - Tree-sitter already parses namespace declarations → PACKAGE frames
        
        Returning empty list prevents:
        - Phantom PACKAGE frames (e.g., "pybind11./pytypes.h")
        - Useless IMPORTS edges that don't represent semantic relationships
        
        Future: Track file dependencies as metadata, not as namespace imports.
        """
        return []

    def resolve_import(self, import_path: str, current_package: str, language_frame: AstFrameBase) -> Optional[str]:
        """
        Resolve C++ include to qualified name.
        
        C++ imports are header-based, resolution is complex.
        Handles file-system relative paths (../, ./) by stripping them.
        
        Examples:
            "pybind11/pytypes.h" → "pybind11::pytypes"
            "../pytypes.h" → "pytypes"
            "../../core/module.h" → "core::module"
        """
        # Strip file-system relative navigation (./ and ../)
        # These are file-system concepts, not namespace concepts
        import re
        # Remove leading ./ and any number of ../
        import_path = re.sub(r'^(\.\.?/)+', '', import_path)
        
        # Convert path separators to namespace separators
        # e.g., "core/processor.h" -> "core::processor"
        qualified = import_path.replace('/', '::').replace('\\', '::')
        # Remove file extension
        qualified = Path(qualified).stem
        return qualified

    # ==================== INHERITANCE RESOLUTION ====================

    def extract_base_classes(self, class_content: str, ts_node=None) -> List[str]:
        """
        Extract base class names from C++ class definition.
        
        Examples:
            class Derived : public Base {
            class Derived : public Base1, private Base2 {
            class Derived : Base {  // private by default for class
        
        Args:
            class_content: Class source code content
            ts_node: Optional tree-sitter node for accurate extraction
        """
        # Method 1: Use tree-sitter node if available (most accurate)
        if ts_node is not None:
            # C++: class_specifier node structure
            # Look for base_class_clause child
            for child in ts_node.children:
                if child.type == 'base_class_clause':
                    # Extract base class names from this clause
                    base_classes = []
                    for base_child in child.children:
                        if base_child.type in ['type_identifier', 'scoped_type_identifier', 'template_type']:
                            base_name = base_child.text.decode('utf-8') if isinstance(base_child.text, bytes) else str(base_child.text)
                            base_classes.append(base_name)
                    if base_classes:
                        return base_classes
        
        # Method 2: Fallback to string parsing (existing implementation)
        if not class_content or not class_content.strip():
            return []

        lines = [line.strip() for line in class_content.strip().split('\n') if line.strip()]
        if not lines:
            return []

        first_line = lines[0]

        # C++: class Derived : public Base {
        if ':' in first_line and 'class ' in first_line:
            # Extract content after : and before {
            match = re.search(r'class\s+\w+\s*:\s*([^{]+)', first_line)
            if match:
                inheritance_str = match.group(1)
                # Parse inheritance list: public Base1, private Base2, etc.
                base_classes = []
                # Split by comma
                for part in inheritance_str.split(','):
                    part = part.strip()
                    # Remove access specifiers (public, private, protected, virtual)
                    part = re.sub(r'\b(public|private|protected|virtual)\b', '', part).strip()
                    if part and self._is_valid_identifier(part.split()[0]):
                        base_classes.append(part.split()[0])
                return base_classes

        return []

    # ==================== FRAME FIELDS ====================
    # ==================== HELPER METHODS ====================

    def _split_cpp_parameters(self, params_str: str) -> List[str]:
        """
        Split C++ parameter string by commas, respecting templates and nested structures.
        
        Example: "int x, const std::vector<T>& items, Func<int, bool> callback"
        """
        param_parts = []
        current = []
        depth = 0
        
        for char in params_str + ',':
            if char in '<({':
                depth += 1
            elif char in '>)}':
                depth -= 1
            
            if char == ',' and depth == 0:
                param_parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        
        return [p for p in param_parts if p]

    def _clean_cpp_type(self, type_str: str) -> str:
        """
        Clean up C++ type string by normalizing whitespace.
        
        Example: "const  std::vector<int> &" -> "const std::vector<int>&"
        """
        # Remove extra whitespace
        type_str = re.sub(r'\s+', ' ', type_str).strip()
        # Remove space before & and *
        type_str = re.sub(r'\s+([&*])', r'\1', type_str)
        return type_str

    # ==================== TREE-SITTER HELPER METHODS ====================

    def _find_node_by_type(self, node, target_type: str, recursive: bool = True):
        """
        Find first node of given type.
        
        Args:
            node: Tree-sitter node to search
            target_type: Node type to find
            recursive: Whether to search recursively in children
            
        Returns:
            First matching node or None
        """
        if node is None:
            return None
            
        if node.type == target_type:
            return node
        
        if recursive:
            for child in node.children:
                result = self._find_node_by_type(child, target_type, recursive=True)
                if result:
                    return result
        
        return None

    def _find_all_nodes_by_type(self, node, target_type: str) -> List:
        """
        Find all nodes of given type recursively.
        
        Args:
            node: Tree-sitter node to search
            target_type: Node type to find
            
        Returns:
            List of matching nodes
        """
        results = []
        if node is None:
            return results
            
        if node.type == target_type:
            results.append(node)
        
        for child in node.children:
            results.extend(self._find_all_nodes_by_type(child, target_type))
        
        return results

    def _get_node_text(self, node) -> str:
        """
        Get text content of a tree-sitter node.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            UTF-8 decoded text of the node
        """
        if node is None:
            return ""
        return node.text.decode('utf-8') if isinstance(node.text, bytes) else str(node.text)

    def _debug_log_node_tree(self, node, depth: int = 0, max_depth: int = 3, prefix: str = "") -> str:
        """
        Debug helper to visualize tree-sitter node structure.
        
        Args:
            node: Tree-sitter node
            depth: Current depth
            max_depth: Maximum depth to traverse
            prefix: Indentation prefix
            
        Returns:
            String representation of tree
        """
        if node is None or depth > max_depth:
            return ""
        
        indent = "  " * depth
        text_preview = self._get_node_text(node)[:50].replace('\n', '\\n')
        result = f"{indent}{prefix}{node.type}: '{text_preview}'\n"
        
        if depth < max_depth:
            for i, child in enumerate(node.children):
                result += self._debug_log_node_tree(child, depth + 1, max_depth, f"[{i}] ")
        
        return result

    def _extract_type_from_any_node(self, node, depth: int = 0, max_depth: int = 3) -> str:
        """
        Recursively extract type string from any tree-sitter node.
        
        Handles deeply nested type structures like:
            template_type -> qualified_type_identifier
            type_specifier -> qualified_type_identifier
            
        This is needed because C++ type nodes can be nested 2-3 levels deep
        in the AST, unlike simpler languages.
        
        Args:
            node: Any tree-sitter node that might contain type info
            depth: Current recursion depth (internal use)
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            Type string extracted from node tree
        """
        if node is None or depth >= max_depth:
            return ""
        
        # Direct type nodes - extract text immediately
        if node.type in [
            'type_identifier',
            'qualified_identifier',
            'qualified_type_identifier',    # C++ namespace::Type
            'scoped_type_identifier',       # C++ alternative syntax
            'dependent_type',               # typename T::Type
            'primitive_type',
            'template_type',
            'auto',                         # C++11 auto
            'decltype',                     # decltype(expr)
        ]:
            return self._get_node_text(node)
        
        # Container nodes - recurse into children
        if node.type in [
            'type_specifier',
            '_declaration_specifiers',
            'struct_specifier',
            'union_specifier',
            'enum_specifier',
            'class_specifier',
            'sized_type_specifier',
        ]:
            # Recursively extract from all children
            type_parts = []
            for child in node.children:
                # Skip non-type tokens
                if child.type in ['{', '}', ';', 'struct', 'class', 'enum', 'union']:
                    continue
                
                child_type = self._extract_type_from_any_node(child, depth + 1, max_depth)
                if child_type:
                    type_parts.append(child_type)
            
            return ' '.join(type_parts)
        
        # Unknown node type - return empty
        return ""

    def _extract_type_from_specifiers(self, node) -> str:
        """
        Extract type string from _declaration_specifiers node.
        
        Handles:
        - type_identifier: int, bool, etc.
        - qualified_type_identifier: std::string (C++)
        - scoped_type_identifier: namespace::Type (C++)
        - primitive_type: int, char, void
        - template_type: std::vector<int>
        - struct_specifier, union_specifier, enum_specifier
        - type qualifiers: const, volatile
        - auto, decltype (C++11+)
        
        Args:
            node: _declaration_specifiers or similar node
            
        Returns:
            Type string (e.g., "const std::string", "int")
        """
        import re
        
        type_parts = []
        
        if node is None:
            return ""
        
        # Traverse children looking for type-related nodes
        for child in node.children:
            if child.type == 'type_qualifier':
                # const, volatile, restrict
                type_parts.append(self._get_node_text(child))
            
            # CHANGE 1: Expanded node type list for C++
            elif child.type in [
                'type_identifier',
                'qualified_identifier',         # Keep for compatibility
                'qualified_type_identifier',    # C++ namespace::Type
                'scoped_type_identifier',       # C++ alternative syntax
                'dependent_type',               # typename T::Type
                'primitive_type',
                'template_type',
                'struct_specifier',
                'union_specifier',
                'enum_specifier',
                'class_specifier',
                'sized_type_specifier',
                'auto',                         # C++11 auto keyword
                'decltype',                     # decltype(expr)
            ]:
                type_parts.append(self._get_node_text(child))
            
            # CHANGE 2: Use new recursive helper for nested types
            elif child.type == 'type_specifier':
                # Use recursive helper to handle deeply nested structures
                nested_type = self._extract_type_from_any_node(child)
                if nested_type:
                    type_parts.append(nested_type)
        
        # CHANGE 3: Fallback to full node text if we couldn't parse structure
        if not type_parts and node:
            # Extract full text from _declaration_specifiers
            # This captures the type even if we don't understand the structure
            full_text = self._get_node_text(node)
            # Clean up: remove storage class specifiers (keep qualifiers like 'const')
            full_text = re.sub(r'\b(static|inline|virtual|explicit|extern|mutable)\b', '', full_text)
            return full_text.strip()
        
        return ' '.join(type_parts)

    def _extract_identifier_from_declarator(self, declarator_node) -> Optional[str]:
        """
        Extract identifier name from declarator node.
        
        Handles:
        - field_identifier (for fields)
        - identifier (for parameters)
        - pointer_declarator, reference_declarator
        - array_declarator
        - function_declarator
        
        Args:
            declarator_node: Declarator tree-sitter node
            
        Returns:
            Identifier name or None
        """
        if declarator_node is None:
            return None
        
        # Direct identifier
        if declarator_node.type in ['field_identifier', 'identifier']:
            return self._get_node_text(declarator_node)
        
        # Search in children for identifier
        for child in declarator_node.children:
            # Recursively search in nested declarators
            if child.type in [
                'pointer_declarator',
                'pointer_field_declarator',
                'reference_declarator',
                'array_declarator',
                'array_field_declarator',
                'function_declarator',
                'function_field_declarator',
                'parenthesized_declarator',
                'parenthesized_field_declarator',
            ]:
                result = self._extract_identifier_from_declarator(child)
                if result:
                    return result
            
            # Found identifier
            elif child.type in ['field_identifier', 'identifier']:
                return self._get_node_text(child)
        
        return None

    def _extract_type_modifiers_from_declarator(self, declarator_node) -> str:
        """
        Extract type modifiers (*, &, []) from declarator node.
        
        Args:
            declarator_node: Declarator tree-sitter node
            
        Returns:
            String of modifiers (e.g., "*", "&", "**", "*&")
        """
        modifiers = []
        
        if declarator_node is None:
            return ""
        
        # Check current node type
        if 'pointer' in declarator_node.type:
            modifiers.append('*')
        elif 'reference' in declarator_node.type:
            modifiers.append('&')
        
        # Recursively check children
        for child in declarator_node.children:
            if child.type in [
                'pointer_declarator',
                'pointer_field_declarator',
                'reference_declarator',
            ]:
                nested_modifiers = self._extract_type_modifiers_from_declarator(child)
                modifiers.append(nested_modifiers)
        
        return ''.join(modifiers)

    def _is_static_field(self, field_decl_node) -> bool:
        """
        Check if field_declaration node has static storage class.
        
        Args:
            field_decl_node: field_declaration tree-sitter node
            
        Returns:
            True if field is static
        """
        if field_decl_node is None:
            return False
        
        # Look for storage_class_specifier with text "static"
        for child in field_decl_node.children:
            if child.type == 'storage_class_specifier':
                if self._get_node_text(child) == 'static':
                    return True
            
            # storage_class_specifier might be nested in _declaration_specifiers
            elif child.type == '_declaration_specifiers':
                for nested in child.children:
                    if nested.type == 'storage_class_specifier':
                        if self._get_node_text(nested) == 'static':
                            return True
        
        return False

    # ==================== FIELD/PARAMETER EXTRACTION ====================

    def extract_instance_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract instance fields from C++ class/struct using tree-sitter AST.
        
        Patterns:
            int count_;
            std::string name_ = "default";
            const std::vector<int>& items_;
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        
        # CRITICAL: Use tree-sitter AST if available
        if ts_node is None:
            # Fallback to regex for backward compatibility
            return self._extract_fields_regex(class_content, is_static=False)
        
        # Find field_declaration_list (class body)
        field_list = self._find_node_by_type(ts_node, 'field_declaration_list')
        
        if not field_list:
            return fields
        
        # Iterate through class body looking for field_declaration nodes
        for node in field_list.children:
            # In C++, field_declaration_list contains multiple node types:
            # - field_declaration (actual fields)
            # - inline_method_definition (methods)
            # - constructor_or_destructor_definition
            # - access_specifier (public:, private:, protected:)
            # - template_declaration
            # Only process actual field_declaration nodes
            if node.type != 'field_declaration':
                continue
            
            # Additional check: field_declaration can contain methods in C++
            # If it has a function_declarator, it's a method declaration, not a field
            has_function_declarator = self._find_node_by_type(node, 'function_declarator', recursive=False)
            if has_function_declarator:
                continue  # This is a method declaration, skip it
            
            # Check if static - skip static fields in instance method
            if self._is_static_field(node):
                continue
            
            # Extract field information from this field_declaration
            field_info = self._extract_field_from_declaration(node)
            if field_info:
                fields.append(field_info)
        
        return fields

    def _extract_field_from_declaration(self, decl_node) -> Optional['FieldInfo']:
        """
        Extract field information from field_declaration node.
        
        C++ field_declaration has TWO possible structures:
        
        Structure 1 (with _declaration_specifiers wrapper):
            field_declaration
            ├── _declaration_specifiers
            │   ├── type_qualifier (const, volatile)
            │   └── type nodes
            ├── declarator
            └── ;
            
        Structure 2 (types as direct children - MOST COMMON):
            field_declaration
            ├── type_qualifier (const, volatile) - direct child!
            ├── qualified_identifier (std::string) - direct child!
            ├── pointer/reference_declarator
            └── ;
        """
        from nabu.core.field_info import FieldInfo
        import os
        
        if decl_node is None:
            return None
        
        # DEBUG: Log node structure
        if os.getenv('NABU_DEBUG_TYPES') == '1':
            debug_tree = self._debug_log_node_tree(decl_node, max_depth=2)
            print(f"\n=== FIELD_DECLARATION DEBUG ===\n{debug_tree}")
        
        field_name = None
        field_type = ""
        line_num = decl_node.start_point[0]
        
        # Step 1: Try to extract type from _declaration_specifiers (if it exists)
        decl_specifiers = self._find_node_by_type(decl_node, '_declaration_specifiers', recursive=False)
        if decl_specifiers:
            field_type = self._extract_type_from_specifiers(decl_specifiers)
        else:
            # No _declaration_specifiers wrapper - extract type from direct children!
            type_parts = []
            
            for child in decl_node.children:
                # Extract type qualifiers (const, volatile)
                if child.type == 'type_qualifier':
                    type_parts.append(self._get_node_text(child))
                
                # Extract type nodes directly
                elif child.type in [
                    'type_identifier',
                    'qualified_identifier',
                    'qualified_type_identifier',
                    'scoped_type_identifier',
                    'dependent_type',
                    'primitive_type',
                    'template_type',
                    'struct_specifier',
                    'union_specifier',
                    'enum_specifier',
                    'class_specifier',
                    'sized_type_specifier',
                    'auto',
                    'decltype',
                ]:
                    type_parts.append(self._get_node_text(child))
            
            field_type = ' '.join(type_parts)
        
        if os.getenv('NABU_DEBUG_TYPES') == '1':
            print(f"Extracted base type: '{field_type}'")
        
        # Step 2: Extract declarator (contains name and modifiers)
        declarator = None
        
        for child in decl_node.children:
            # Skip non-declarator nodes
            if child.type in ['_declaration_specifiers', ';', 'attribute_specifier',
                              'type_qualifier', 'type_identifier', 'qualified_identifier',
                              'qualified_type_identifier', 'primitive_type', 'template_type',
                              'struct_specifier', 'union_specifier', 'enum_specifier',
                              'class_specifier', '=', 'number_literal', 'null']:
                continue
            
            # Find declarator
            if child.type in ['reference_declarator', 'pointer_declarator', 
                              'field_identifier', 'init_declarator',
                              'pointer_field_declarator', 'reference_field_declarator',
                              'array_field_declarator']:
                declarator = child
                break
        
        if declarator:
            # Extract name
            field_name = self._extract_identifier_from_declarator(declarator)
            
            # Extract modifiers (*, &)
            modifiers = self._extract_type_modifiers_from_declarator(declarator)
            if modifiers:
                field_type = field_type.strip() + modifiers
            
            if os.getenv('NABU_DEBUG_TYPES') == '1':
                print(f"Field: name='{field_name}', type='{field_type}', modifiers='{modifiers}'")
        
        if not field_name:
            return None
        
        return FieldInfo(
            name=field_name,
            declared_type=self._clean_cpp_type(field_type),
            line=line_num + 1,
            confidence=0.95,
            is_static=False
        )

    def _extract_fields_regex(self, class_content: str, is_static: bool) -> List['FieldInfo']:
        """
        Regex fallback for field extraction (backward compatibility).
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        if not class_content:
            return fields
        
        lines = class_content.split('\n')
        in_method = False
        
        for i, line in enumerate(lines, 1):
            # Skip method definitions
            if re.search(r'\w+\s*\([^)]*\)\s*(?:const)?\s*\{', line):
                in_method = True
            if in_method and '}' in line:
                in_method = False
                continue
            if in_method:
                continue
            
            # Skip function declarations
            if '(' in line and ')' in line:
                continue
            
            # Match field pattern
            if is_static:
                pattern = (
                    r'\s*'
                    r'(?:inline\s+)?'
                    r'static\s+'
                    r'(?:const\s+)?'
                    r'([\w:_<>,\s]+?)'
                    r'\s*([&*]*)\s*'
                    r'(\w+)'
                    r'(?:\s*=\s*([^;]+))?'
                    r'\s*;'
                )
            else:
                pattern = (
                    r'\s*'
                    r'(?!static\s+)'
                    r'((?:const\s+)?[\w:_<>,\s]+?)'
                    r'\s*([&*]*)\s*'
                    r'(\w+)'
                    r'(?:\s*=\s*([^;]+))?'
                    r'\s*;'
                )
            
            match = re.match(pattern, line)
            if match:
                field_type, ref_ptr, field_name, initializer = match.groups()
                full_type = self._clean_cpp_type(field_type + ref_ptr)
                
                if 'typedef' not in field_type and 'using' not in field_type:
                    fields.append(FieldInfo(
                        name=field_name,
                        declared_type=full_type,
                        line=i,
                        confidence=0.85,
                        is_static=is_static
                    ))
        
        return fields

    def extract_static_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract static fields from C++ class/struct using tree-sitter AST.
        
        Patterns:
            static int count_;
            static const std::string NAME;
            inline static int value = 0;  // C++17
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        
        # CRITICAL: Use tree-sitter AST if available
        if ts_node is None:
            # Fallback to regex
            return self._extract_fields_regex(class_content, is_static=True)
        
        # Find field_declaration_list (class body)
        field_list = self._find_node_by_type(ts_node, 'field_declaration_list')
        
        if not field_list:
            return fields
        
        # Iterate through class body looking for field_declaration nodes
        for node in field_list.children:
            # Only process actual field_declaration nodes (same filtering as instance fields)
            if node.type != 'field_declaration':
                continue
            
            # Additional check: skip method declarations
            has_function_declarator = self._find_node_by_type(node, 'function_declarator', recursive=False)
            if has_function_declarator:
                continue  # This is a method declaration, skip it
            
            # Check if static - only process static fields
            if not self._is_static_field(node):
                continue
            
            # Extract field information from this field_declaration
            field_info = self._extract_field_from_declaration(node)
            if field_info:
                # Mark as static
                field_info.is_static = True
                fields.append(field_info)
        
        return fields

    def extract_parameters(self, callable_content: str, ts_node=None) -> List['ParameterInfo']:
        """
        Extract parameters from C++ function/method using tree-sitter AST.
        
        Examples:
            void foo(int x, const std::string& name, bool flag = true)
            auto bar(T value) -> decltype(value)
            template<typename T> T get(const T& value)
        """
        from nabu.core.field_info import ParameterInfo
        
        params = []
        
        # CRITICAL: Use tree-sitter AST if available
        if ts_node is None:
            # Fallback to regex
            return self._extract_parameters_regex(callable_content)
        
        # Find parameter_list node in the function_definition
        param_list = self._find_parameter_list(ts_node)
        
        if not param_list:
            return params
        
        # Process each parameter_declaration
        position = 0
        for node in param_list.children:
            if node.type in ['parameter_declaration', 'optional_parameter_declaration']:
                param_info = self._extract_parameter_from_declaration(node, position)
                if param_info:
                    params.append(param_info)
                    position += 1
            elif node.type == 'variadic_parameter_declaration':
                # Handle variadic parameters: int... args
                param_info = self._extract_parameter_from_declaration(node, position)
                if param_info:
                    params.append(param_info)
                    position += 1
        
        return params

    def _find_parameter_list(self, node):
        """
        Find parameter_list node in function_definition.
        
        Tree structure:
            function_definition
            ├── declarator: function_declarator
            │   ├── declarator: identifier (function name)
            │   └── parameters: parameter_list
            │       ├── parameter_declaration
            │       ├── parameter_declaration
            │       └── ...
            └── body: compound_statement
        """
        if node is None:
            return None
        
        # Direct match
        if node.type == 'parameter_list':
            return node
        
        # Search in children
        for child in node.children:
            if child.type in ['function_declarator', 'declarator']:
                # Recurse into declarator
                result = self._find_parameter_list(child)
                if result:
                    return result
            elif child.type == 'parameter_list':
                return child
        
        return None

    def _extract_parameter_from_declaration(self, param_node, position: int) -> Optional['ParameterInfo']:
        """
        Extract parameter from parameter_declaration node.
        
        Tree structure:
            parameter_declaration
            ├── _declaration_specifiers (type)
            ├── [optional] declarator (name and modifiers)
            └── [optional] default_value
            
        Or for optional_parameter_declaration:
            optional_parameter_declaration
            ├── _declaration_specifiers (type)
            ├── declarator
            ├── "="
            └── default_value: expression
        """
        from nabu.core.field_info import ParameterInfo
        
        if param_node is None:
            return None
        
        param_name = None
        param_type = ""
        default_val = None
        
        # Step 1: Extract type from _declaration_specifiers
        decl_specifiers = self._find_node_by_type(param_node, '_declaration_specifiers', recursive=False)
        if decl_specifiers:
            param_type = self._extract_type_from_specifiers(decl_specifiers)
        
        # Step 2: Find declarator (contains name and modifiers)
        declarator = None
        for child in param_node.children:
            if 'declarator' in child.type and child.type != '_declaration_specifiers':
                declarator = child
                break
        
        if declarator:
            # Extract name
            param_name = self._extract_identifier_from_declarator(declarator)
            
            # Extract modifiers (*, &)
            modifiers = self._extract_type_modifiers_from_declarator(declarator)
            if modifiers:
                param_type = param_type + modifiers
        
        # Step 3: Extract default value for optional parameters
        if param_node.type == 'optional_parameter_declaration':
            # Find expression node after "="
            found_equals = False
            for child in param_node.children:
                if found_equals and child.type != ',':
                    default_val = self._get_node_text(child)
                    break
                if self._get_node_text(child) == '=':
                    found_equals = True
        
        # Anonymous parameter (valid in C++)
        if not param_name:
            param_name = f"_unnamed_param_{position}"
        
        return ParameterInfo(
            name=param_name,
            declared_type=self._clean_cpp_type(param_type),
            default_value=default_val,
            position=position
        )

    def _extract_parameters_regex(self, callable_content: str) -> List['ParameterInfo']:
        """
        Regex fallback for parameter extraction (backward compatibility).
        """
        from nabu.core.field_info import ParameterInfo
        
        params = []
        if not callable_content:
            return params
        
        # Extract signature between ( and ), handling multi-line
        signature_match = re.search(
            r'\w+\s*\((.*?)\)\s*(?:const)?\s*(?:->\s*[\w:<>,\s&*]+)?\s*\{',
            callable_content,
            re.DOTALL
        )
        
        if not signature_match:
            return params
        
        params_str = signature_match.group(1)
        params_str = re.sub(r'\s+', ' ', params_str).strip()
        
        if not params_str:
            return params
        
        # Split by comma (respecting templates <...>)
        param_parts = self._split_cpp_parameters(params_str)
        
        for pos, param in enumerate(param_parts):
            param = param.strip()
            if not param:
                continue
            
            # Parse: [const] Type [*&] name [= default]
            match = re.match(
                r'((?:const\s+)?[\w:<>,\s]+?)'
                r'\s*([&*]*)\s*'
                r'(\w+)'
                r'(?:\s*=\s*(.+))?',
                param
            )
            
            if match:
                param_type, ref_ptr, param_name, default_val = match.groups()
                full_type = self._clean_cpp_type(param_type + ref_ptr)
                
                params.append(ParameterInfo(
                    name=param_name,
                    declared_type=full_type,
                    default_value=default_val.strip() if default_val else None,
                    position=pos
                ))
        
        return params

    def extract_return_type(self, callable_content: str) -> Optional[str]:
        """
        Extract return type from C++ function/method.
        
        Handles both traditional and trailing return types:
            void foo()                    -> "void"
            std::vector<int> bar()        -> "std::vector<int>"
            auto baz() -> int             -> "int" (trailing)
            template<typename T> T get()  -> "T"
        """
        if not callable_content:
            return None
        
        first_line = callable_content.split('\n')[0]
        
        # Check for trailing return type: auto name(...) -> ReturnType
        trailing_match = re.search(
            r'auto\s+\w+\s*\([^)]*\)\s*(?:const)?\s*->\s*([\w:<>,\s&*]+)',
            first_line
        )
        if trailing_match:
            return_type = trailing_match.group(1).strip()
            return self._clean_cpp_type(return_type)
        
        # Traditional return type: ReturnType name(...)
        # Pattern: [template<...>] ReturnType functionName(
        match = re.search(
            r'(?:template\s*<[^>]+>\s+)?'  # Optional template
            r'([\w:<>,\s&*]+?)'  # Return type
            r'\s+(\w+)\s*\(',  # Function name
            first_line
        )
        
        if match:
            return_type = match.group(1).strip()
            
            # Filter out keywords that aren't return types
            if return_type in ('virtual', 'static', 'inline', 'constexpr', 'explicit'):
                # These are modifiers, look for actual type after them
                type_match = re.search(
                    r'(?:virtual|static|inline|constexpr|explicit)\s+([\w:<>,\s&*]+?)\s+\w+\s*\(',
                    first_line
                )
                if type_match:
                    return_type = type_match.group(1).strip()
            
            return self._clean_cpp_type(return_type)

        return None

    # ==================== SPECIAL CASES ====================

    def is_constructor(self, callable_name: str, parent_class_name: str) -> bool:
        """C++ constructors have the same name as the class"""
        return callable_name == parent_class_name

    def is_destructor(self, callable_name: str) -> bool:
        """C++ destructors start with ~"""
        return callable_name.startswith('~')

    def normalize_callable_name(self, name: str, parent_class: Optional[str]) -> str:
        """
        C++ name normalization for special cases.
        
        - Destructors: Keep ~ClassName format
        - Operators: Keep operator+ format
        - Regular names: No change needed
        """
        return name

    # ==================== CALL SITE EXTRACTION HELPERS ====================

    def _extract_name_from_field_expression(self, field_expr_node) -> Optional[str]:
        """
        Extract qualified name from field_expression node.
        
        Handles:
        - obj.method → "obj.method"
        - ptr->method → "ptr.method" 
        - this->method → "method"
        - obj.field.method → "obj.field.method" (chained)
        
        Args:
            field_expr_node: field_expression tree-sitter node
            
        Returns:
            Qualified name string or None
        """
        if field_expr_node is None or field_expr_node.type != 'field_expression':
            return None
        
        # Extract the field/method name (right side)
        field_node = field_expr_node.child_by_field_name('field')
        if not field_node:
            return None
        
        field_name = self._get_node_text(field_node)
        
        # Handle template methods - extract base name
        if field_node.type == 'template_method':
            # template_method contains the method name before <
            for child in field_node.children:
                if child.type == 'identifier':
                    field_name = self._get_node_text(child)
                    break
        
        # Extract the object/receiver (left side)
        argument_node = field_expr_node.child_by_field_name('argument')
        if not argument_node:
            return field_name
        
        # Check if argument is "this" - skip it
        arg_text = self._get_node_text(argument_node)
        if arg_text == 'this':
            return field_name
        
        # Build qualified name
        # For simple identifiers, use as-is
        if argument_node.type == 'identifier':
            return f"{arg_text}.{field_name}"
        
        # For nested field_expression (chained calls), recurse
        elif argument_node.type == 'field_expression':
            nested_name = self._extract_name_from_field_expression(argument_node)
            if nested_name:
                return f"{nested_name}.{field_name}"
        
        # For other expression types, try to get text
        else:
            # For complex expressions, just use the field name
            # (resolver will need context to figure it out)
            return field_name
        
        return field_name

    def _extract_callee_from_call_expression(self, call_node) -> Optional[str]:
        """
        Extract callee name from call_expression node.
        
        Handles:
        - Simple calls: foo() → "foo"
        - Qualified calls: std::func() → "std::func"
        - Method calls: obj.method() → "obj.method"
        - Static calls: Class::method() → "Class::method"
        - Template calls: func<T>() → "func"
        
        Args:
            call_node: call_expression tree-sitter node
            
        Returns:
            Callee name or None
        """
        if call_node is None or call_node.type != 'call_expression':
            return None
        
        # Get the function node (what's being called)
        function_node = call_node.child_by_field_name('function')
        if not function_node:
            return None
        
        # Handle different function node types
        
        # 1. Simple identifier: foo()
        if function_node.type == 'identifier':
            return self._get_node_text(function_node)
        
        # 2. Qualified identifier: std::cout, namespace::func, Class::method
        elif function_node.type in ['qualified_identifier', 'scoped_identifier']:
            return self._get_node_text(function_node)
        
        # 3. Field expression: obj.method(), ptr->method()
        elif function_node.type == 'field_expression':
            return self._extract_name_from_field_expression(function_node)
        
        # 4. Template function: func<T>()
        elif function_node.type == 'template_function':
            # Extract the base function name (before <)
            for child in function_node.children:
                if child.type in ['identifier', 'qualified_identifier', 'scoped_identifier']:
                    return self._get_node_text(child)
        
        # 5. Template method: obj.method<T>()
        elif function_node.type == 'template_method':
            # template_method is similar to template_function
            for child in function_node.children:
                if child.type in ['identifier', 'qualified_identifier', 'scoped_identifier']:
                    return self._get_node_text(child)
        
        # 6. Primitive type cast: int(x) - skip these
        elif function_node.type == 'primitive_type':
            return None
        
        # Fallback: try to get text directly
        else:
            try:
                return self._get_node_text(function_node)
            except:
                return None

    def _extract_callee_from_new_expression(self, new_node) -> Optional[str]:
        """
        Extract class name from new_expression node.
        
        Handles:
        - Simple: new MyClass() → "MyClass"
        - Qualified: new std::string() → "std::string"
        - Template: new std::vector<int>() → "std::vector"
        
        Args:
            new_node: new_expression tree-sitter node
            
        Returns:
            Class name or None
        """
        if new_node is None or new_node.type != 'new_expression':
            return None
        
        # Get the type being constructed
        type_node = new_node.child_by_field_name('type')
        if not type_node:
            return None
        
        # Extract type name
        type_text = self._get_node_text(type_node)
        
        # For template types, extract base class name
        # e.g., "std::vector<int>" → "std::vector"
        if '<' in type_text:
            type_text = type_text.split('<')[0].strip()
        
        return type_text if type_text else None

    def extract_call_sites(
        self, 
        callable_content: str,
        callable_node: Any
    ) -> List[Tuple[str, int]]:
        """
        Extract function/method call sites from C++ callable.
        
        Handles:
        - Function calls: foo()
        - Method calls: obj.method(), obj->method()
        - Namespace calls: std::func(), namespace::func()
        - Static calls: Class::staticMethod()
        - Template calls: func<T>() → extracts "func"
        - Constructor calls: new MyClass()
        
        Args:
            callable_content: Source code of the callable
            callable_node: Tree-sitter node for the callable
            
        Returns:
            List of (callee_name, line_number) tuples
        """
        if not callable_content or not callable_node:
            return []
        
        call_sites = []
        
        def traverse_for_calls(node):
            """Recursively find all call expressions."""
            # 1. Handle call_expression nodes (function/method calls)
            if node.type == 'call_expression':
                callee_name = self._extract_callee_from_call_expression(node)
                if callee_name:
                    # Line number is 0-indexed in tree-sitter, convert to 1-indexed
                    line_number = node.start_point[0] + 1
                    call_sites.append((callee_name, line_number))
            
            # 2. Handle new_expression nodes (constructor calls)
            elif node.type == 'new_expression':
                callee_name = self._extract_callee_from_new_expression(node)
                if callee_name:
                    line_number = node.start_point[0] + 1
                    call_sites.append((callee_name, line_number))
            
            # 3. Recurse into children
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
        Extract field usage sites from C++ callable.
        
        Patterns detected:
        - this->field_name (explicit this pointer)
        - ClassName::static_field (static field access)
        
        Note: Implicit field access (field without this->) is NOT detected
        in Phase 1 due to ambiguity with local variables.
        
        Args:
            callable_content: Source code of the callable
            callable_node: Tree-sitter node for the callable
            parent_class_fields: List of field names from parent CLASS frame
        
        Returns:
            List of (field_name, line_number, access_type, pattern_type) tuples
            pattern_type: "explicit" for this->field, "qualified_static" for Class::field
        """
        if not callable_content or not callable_node:
            return []
        
        if not parent_class_fields:
            return []
        
        field_usages = []
        field_set = set(parent_class_fields)
        
        def determine_access_type(node) -> str:
            """Determine read/write/both for C++ field access."""
            parent = node.parent
            if not parent:
                return "read"
            
            # Check for assignment (field = ...)
            if parent.type == 'assignment_expression':
                left_node = parent.child_by_field_name('left')
                if left_node and left_node == node:
                    return "write"
            
            # Check for compound assignment (field += ..., field++, etc.)
            elif parent.type in ['update_expression', 'compound_assignment_expression']:
                return "both"
            
            return "read"
        
        def traverse_for_fields(node):
            """Recursively find field access patterns."""
            
            # Pattern 1: this->field_name
            if node.type == 'field_expression':
                obj = node.child_by_field_name('argument')
                field = node.child_by_field_name('field')
                
                if obj and field:
                    obj_text = self._get_node_text(obj)
                    field_text = self._get_node_text(field)
                    
                    # Check if object is 'this'
                    if obj_text == 'this' and field_text in field_set:
                        line_number = node.start_point[0] + 1
                        access_type = determine_access_type(node)
                        field_usages.append((field_text, line_number, access_type, "explicit"))
            
            # Pattern 2: Static field access (ClassName::field)
            elif node.type == 'qualified_identifier':
                scope = node.child_by_field_name('scope')
                name = node.child_by_field_name('name')
                
                if scope and name:
                    name_text = self._get_node_text(name)
                    
                    # Check if name is in field set
                    # Note: We can't verify ClassName matches without more context
                    # Accept as potential static field access
                    if name_text in field_set:
                        line_number = node.start_point[0] + 1
                        access_type = determine_access_type(node)
                        field_usages.append((name_text, line_number, access_type, "qualified_static"))
            
            # Recurse into children
            for child in node.children:
                traverse_for_fields(child)
        
        traverse_for_fields(callable_node)
        
        return field_usages
