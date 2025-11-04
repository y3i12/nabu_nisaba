from enum import Enum


class FrameNodeType(Enum):
    # Structural frames - core hierarchy
    CODEBASE = "CODEBASE"           # Root frame (was: codebase in current)
    LANGUAGE = "LANGUAGE"           # NEW: python_root, cpp_root, java_root
    PACKAGE = "PACKAGE"             # Also cpp namespace, java package
    CLASS = "CLASS"                 # Also struct, interface, union, enum
    CALLABLE = "CALLABLE"           # Functions, methods, lambdas (unified)

    # Variable subtypes (refined from generic VARIABLE)
    # LOCAL_VAR = "LOCAL_VAR"         # Local variables within functions
    # PARAMETER = "PARAMETER"         # Function/method parameters
    # FIELD = "FIELD"                 # Class/struct member variables
    # STATIC_VAR = "STATIC_VAR"       # Static/class variables
    # GLOBAL_VAR = "GLOBAL_VAR"       # Module-level variables
    # CONSTANT = "CONSTANT"           # const/final/readonly values
    # TYPE_ALIAS = "TYPE_ALIAS"       # typedef, type hints
    # ENUM_VALUE = "ENUM_VALUE"       # Enumeration members

    # Control flow frames (language-agnostic)
    IF_BLOCK = "IF_BLOCK"
    ELIF_BLOCK = "ELIF_BLOCK"
    ELSE_BLOCK = "ELSE_BLOCK"
    FOR_LOOP = "FOR_LOOP"
    WHILE_LOOP = "WHILE_LOOP"
    TRY_BLOCK = "TRY_BLOCK"
    EXCEPT_BLOCK = "EXCEPT_BLOCK"   # Also cpp's catch
    FINALLY_BLOCK = "FINALLY_BLOCK"
    SWITCH_BLOCK = "SWITCH_BLOCK"   # Also python's match
    CASE_BLOCK = "CASE_BLOCK"
    WITH_BLOCK = "WITH_BLOCK"

    # Generic scope for edge cases
    SCOPE = "SCOPE"                 # Generic scope when others don't fit

    # Helper methods for frame type classification
    
    @classmethod
    def control_flow_types(cls) -> set:
        """
        All control flow frame types.
        
        These represent language control structures (conditionals, loops, exception handling).
        """
        return {
            cls.IF_BLOCK, cls.ELIF_BLOCK, cls.ELSE_BLOCK,
            cls.FOR_LOOP, cls.WHILE_LOOP,
            cls.TRY_BLOCK, cls.EXCEPT_BLOCK, cls.FINALLY_BLOCK,
            cls.SWITCH_BLOCK, cls.CASE_BLOCK, cls.WITH_BLOCK
        }
    
    @classmethod
    def structural_types(cls) -> set:
        """
        Structural frame types that create semantic context.
        
        These represent code organization structures (classes, functions, packages).
        """
        return {cls.CLASS, cls.CALLABLE, cls.PACKAGE}
    
    @classmethod
    def context_creating_types(cls) -> set:
        """
        All frame types that should push to the frame stack.
        
        These frames create new scopes for their children in the hierarchy.
        Includes both structural types and control flow types.
        """
        return cls.structural_types() | cls.control_flow_types()
    
    def is_control_flow(self) -> bool:
        """Check if this frame type is a control flow structure."""
        return self in self.control_flow_types()
    
    def is_structural(self) -> bool:
        """Check if this frame type is a structural element."""
        return self in self.structural_types()
    
    def creates_context(self) -> bool:
        """Check if this frame type creates a new context scope."""
        return self in self.context_creating_types()
    
    def has_semantic_name(self) -> bool:
        """
        Check if this frame type has a semantic name extracted via language handler.
        
        Returns True for structural types, False for control flow (which use positional names).
        """
        return self.is_structural()


class EdgeType(Enum):
    """
    Relationship types between frames.
    """

    CONTAINS = "CONTAINS"           # Parent-child hierarchical relationships
    IMPORTS = "IMPORTS"             # Import/include relationships
    CALLS = "CALLS"                 # Function/method calls
    INHERITS = "INHERITS"           # Class inheritance
    IMPLEMENTS = "IMPLEMENTS"       # Interface implementation
    USES = "USES"                   # Field/variable usage (CALLABLE → CLASS)


class ConfidenceTier(Enum):
    HIGH = "HIGH"                   # confidence >= 0.8
    MEDIUM = "MEDIUM"               # confidence 0.5-0.79
    LOW = "LOW"                     # confidence 0.2-0.49
    SPECULATIVE = "SPECULATIVE"     # confidence < 0.2