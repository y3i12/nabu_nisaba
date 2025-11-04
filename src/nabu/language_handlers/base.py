"""Base class for language-specific handlers"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, TYPE_CHECKING, Tuple, Any
from dataclasses import dataclass

from nabu.core.frames import AstFrameBase
from nabu.core.frame_types import FrameNodeType
from nabu.parsing.raw_extraction import RawNode

if TYPE_CHECKING:
    from nabu.core.field_info import FieldInfo, ParameterInfo


@dataclass
class ImportStatement:
    """Represents an import statement extracted from source code"""
    import_path: str
    alias: Optional[str] = None
    is_wildcard: bool = False
    line_number: Optional[int] = None


class LanguageHandler(ABC):
    """
    Abstract base class for language-specific operations.
    
    Each language handler implements all language-specific logic:
    - File discovery (extensions)
    - Semantic mapping (tree-sitter → frame types)
    - Name extraction (classes, callables, packages)
    - Qualified name generation
    - Package hierarchy extraction
    - Import/inheritance resolution
    """

    def __init__(self, language: str):
        self.language = language

    # ==================== FILE DISCOVERY ====================

    @abstractmethod
    def get_file_extensions(self) -> List[str]:
        """Return file extensions for this language (.py, .java, etc.)"""
        pass

    # ==================== SEMANTIC MAPPING ====================

    @abstractmethod
    def get_frame_mappings(self) -> Dict[str, FrameNodeType]:
        """Map tree-sitter node types to semantic frame types"""
        pass

    # ==================== NAME EXTRACTION ====================

    @abstractmethod
    def extract_class_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """Extract class/struct/interface name from content"""
        pass

    @abstractmethod
    def extract_callable_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """Extract function/method name from content"""
        pass

    @abstractmethod
    def extract_package_name(self, content: str, raw_node: RawNode) -> Optional[str]:
        """Extract package/namespace/module name from content"""
        pass

    # ==================== QUALIFIED NAME GENERATION ====================

    @abstractmethod
    def build_qualified_name(self, frame: AstFrameBase, parent_chain: List[AstFrameBase]) -> str:
        """Build fully qualified name using language conventions"""
        pass

    @abstractmethod
    def get_separator(self) -> str:
        """Return language-specific separator (. for Python/Java, :: for C++/Perl)"""
        pass

    # ==================== PACKAGE HIERARCHY ====================

    @abstractmethod
    def extract_package_hierarchy_from_path(self, file_path: str, codebase_root: str) -> List[str]:
        """Extract package path from file system path"""
        pass

    @abstractmethod
    def extract_package_from_content(self, file_content: str) -> Optional[str]:
        """Extract package declaration from file content (Java package, C++ namespace, etc.)"""
        pass

    # ==================== IMPORT RESOLUTION ====================

    @abstractmethod
    def extract_imports(self, file_content: str) -> List[ImportStatement]:
        """Extract import statements from file"""
        pass

    @abstractmethod
    def resolve_import(self, import_path: str, current_package: str, language_frame: AstFrameBase) -> Optional[str]:
        """Resolve import to qualified name"""
        pass

    # ==================== INHERITANCE RESOLUTION ====================

    @abstractmethod
    def extract_base_classes(self, class_content: str, ts_node=None) -> List[str]:
        """
        Extract base class names from class definition.
        
        Args:
            class_content: Class source code content
            ts_node: Optional tree-sitter node for accurate extraction
            
        Returns:
            List of base class names
        """
        pass

    # ==================== CALL RESOLUTION ====================

    @abstractmethod
    def extract_call_sites(
        self, 
        callable_content: str,
        callable_node: Any
    ) -> List[Tuple[str, int]]:
        """
        Extract function/method call sites from callable content.
        
        Args:
            callable_content: Source code of the function/method
            callable_node: Tree-sitter node for the callable
            
        Returns:
            List of (callee_name, line_number) tuples relative to file start
            
        Examples:
            Python: ['foo()', 'obj.method()'] → [('foo', 42), ('obj.method', 43)]
            C++: ['std::cout', 'myFunc()'] → [('std::cout', 10), ('myFunc', 11)]
            
        Note:
            - Should extract both function calls and method calls
            - Line numbers should be absolute (relative to file start)
            - Qualified names preferred when available (e.g., 'module.func' vs 'func')
        """
        pass

    # ==================== FRAME FIELDS ====================
    @abstractmethod
    def extract_instance_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """Extract instance fields from class definition.
        
        Args:
            class_content: Class source code
            ts_node: Optional tree-sitter node for accurate decorator detection
        """
        pass

    @abstractmethod
    def extract_static_fields(self, class_content: str, ts_node=None) -> List['FieldInfo']:
        """Extract static/class fields from class definition.
        
        Args:
            class_content: Class source code
            ts_node: Optional tree-sitter node for accurate decorator detection
        """
        pass

    @abstractmethod
    def extract_parameters(self, callable_content: str, ts_node=None) -> List['ParameterInfo']:
        """Extract function/method parameters with types."""
        pass

    @abstractmethod
    def extract_return_type(self, callable_content: str) -> Optional[str]:
        """Extract return type annotation."""
        pass

    # ==================== SPECIAL CASES ====================

    def is_constructor(self, callable_name: str, parent_class_name: str) -> bool:
        """Check if callable is a constructor"""
        return False  # Override in subclasses

    def is_destructor(self, callable_name: str) -> bool:
        """Check if callable is a destructor"""
        return False  # Override in subclasses

    def normalize_callable_name(self, name: str, parent_class: Optional[str]) -> str:
        """Normalize special callable names (constructors, operators, etc.)"""
        return name  # Override in subclasses

    # ==================== HELPER METHODS ====================

    def _clean_name(self, name: str, terminators: list) -> str:
        """Clean name by removing terminators and invalid characters."""
        if not name:
            return name

        # Remove terminators
        for term in terminators:
            if term in name:
                name = name.split(term)[0]

        # Remove common invalid characters
        name = name.strip()
        for char in [' ', '\t', '\n', '\r']:
            name = name.replace(char, '')

        return name if name and self._is_valid_identifier(name) else ""

    def _is_valid_identifier(self, name: str) -> bool:
        """Check if name is a valid identifier."""
        if not name:
            return False

        # Must start with letter or underscore
        if not (name[0].isalpha() or name[0] == '_'):
            return False

        # Rest must be alphanumeric or underscore (or language-specific chars)
        # Note: Some languages allow additional chars (e.g., $ in Java)
        return all(c.isalnum() or c in ['_', '$'] for c in name[1:])
