"""Perl language handler implementation"""

import re
from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING
from pathlib import Path

from .base import LanguageHandler, ImportStatement
from nabu.core.frames import AstFrameBase
from nabu.core.frame_types import FrameNodeType
from nabu.parsing.raw_extraction import RawNode

if TYPE_CHECKING:
    from nabu.core.field_info import FieldInfo, ParameterInfo


class PerlHandler(LanguageHandler):
    """Perl-specific language handler"""

    def __init__(self):
        super().__init__("perl")

    # ==================== FILE DISCOVERY ====================

    def get_file_extensions(self) -> List[str]:
        """Perl file extensions"""
        return ['.pl', '.pm', '.t']

    # ==================== SEMANTIC MAPPING ====================

    def get_frame_mappings(self) -> Dict[str, FrameNodeType]:
        """Map Perl tree-sitter node types to semantic frame types"""
        return {
            'subroutine_declaration_statement': FrameNodeType.CALLABLE,
            'method_declaration_statement': FrameNodeType.CALLABLE,
            'class_statement': FrameNodeType.CLASS,
            'role_statement': FrameNodeType.CLASS,
            # Control flow enabled
            'cstyle_for_statement': FrameNodeType.FOR_LOOP,
            'for_statement': FrameNodeType.FOR_LOOP,
            'loop_statement': FrameNodeType.WHILE_LOOP,
            'try_statement': FrameNodeType.TRY_BLOCK,
            'conditional_statement': FrameNodeType.IF_BLOCK,
        }

    # ==================== NAME EXTRACTION ====================

    def extract_class_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract class/role name from Perl definition.
        
        Modern Perl (5.12+):
            class MyClass {
            role MyRole {
        
        Note: Traditional Perl uses packages for "classes", not class keyword.
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # Modern Perl: class MyClass { or role MyRole {
        for keyword in ['class', 'role']:
            if f'{keyword} ' in first_line:
                parts = first_line.split()
                try:
                    idx = parts.index(keyword)
                    if idx + 1 < len(parts):
                        name = parts[idx + 1]
                        return self._clean_name(name, ['{', ':', ';'])
                except ValueError:
                    pass

        return None

    def extract_callable_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract subroutine name from Perl definition.
        
        Examples:
            sub new {
            sub process {
            sub _private_method {
            sub AUTOLOAD {
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # Perl: sub name {
        # Pattern: sub <name> [prototype] {
        if 'sub ' in first_line:
            # Match: sub <word>
            match = re.search(r'\bsub\s+([a-zA-Z_][a-zA-Z0-9_]*)', first_line)
            if match:
                sub_name = match.group(1)
                return sub_name

        return None

    def extract_package_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """
        Extract package name from Perl package statement.
        
        Examples:
            package Core::BaseProcessor;
            package Utils::Logger;
        """
        if not content or not content.strip():
            return None

        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        if not lines:
            return None

        first_line = lines[0]

        # Perl: package Core::BaseProcessor;
        if first_line.startswith('package '):
            package_name = first_line[8:].strip().rstrip(';')
            # Return full package name (Perl packages can be nested with ::)
            return package_name

        return None

    # ==================== QUALIFIED NAME GENERATION ====================

    def build_qualified_name(self, frame: AstFrameBase, parent_chain: List[AstFrameBase]) -> str:
        """
        Build fully qualified name with Perl package path.
        
        Format: Core::BaseProcessor::method
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
        """Perl uses :: notation"""
        return "::"

    # ==================== PACKAGE HIERARCHY ====================

    def extract_package_hierarchy_from_path(self, file_path: str, codebase_root: str) -> List[str]:
        """
        Extract Perl package path from file system path.
        
        Perl packages typically match directory structure:
        - lib/Core/BaseProcessor.pm corresponds to package Core::BaseProcessor
        
        Strategy:
        1. Look for 'lib' or 'perl5' as anchor points
        2. If not found, use directory structure relative to language-specific directories
        
        Example:
            /path/to/project/lib/Core/BaseProcessor.pm -> ['Core']
            /path/to/test/perl/Core/BaseProcessor.pm -> ['Core']
        """
        path = Path(file_path)
        parts = path.parts

        package_parts = []
        found_anchor = False

        for i, part in enumerate(parts[:-1]):  # Exclude file name
            # Check for standard Perl directory anchors
            if part in ['lib', 'perl5']:
                found_anchor = True
                continue
            
            # If we found anchor, collect everything after
            if found_anchor:
                package_parts.append(part)
        
        # Fallback: if no anchor found, look for 'perl' directory
        # and use structure after it (for test files)
        if not package_parts:
            for i, part in enumerate(parts[:-1]):
                if part == 'perl':
                    # Collect parts after 'perl' directory
                    package_parts = list(parts[i+1:-1])
                    break
        
        return package_parts

    def extract_package_from_content(self, file_content: str) -> Optional[str]:
        """
        Extract package from Perl file content.
        
        Perl files have package declaration at top (usually).
        Returns full package path with :: separator.
        """
        lines = file_content.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            if line.startswith('package '):
                package_name = line[8:].strip().rstrip(';')
                return package_name
        
        return None

    # ==================== IMPORT RESOLUTION ====================

    def extract_imports(self, file_content: str) -> List[ImportStatement]:
        """
        Extract Perl use/require statements.
        
        Handles:
            use Module;
            use Module qw(func1 func2);
            use parent 'BaseClass';
            require Module;
        """
        imports = []

        # Pattern 1: use Module;
        # Pattern 2: use Module qw(...);
        for match in re.finditer(r'^\s*use\s+([a-zA-Z_][a-zA-Z0-9_:]*)', file_content, re.MULTILINE):
            module = match.group(1)
            # Skip pragmas (lowercase modules like strict, warnings)
            if not module[0].islower() or module in ['parent', 'base']:
                imports.append(ImportStatement(import_path=module))

        # Pattern 3: require Module;
        for match in re.finditer(r'^\s*require\s+([a-zA-Z_][a-zA-Z0-9_:]*)', file_content, re.MULTILINE):
            module = match.group(1)
            imports.append(ImportStatement(import_path=module))

        return imports

    def resolve_import(self, import_path: str, current_package: str, language_frame: AstFrameBase) -> Optional[str]:
        """
        Resolve Perl use/require to qualified name.
        
        Perl modules use :: separator and are typically fully qualified.
        """
        return import_path

    # ==================== INHERITANCE RESOLUTION ====================

    def extract_base_classes(self, class_content: str, ts_node=None) -> List[str]:
        """
        Extract base class names from Perl class definition.
        
        Perl inheritance via:
            use parent 'BaseClass';
            use parent qw(Base1 Base2);
            use base 'BaseClass';
            our @ISA = ('BaseClass');
        
        Args:
            class_content: Class source code content
            ts_node: Optional tree-sitter node for accurate extraction
        """
        # Method 1: Tree-sitter extraction (if ts_node provided)
        # Note: Perl tree-sitter parser has limited OO support
        # Fallback to string parsing for now
        if ts_node is not None:
            # TODO: Implement when tree-sitter-perl improves OO parsing
            pass
        
        # Method 2: String parsing (existing implementation)
        if not class_content or not class_content.strip():
            return []

        base_classes = []

        # Pattern 1: use parent 'BaseClass';
        match = re.search(r"use\s+parent\s+['\"]([^'\"]+)['\"]", class_content)
        if match:
            base_classes.append(match.group(1))

        # Pattern 2: use parent qw(Base1 Base2);
        match = re.search(r"use\s+parent\s+qw\(([^)]+)\)", class_content)
        if match:
            bases = match.group(1).split()
            base_classes.extend(bases)

        # Pattern 3: use base 'BaseClass';
        match = re.search(r"use\s+base\s+['\"]([^'\"]+)['\"]", class_content)
        if match:
            base_classes.append(match.group(1))

        # Pattern 4: use base qw(Base1 Base2);
        match = re.search(r"use\s+base\s+qw\(([^)]+)\)", class_content)
        if match:
            bases = match.group(1).split()
            base_classes.extend(bases)

        # Pattern 5: @ISA = ('BaseClass');
        match = re.search(r"@ISA\s*=\s*\(['\"]([^'\"]+)['\"]", class_content)
        if match:
            base_classes.append(match.group(1))

        return list(set(base_classes))  # Remove duplicates  # Remove duplicates

    # ==================== FRAME FIELDS ====================
    # ==================== HELPER METHODS ====================

    def _extract_perl_params_from_shift(self, sub_content: str) -> List[str]:
        """
        Extract parameter names from Perl my ($self, $x, $y) = @_; pattern.
        
        Returns list of parameter names without $ sigil.
        """
        params = []
        
        # Pattern: my ($var1, $var2, ...) = @_;
        match = re.search(r'my\s*\(\s*\$(\w+)(?:\s*,\s*\$(\w+))*\s*\)\s*=\s*@_', sub_content)
        if match:
            # Extract all captured groups
            for group in match.groups():
                if group:
                    params.append(group)
        
        # Also look for: my $var = shift; pattern (common for $self)
        shift_matches = re.findall(r'my\s+\$(\w+)\s*=\s*shift', sub_content)
        params.extend(shift_matches)
        
        return params

    # ==================== FIELD/PARAMETER EXTRACTION ====================

    def extract_instance_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract instance fields from Perl class (blessed hash).
        
        Patterns:
            $self->{field_name} = value;
            sub field_name { ... $self->{field_name} ... }  (accessor methods)
            field_name => undef,  (in hash initialization)
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        if not class_content:
            return fields
        
        seen_fields = set()
        lines = class_content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Pattern 1: $self->{field_name} = ...
            self_field_matches = re.findall(r'\$self\s*->\s*\{\s*["\']?(\w+)["\']?\s*\}', line)
            for field_name in self_field_matches:
                if field_name not in seen_fields:
                    seen_fields.add(field_name)
                    fields.append(FieldInfo(
                        name=field_name,
                        declared_type=None,  # Perl is dynamically typed
                        line=i,
                        confidence=0.7,  # Heuristic-based
                        is_static=False
                    ))
            
            # Pattern 1b: Accessor method definitions (common Perl pattern)
            # sub field_name { my $self = shift; $self->{field_name} = shift if @_; ... }
            accessor_match = re.match(r'^\s*sub\s+(\w+)\s*\{.*\$self\s*->\s*\{["\']?\1["\']?\}', line)
            if accessor_match:
                field_name = accessor_match.group(1)
                if field_name not in seen_fields:
                    seen_fields.add(field_name)
                    fields.append(FieldInfo(
                        name=field_name,
                        declared_type=None,
                        line=i,
                        confidence=0.8,  # Higher confidence from accessor pattern
                        is_static=False
                    ))
            
            # Pattern 2: field_name => value, (in hash literal, likely in new())
            # Only if we're in what looks like object initialization
            if 'bless' in class_content or 'new' in class_content:
                hash_field_matches = re.findall(r'^\s*["\']?(\w+)["\']?\s*=>', line)
                for field_name in hash_field_matches:
                    if field_name not in seen_fields and field_name not in ('self', 'class'):
                        seen_fields.add(field_name)
                        fields.append(FieldInfo(
                            name=field_name,
                            declared_type=None,
                            line=i,
                            confidence=0.6,  # Lower confidence for hash keys
                            is_static=False
                        ))

        return fields

    def extract_static_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """
        Extract static/package variables from Perl class.
        
        Patterns:
            our $COUNT = 0;
            my $INSTANCE;  (file-scoped)
        """
        from nabu.core.field_info import FieldInfo
        
        fields = []
        if not class_content:
            return fields
        
        lines = class_content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Pattern: our $VAR = ...;
            our_match = re.match(r'\s*our\s+\$(\w+)\s*(?:=\s*([^;]+))?\s*;', line)
            if our_match:
                var_name = our_match.group(1)
                fields.append(FieldInfo(
                    name=var_name,
                    declared_type=None,  # Perl is dynamically typed
                    line=i,
                    confidence=0.8,  # 'our' explicitly declares package variable
                    is_static=True
                ))
            
            # Pattern: my $VAR = ...; (at package level, not in sub)
            # This is trickier - we'd need to check indentation
            # For now, only capture 'our' variables for higher confidence

        return fields

    def extract_parameters(self, callable_content: str, ts_node=None) -> List['ParameterInfo']:
        """
        Extract parameters from Perl subroutine.
        
        Patterns:
            my ($self, $param1, $param2) = @_;
            my $self = shift; my $x = shift;
        """
        from nabu.core.field_info import ParameterInfo
        
        params = []
        if not callable_content:
            return params
        
        # Extract first few lines where parameters are typically unpacked
        lines = callable_content.split('\n')[:10]  # Check first 10 lines
        content_slice = '\n'.join(lines)
        
        # Pattern 1: my ($var1, $var2, ...) = @_;
        list_match = re.search(
            r'my\s*\(\s*\$(\w+)(?:\s*,\s*\$(\w+))*\s*\)\s*=\s*@_',
            content_slice
        )
        
        if list_match:
            # Build list from regex groups
            param_names = [list_match.group(1)]  # First param
            # Find all remaining params
            remaining = re.findall(r',\s*\$(\w+)', list_match.group(0))
            param_names.extend(remaining)
            
            for pos, name in enumerate(param_names):
                # Skip 'self' and 'class' from parameter list
                if name in ('self', 'class'):
                    continue
                
                params.append(ParameterInfo(
                    name=name,
                    declared_type=None,  # Perl is dynamically typed
                    default_value=None,
                    position=pos
                ))
        
        else:
            # Pattern 2: my $var = shift; (sequential shifts)
            shift_matches = re.findall(r'my\s+\$(\w+)\s*=\s*shift', content_slice)
            
            for pos, name in enumerate(shift_matches):
                # Skip 'self' and 'class'
                if name in ('self', 'class'):
                    continue
                
                params.append(ParameterInfo(
                    name=name,
                    declared_type=None,
                    default_value=None,
                    position=pos
                ))

        return params

    def extract_return_type(self, callable_content: str) -> Optional[str]:
        """
        Extract return type from Perl subroutine.
        
        Perl doesn't have static return types, but we can try to infer from:
        - POD documentation: =head2 method() -> ReturnType
        - Comments: # Returns: SomeType
        
        Returns None for most cases (dynamically typed).
        """
        if not callable_content:
            return None
        
        # Look for POD documentation patterns
        # Pattern: =head2 method_name() -> ReturnType
        pod_match = re.search(r'=head[123]\s+\w+\([^)]*\)\s*->\s*(\w+)', callable_content)
        if pod_match:
            return pod_match.group(1)
        
        # Look for comment-based type hints
        # Pattern: # Returns: TypeName
        # Pattern: # @return TypeName
        comment_match = re.search(r'#\s*(?:Returns?:|@return)\s*(\w+)', callable_content)
        if comment_match:
            return comment_match.group(1)

        # Perl is dynamically typed - no static return type
        return None

    # ==================== SPECIAL CASES ====================

    def is_constructor(self, callable_name: str, parent_class_name: str) -> bool:
        """
        Perl constructors are conventionally named 'new'.
        
        However, any sub that blesses can be a constructor.
        For simplicity, we check for 'new' name.
        """
        return callable_name == 'new'

    def is_destructor(self, callable_name: str) -> bool:
        """Perl destructors are named DESTROY"""
        return callable_name == 'DESTROY'

    def normalize_callable_name(self, name: str, parent_class: Optional[str]) -> str:
        """
        Perl name normalization.
        
        No special mangling in Perl - names are as declared.
        Private conventions (leading underscore) are just conventions.
        """
        return name

    def extract_call_sites(
        self, 
        callable_content: str,
        callable_node: Any
    ) -> List[Tuple[str, int]]:
        """
        Extract function/method call sites from Perl callable.
        
        Handles:
        - Subroutine calls: func(), &func
        - Method calls: $obj->method()
        - Package calls: Package::subroutine()
        - Ambiguous function calls: print "hello", func arg1, arg2
        """
        if not callable_content or not callable_node:
            return []
        
        call_sites = []
        
        def extract_function_name(func_call_node) -> Optional[str]:
            """Extract function name from function_call_expression node."""
            function_node = func_call_node.child_by_field_name('function')
            if not function_node:
                return None
            
            # Handle different function node types
            if function_node.type == 'amper_sub':
                # &subroutine call - extract the subroutine name
                # amper_sub typically contains the & prefix and name
                text = function_node.text.decode('utf-8')
                # Remove & prefix if present
                return text.lstrip('&')
            elif function_node.type in ['function', '_bareword', 'identifier']:
                # Simple function call
                return function_node.text.decode('utf-8')
            elif function_node.type == '_unambiguous_function':
                # Unambiguous function - extract text
                return function_node.text.decode('utf-8')
            else:
                # Try to get text directly
                try:
                    return function_node.text.decode('utf-8')
                except:
                    return None
        
        def extract_method_name(method_call_node) -> Optional[str]:
            """Extract method name from method_call_expression node."""
            method_node = method_call_node.child_by_field_name('method')
            if not method_node:
                return None
            
            method_name = method_node.text.decode('utf-8')
            
            # Check for invocant (object or class)
            invocant_node = method_call_node.child_by_field_name('invocant')
            if invocant_node:
                # Build qualified name with invocant
                invocant_text = invocant_node.text.decode('utf-8')
                # Handle both $obj->method and Package->method
                return f"{invocant_text}.{method_name}"
            
            # Simple method call without qualifier
            return method_name
        
        def extract_ambiguous_function_name(ambig_call_node) -> Optional[str]:
            """Extract function name from ambiguous_function_call_expression node."""
            function_node = ambig_call_node.child_by_field_name('function')
            if not function_node:
                return None
            
            # Similar to function_call_expression
            if function_node.type in ['function', '_bareword', 'identifier']:
                return function_node.text.decode('utf-8')
            else:
                try:
                    return function_node.text.decode('utf-8')
                except:
                    return None
        
        def traverse_for_calls(node):
            """Recursively find all call expressions."""
            if node.type == 'function_call_expression':
                callee_name = extract_function_name(node)
                if callee_name:
                    line_number = node.start_point[0] + 1
                    call_sites.append((callee_name, line_number))
            
            elif node.type == 'method_call_expression':
                callee_name = extract_method_name(node)
                if callee_name:
                    line_number = node.start_point[0] + 1
                    call_sites.append((callee_name, line_number))
            
            elif node.type == 'ambiguous_function_call_expression':
                callee_name = extract_ambiguous_function_name(node)
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
        Extract field usage sites from Perl callable.
        
        Patterns detected:
        - $self->{field_name} (hash key access on $self)
        
        Note: Dynamic field access ($self->{$variable}) is NOT detected
        as we cannot resolve variable values statically.
        
        Args:
            callable_content: Source code of the callable
            callable_node: Tree-sitter node for the callable (may be None)
            parent_class_fields: List of field names from parent CLASS frame
        
        Returns:
            List of (field_name, line_number, access_type, pattern_type) tuples
            pattern_type: "regex_based" for $self->{field}
        """
        if not callable_content:
            return []
        
        if not parent_class_fields:
            return []
        
        field_usages = []
        field_set = set(parent_class_fields)
        
        # Perl uses subscript expressions: $self->{field_name}
        # Regex approach (tree-sitter for Perl is less reliable)
        
        import re
        lines = callable_content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Pattern: $self->{field_name} or $self->{'field_name'} or $self->{"field_name"}
            matches = re.findall(r'\$self\s*->\s*\{\s*["\']?(\w+)["\']?\s*\}', line)
            
            for field_name in matches:
                if field_name in field_set:
                    # Determine access type
                    access_type = "read"
                    
                    # Check if assignment (heuristic: = follows the expression)
                    # Pattern: $self->{field} = ...
                    if re.search(rf'\$self\s*->\s*\{{\s*["\']?{field_name}["\']?\s*\}}\s*=', line):
                        access_type = "write"
                    
                    field_usages.append((field_name, i, access_type, "regex_based"))
        
        return field_usages
