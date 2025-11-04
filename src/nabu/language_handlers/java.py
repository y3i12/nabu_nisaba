"""Java language handler implementation"""

import re
from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING
from pathlib import Path

from .base import LanguageHandler, ImportStatement
from nabu.core.frames import AstFrameBase
from nabu.core.frame_types import FrameNodeType
from nabu.parsing.raw_extraction import RawNode

if TYPE_CHECKING:
    from nabu.core.field_info import FieldInfo, ParameterInfo


class JavaHandler(LanguageHandler):
    """Java-specific language handler"""

    def __init__(self):
        super().__init__("java")

    # ==================== FILE DISCOVERY ====================

    def get_file_extensions(self) -> List[str]:
        """Java file extensions"""
        return ['.java']

    # ==================== SEMANTIC MAPPING ====================

    def get_frame_mappings(self) -> Dict[str, FrameNodeType]:
        """Map Java tree-sitter node types to semantic frame types"""
        return {
            'method_declaration': FrameNodeType.CALLABLE,
            'constructor_declaration': FrameNodeType.CALLABLE,
            'class_declaration': FrameNodeType.CLASS,
            'interface_declaration': FrameNodeType.CLASS,  # Interface mapped to CLASS
            'enum_declaration': FrameNodeType.CLASS,       # Enum mapped to CLASS
            # Control flow enabled
            'if_statement': FrameNodeType.IF_BLOCK,
            'else_clause': FrameNodeType.ELSE_BLOCK,
            'for_statement': FrameNodeType.FOR_LOOP,
            'while_statement': FrameNodeType.WHILE_LOOP,
            'switch_expression': FrameNodeType.SWITCH_BLOCK,
            'try_statement': FrameNodeType.TRY_BLOCK,
            'catch_clause': FrameNodeType.EXCEPT_BLOCK,
            'finally_clause': FrameNodeType.FINALLY_BLOCK,
        }

    # ==================== NAME EXTRACTION ====================

    def extract_class_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract class/interface/enum name from Java definition.
        
        Examples:
            public class MyClass {
            class MyClass extends BaseClass {
            public interface MyInterface {
            public enum MyEnum {
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        # Find first non-annotation line (same as extract_callable_name does)
        first_line = None
        for line in lines:
            if not line.startswith('@'):
                first_line = line
                break
        
        # Handle case where all lines are annotations
        if not first_line:
            return None

        # Java: public/private/protected class ClassName
        # Also handles: interface, enum
        for keyword in ['class', 'interface', 'enum']:
            if f' {keyword} ' in first_line or first_line.startswith(f'{keyword} '):
                parts = first_line.split()
                try:
                    class_idx = parts.index(keyword)
                    if class_idx + 1 < len(parts):
                        name = parts[class_idx + 1]
                        return self._clean_name(name, ['<', '{', 'extends', 'implements'])
                except ValueError:
                    pass

        return None

    def extract_callable_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract method/constructor name from Java definition.
        
        Examples:
            public void methodName(args) {
            public ClassName(args) {           // Constructor (no return type)
            public static int method(args) {
            @Override public String method() {
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        # Find first non-annotation line
        first_line = None
        for line in lines:
            if not line.startswith('@'):
                first_line = line
                break

        if not first_line:
            return None

        # Java method/constructor: [modifiers] [returnType] methodName(args) {
        # Constructor: [modifiers] ClassName(args) {  (no return type)
        if '(' in first_line:
            # Extract everything before the first (
            before_paren = first_line.split('(')[0].strip()
            parts = before_paren.split()

            if len(parts) >= 1:
                # The last part before ( is the method/constructor name
                potential_name = parts[-1]
                
                # Handle generic methods: <T> void method -> method is at -1
                # Remove generic type parameters if present
                potential_name = re.sub(r'<[^>]+>', '', potential_name).strip()
                
                if self._is_valid_identifier(potential_name):
                    return potential_name

        return None

    def extract_package_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract package name from Java package declaration.
        
        Examples:
            package com.example.myapp;
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # Java: package com.example.myapp;
        if first_line.startswith('package '):
            package_name = first_line[8:].strip().rstrip(';')
            # Return the last component for the package frame name
            # Full package hierarchy will be built by extract_package_hierarchy_from_path
            return package_name.split('.')[-1]

        return None

    # ==================== QUALIFIED NAME GENERATION ====================

    def build_qualified_name(self, frame: AstFrameBase, parent_chain: List[AstFrameBase]) -> str:
        """
        Build fully qualified name with Java package path.
        
        Format: com.example.package.Class.method
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
        """Java uses dot notation"""
        return "."

    # ==================== PACKAGE HIERARCHY ====================

    def extract_package_hierarchy_from_path(self, file_path: str, codebase_root: str) -> List[str]:
        """
        Extract Java package path from file system path.
        
        Java packages must match directory structure:
        - com/example/myapp/MyClass.java corresponds to package com.example.myapp
        
        However, we prefer to extract from package declaration in file content.
        This method serves as fallback.
        
        Example:
            /path/to/project/src/com/example/myapp/MyClass.java
            -> ['com', 'example', 'myapp']
        """
        path = Path(file_path)
        parts = path.parts

        package_parts = []
        found_src = False

        for part in parts[:-1]:  # Exclude file name
            if part in ['src', 'main', 'java']:
                found_src = True
                continue
            if found_src:
                package_parts.append(part)

        return package_parts

    def extract_package_from_content(self, file_content: str) -> Optional[str]:
        """
        Extract package from Java file content.
        
        Java files must have package declaration at top (except default package).
        Returns full package path as dotted string.
        """
        lines = file_content.split('\n')
        for line in lines[:20]:  # Check first 20 lines (before class)
            line = line.strip()
            if line.startswith('package '):
                package_name = line[8:].strip().rstrip(';')
                return package_name
        
        return None

    # ==================== IMPORT RESOLUTION ====================

    def extract_imports(self, file_content: str) -> List[ImportStatement]:
        """
        Extract Java import statements.
        
        Handles:
            import com.example.MyClass;
            import com.example.*;
            import static com.example.MyClass.staticMethod;
        """
        imports = []

        # Pattern: import [static] package.Class;
        for match in re.finditer(r'^\s*import\s+(?:static\s+)?([a-zA-Z_][a-zA-Z0-9_.$*]*)\s*;',
                                  file_content, re.MULTILINE):
            import_path = match.group(1)
            
            # Check for wildcard import
            if import_path.endswith('.*'):
                imports.append(ImportStatement(
                    import_path=import_path[:-2],  # Remove .*
                    is_wildcard=True
                ))
            else:
                imports.append(ImportStatement(import_path=import_path))

        return imports

    def resolve_import(self, import_path: str, current_package: str, language_frame: AstFrameBase) -> Optional[str]:
        """
        Resolve Java import to qualified name.
        
        Java imports are fully qualified, so resolution is straightforward.
        """
        return import_path

    # ==================== INHERITANCE RESOLUTION ====================

    def extract_base_classes(self, class_content: str, ts_node=None) -> List[str]:
        """
        Extract base class names from Java class definition.
        
        Examples:
            public class MyClass extends BaseClass {
            public class MyClass implements Interface1, Interface2 {
            public class MyClass extends Base implements Interface1 {
        
        Args:
            class_content: Class source code content
            ts_node: Optional tree-sitter node for accurate extraction
        """
        # Method 1: Use tree-sitter node if available (most accurate)
        if ts_node is not None:
            # Java: class_declaration node
            # Look for superclass and super_interfaces
            base_classes = []
            for child in ts_node.children:
                if child.type == 'superclass':
                    # extends Foo
                    for sc_child in child.children:
                        if sc_child.type in ['type_identifier', 'generic_type']:
                            base_text = sc_child.text.decode('utf-8') if isinstance(sc_child.text, bytes) else str(sc_child.text)
                            # Remove generic parameters
                            base_text = re.sub(r'<[^>]+>', '', base_text).strip()
                            if base_text:
                                base_classes.append(base_text)
                elif child.type == 'super_interfaces':
                    # implements Foo, Bar
                    for si_child in child.children:
                        if si_child.type in ['type_identifier', 'generic_type']:
                            iface_text = si_child.text.decode('utf-8') if isinstance(si_child.text, bytes) else str(si_child.text)
                            # Remove generic parameters
                            iface_text = re.sub(r'<[^>]+>', '', iface_text).strip()
                            if iface_text:
                                base_classes.append(iface_text)
            if base_classes:
                return base_classes
        
        # Method 2: Fallback to string parsing (existing implementation)
        if not class_content or not class_content.strip():
            return []

        lines = [line.strip() for line in class_content.strip().split('\n') if line.strip()]
        if not lines:
            return []

        first_line = lines[0]
        base_classes = []

        # Extract extends clause
        if ' extends ' in first_line:
            match = re.search(r' extends\s+([a-zA-Z_][a-zA-Z0-9_.<>]*)', first_line)
            if match:
                base_class = match.group(1).strip()
                # Remove generic parameters
                base_class = re.sub(r'<[^>]+>', '', base_class).strip()
                if base_class:
                    base_classes.append(base_class)

        # Extract implements clause
        if ' implements ' in first_line:
            match = re.search(r' implements\s+([^{]+)', first_line)
            if match:
                interfaces_str = match.group(1).strip()
                # Split by comma
                interfaces = [iface.strip() for iface in interfaces_str.split(',')]
                for iface in interfaces:
                    # Remove generic parameters
                    iface = re.sub(r'<[^>]+>', '', iface).strip()
                    if iface and self._is_valid_identifier(iface):
                        base_classes.append(iface)

        return base_classes


    # ==================== FRAME FIELDS ====================
    # ==================== HELPER METHODS ====================

    def _split_java_parameters(self, params_str: str) -> List[str]:
        """
        Split Java parameter string by commas, respecting generics.
        
        Example: "T value, Comparator<? super T> comp, List<String> items"
        """
        param_parts = []
        current = []
        depth = 0
        
        for char in params_str + ',':
            if char == '<':
                depth += 1
            elif char == '>':
                depth -= 1
            
            if char == ',' and depth == 0:
                param_parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        
        return [p for p in param_parts if p]

    # ==================== FIELD/PARAMETER EXTRACTION ====================

    def extract_instance_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract instance fields from Java class.
        
        Patterns:
            private int count;
            private String name = "default";
            protected List<String> items = new ArrayList<>();
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        if not class_content:
            return fields
        
        lines = class_content.split('\n')
        
        # Track brace depth instead of boolean flag
        brace_depth = 0
        class_body_started = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Track braces more accurately
            # Count opening and closing braces
            for char in line:
                if char == '{':
                    brace_depth += 1
                    if not class_body_started:
                        class_body_started = True
                elif char == '}':
                    brace_depth -= 1
            
            # Only process field declarations at class level (depth = 1)
            # Depth 0: Outside class
            # Depth 1: Inside class body (fields live here)
            # Depth 2+: Inside methods, inner classes, initializer blocks
            
            # Skip if not at class body level
            if brace_depth != 1:
                continue
            
            # Skip if line contains method signature pattern
            # More robust pattern that matches Java methods
            if re.search(r'\w+\s*\([^)]*\)\s*(?:throws\s+[\w\s,]+)?\s*\{', stripped):
                continue
            
            # Also skip lines with common non-field patterns
            # Skip if line has lambda or anonymous class
            if '->' in stripped or re.search(r'new\s+\w+\s*\(', stripped):
                continue
            
            # Match: [access] [final] Type name [= value];
            # NOT static (that's for static_fields)
            match = re.match(
                r'\s*(private|protected|public)?'  # Optional access modifier
                r'\s+(?!static\s+)'                # Negative lookahead for static
                r'(final\s+)?'                     # Optional final
                r'([\w<>,\s\[\]]+)'               # Type (handles generics)
                r'\s+(\w+)'                        # Name
                r'(?:\s*=\s*([^;]+))?'            # Optional = value
                r'\s*;',                           # Must end with semicolon
                stripped
            )
            
            if match:
                access, final, field_type, field_name, value = match.groups()
                
                # Additional validation - skip if type looks like method call
                # e.g., "SomeMethod.call()" shouldn't match
                if '(' in field_type:
                    continue
                
                # Clean up type (remove extra whitespace)
                field_type = re.sub(r'\s+', ' ', field_type).strip()
                
                fields.append(FieldInfo(
                    name=field_name,
                    declared_type=field_type,
                    line=i,
                    confidence=0.9,  # Java requires types, so high confidence
                    is_static=False
                ))

        return fields

    def extract_static_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract static/class fields from Java class.
        
        Patterns:
            public static final int MAX_SIZE = 100;
            private static Logger logger = ...;
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        if not class_content:
            return fields
        
        lines = class_content.split('\n')
        
        # Track brace depth instead of boolean flag
        brace_depth = 0
        class_body_started = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Track braces more accurately
            # Count opening and closing braces
            for char in line:
                if char == '{':
                    brace_depth += 1
                    if not class_body_started:
                        class_body_started = True
                elif char == '}':
                    brace_depth -= 1
            
            # Only process field declarations at class level (depth = 1)
            # Depth 0: Outside class
            # Depth 1: Inside class body (fields live here)
            # Depth 2+: Inside methods, inner classes, initializer blocks
            
            # Skip if not at class body level
            if brace_depth != 1:
                continue
            
            # Skip if line contains method signature pattern
            # More robust pattern that matches Java methods
            if re.search(r'\w+\s*\([^)]*\)\s*(?:throws\s+[\w\s,]+)?\s*\{', stripped):
                continue
            
            # Also skip lines with common non-field patterns
            # Skip if line has lambda or anonymous class
            if '->' in stripped or re.search(r'new\s+\w+\s*\(', stripped):
                continue
            
            # Match: [access] static [final] Type name = value;
            match = re.match(
                r'\s*(private|protected|public)?'  # Optional access modifier
                r'\s+static\s+'                    # MUST have static
                r'(final\s+)?'                     # Optional final
                r'([\w<>,\s\[\]]+)'               # Type
                r'\s+(\w+)'                        # Name
                r'(?:\s*=\s*([^;]+))?'            # Optional = value
                r'\s*;',                           # Must end with semicolon
                stripped
            )
            
            if match:
                access, final, field_type, field_name, value = match.groups()
                
                # Additional validation - skip if type looks like method call
                if '(' in field_type:
                    continue
                
                field_type = re.sub(r'\s+', ' ', field_type).strip()
                
                fields.append(FieldInfo(
                    name=field_name,
                    declared_type=field_type,
                    line=i,
                    confidence=0.9,
                    is_static=True
                ))

        return fields

    def extract_parameters(self, callable_content: str, ts_node=None) -> List['ParameterInfo']:
        """
        Extract parameters from Java method signature.
        
        Examples:
            public void foo(int x, String name, boolean flag) { }
            private <T> List<T> bar(T value, Comparator<? super T> comp) { }
        """
        from nabu.core.field_info import ParameterInfo
        
        params = []
        if not callable_content:
            return params
        
        # Extract signature: between ( and )
        # Java methods can also be multi-line
        signature_match = re.search(r'\w+\s*\((.*?)\)\s*(?:throws\s+[\w,\s]+)?\s*\{', 
                                     callable_content, re.DOTALL)
        if not signature_match:
            return params
        
        params_str = signature_match.group(1)
        
        # Clean whitespace
        params_str = re.sub(r'\s+', ' ', params_str).strip()
        
        if not params_str:
            return params
        
        # Split by comma (respecting generics <...>)
        param_parts = self._split_java_parameters(params_str)
        
        for pos, param in enumerate(param_parts):
            param = param.strip()
            if not param:
                continue
            
            # Parse: [final] Type name
            # Note: Java doesn't have default values in method signatures
            match = re.match(r'(?:final\s+)?([\w<>,\s\[\]?]+)\s+(\w+)', param)
            if match:
                param_type, param_name = match.groups()
                param_type = re.sub(r'\s+', ' ', param_type).strip()
                
                params.append(ParameterInfo(
                    name=param_name,
                    declared_type=param_type,
                    default_value=None,  # Java doesn't have defaults
                    position=pos
                ))

        return params

    def extract_return_type(self, callable_content: str) -> Optional[str]:
        """
        Extract return type from Java method.
        
        Examples:
            public void foo() { }  → "void"
            private List<String> bar() { }  → "List<String>"
            public static <T> T get() { }  → "T"
        """
        if not callable_content:
            return None
        
        # Skip annotations and find signature line (same as extract_callable_name)
        lines = [line.strip() for line in callable_content.strip().split('\n') if line.strip()]
        if not lines:
            return None
        
        # Find first non-annotation line
        signature_line = None
        for line in lines:
            if not line.startswith('@'):
                signature_line = line
                break
        
        if not signature_line:
            return None
        
        # If multi-line signature, concatenate until we find '('
        if '(' not in signature_line:
            # Signature spans multiple lines - collect until we find '('
            for i, line in enumerate(lines):
                if not line.startswith('@'):
                    signature_parts = [line]
                    for next_line in lines[i+1:]:
                        signature_parts.append(next_line.strip())
                        if '(' in next_line:
                            break
                    signature_line = ' '.join(signature_parts)
                    break
        
        # Detect constructors (no return type expected)
        # Extract method name first
        if '(' in signature_line:
            before_paren = signature_line.split('(')[0].strip()
            parts = before_paren.split()
            if len(parts) >= 1:
                method_name = parts[-1]
                # If method name starts with uppercase, likely a constructor
                # This is heuristic but works for most Java conventions
                if method_name and method_name[0].isupper():
                    # Could be constructor - check if no return type keywords before it
                    modifiers = parts[:-1]
                    # If only access modifiers (no type), it's a constructor
                    if all(m in ['public', 'private', 'protected'] for m in modifiers):
                        return None  # Constructors have no return type
        
        # Improved regex to handle more modifiers
        match = re.search(
            r'(?:public|private|protected)?'  # Optional access modifier
            r'(?:\s+static)?'                  # Optional static
            r'(?:\s+final)?'                   # Optional final
            r'(?:\s+synchronized)?'            # Optional synchronized
            r'(?:\s+native)?'                  # Optional native
            r'(?:\s+abstract)?'                # Optional abstract
            r'\s+(?:<[\w\s,?]+>\s+)?'         # Optional generic declaration <T>
            r'([\w<>,\s\[\]?]+)'              # Return type (capture group)
            r'\s+\w+\s*\(',                    # Method name + (
            signature_line
        )
        
        if match:
            return_type = match.group(1).strip()
            return_type = re.sub(r'\s+', ' ', return_type)
            return return_type

        return None

    # ==================== SPECIAL CASES ====================

    def is_constructor(self, callable_name: str, parent_class_name: str) -> bool:
        """
        Java constructors have the same name as the class and no return type.
        This is detected during name extraction.
        """
        return callable_name == parent_class_name

    def is_destructor(self, callable_name: str) -> bool:
        """Java doesn't have destructors"""
        return False

    def normalize_callable_name(self, name: str, parent_class: Optional[str]) -> str:
        """
        Java name normalization.
        
        No special mangling in Java - names are as declared.
        """
        return name

    def extract_call_sites(
        self, 
        callable_content: str,
        callable_node: Any
    ) -> List[Tuple[str, int]]:
        """
        Extract function/method call sites from Java callable.
        
        Handles:
        - Method calls: method()
        - Instance method calls: obj.method()
        - Static calls: ClassName.staticMethod()
        - Constructor calls: new ClassName()
        - Chained calls: obj.method1().method2()
        - Generic calls: list.<String>add(item)
        """
        if not callable_content or not callable_node:
            return []
        
        call_sites = []
        
        def extract_method_name(method_inv_node) -> Optional[str]:
            """Extract the name being called from a method_invocation node."""
            name_node = method_inv_node.child_by_field_name('name')
            if not name_node:
                return None
            
            method_name = name_node.text.decode('utf-8')
            
            # Check if this is a qualified call (obj.method or Class.method)
            object_node = method_inv_node.child_by_field_name('object')
            if object_node:
                # Build qualified name by extracting object/class name
                parts = []
                
                # Handle chained method calls recursively
                # e.g., obj.method1().method2() - object_node is another method_invocation
                if object_node.type == 'method_invocation':
                    # For chained calls, we just get the immediate object
                    # The resolver will handle finding the ultimate target
                    # Just extract the simple name of the chained call
                    chained_name = extract_method_name(object_node)
                    if chained_name:
                        parts.append(chained_name)
                elif object_node.type == 'identifier':
                    # Simple qualified call: obj.method or ClassName.method
                    parts.append(object_node.text.decode('utf-8'))
                elif object_node.type == 'field_access':
                    # Nested field access: this.field.method or obj.field.method
                    # Extract the full field access chain
                    field_parts = []
                    current = object_node
                    while current and current.type == 'field_access':
                        field = current.child_by_field_name('field')
                        if field:
                            field_parts.insert(0, field.text.decode('utf-8'))
                        current = current.child_by_field_name('object')
                    
                    # Add the base object
                    if current and current.type == 'identifier':
                        field_parts.insert(0, current.text.decode('utf-8'))
                    
                    if field_parts:
                        parts.append('.'.join(field_parts))
                else:
                    # Other object types - try to get text directly
                    try:
                        parts.append(object_node.text.decode('utf-8'))
                    except:
                        pass
                
                # Build the full qualified name
                if parts:
                    return '.'.join(parts) + '.' + method_name
            
            # Simple method call without qualifier
            return method_name
        
        def extract_constructor_name(obj_creation_node) -> Optional[str]:
            """Extract class name from object_creation_expression node."""
            type_node = obj_creation_node.child_by_field_name('type')
            if not type_node:
                return None
            
            # Extract the class name from the type
            # Handle simple types and generic types
            class_name = type_node.text.decode('utf-8')
            
            # For generics, we want just the base class name
            # e.g., "ArrayList<String>" -> "ArrayList"
            # But we'll keep the full name for now to help resolution
            return class_name
        
        def traverse_for_calls(node):
            """Recursively find all call expressions."""
            if node.type == 'method_invocation':
                callee_name = extract_method_name(node)
                if callee_name:
                    # Line number is 0-indexed in tree-sitter, convert to 1-indexed
                    line_number = node.start_point[0] + 1
                    call_sites.append((callee_name, line_number))
            
            elif node.type == 'object_creation_expression':
                callee_name = extract_constructor_name(node)
                if callee_name:
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
        Extract field usage sites from Java callable.
        
        Patterns detected:
        - this.fieldName (explicit this)
        - ClassName.staticField (static field access)
        
        Note: Implicit field access (field without this.) is NOT detected
        in Phase 1 due to ambiguity with local variables.
        
        Args:
            callable_content: Source code of the callable
            callable_node: Tree-sitter node for the callable
            parent_class_fields: List of field names from parent CLASS frame
        
        Returns:
            List of (field_name, line_number, access_type, pattern_type) tuples
            pattern_type: "explicit" for this.field, "uppercase_heuristic" for ClassName.field
        """
        if not callable_content or not callable_node:
            return []
        
        if not parent_class_fields:
            return []
        
        field_usages = []
        field_set = set(parent_class_fields)
        
        def determine_access_type(node) -> str:
            """Determine read/write/both for Java field access."""
            parent = node.parent
            if not parent:
                return "read"
            
            # Check for assignment (field = ...)
            if parent.type == 'assignment_expression':
                left_node = parent.child_by_field_name('left')
                if left_node and left_node == node:
                    return "write"
            
            # Check for update expression (field++, ++field)
            elif parent.type == 'update_expression':
                return "both"
            
            return "read"
        
        def traverse_for_fields(node):
            """Recursively find field access patterns."""
            
            # Pattern: this.fieldName or ClassName.staticField (field_access)
            if node.type == 'field_access':
                obj = node.child_by_field_name('object')
                field = node.child_by_field_name('field')
                
                if obj and field:
                    obj_text = obj.text.decode('utf-8')
                    field_text = field.text.decode('utf-8')
                    
                    # Pattern 1: this.field
                    if obj_text == 'this' and field_text in field_set:
                        line_number = node.start_point[0] + 1
                        access_type = determine_access_type(node)
                        field_usages.append((field_text, line_number, access_type, "explicit"))
                    
                    # Pattern 2: ClassName.staticField (static field access)
                    # Heuristic: if object looks like class name (starts with uppercase)
                    elif field_text in field_set and obj_text and obj_text[0].isupper():
                        line_number = node.start_point[0] + 1
                        access_type = determine_access_type(node)
                        field_usages.append((field_text, line_number, access_type, "uppercase_heuristic"))
            
            # Recurse into children
            for child in node.children:
                traverse_for_fields(child)
        
        traverse_for_fields(callable_node)
        
        return field_usages
