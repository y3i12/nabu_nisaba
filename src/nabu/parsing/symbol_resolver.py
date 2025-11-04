"""
Symbol Resolution

Handles cross-references after structure is built.

This phase:
- Takes complete frame hierarchy from GraphBuilder
- Creates IMPORTS, CALLS, INHERITS edges
- Handles uncertain symbol resolution with confidence system
- Uses frame stack for import resolution
"""

from typing import List, Dict, Set, Optional
import re
import logging

from nabu.core.frames import AstFrameBase, AstEdge
from nabu.core.frame_types import FrameNodeType, EdgeType
from nabu.core.frame_stack import FrameStack
from nabu.core.confidence import ConfidenceCalculator
from nabu.core.pattern_confidence import adjust_field_usage_confidence
from nabu.core.resolution_strategy import MemoryResolutionStrategy
from nabu.core.cpp_utils import extract_cpp_class_from_signature
from nabu.language_handlers import language_registry


logger = logging.getLogger(__name__)


class SymbolResolver:
    """
    Handles cross-references after structure is built.
    """

    def __init__(self, context: 'CodebaseContext'):
        """
        Initialize SymbolResolver with shared CodebaseContext.

        Args:
            context: Shared context containing frame_stack, registries, etc.
        """
        from nabu.core.codebase_context import CodebaseContext

        self.context = context
        # Initialize resolution strategy for in-memory lookups
        self.resolution_strategy = MemoryResolutionStrategy(context)

    def resolve_references(self, codebase_frame: AstFrameBase) -> List[AstEdge]:
        """
        Main entry point for symbol resolution.

        Performs multiple passes with decreasing confidence levels.
        """
        self.context.symbol_edges = []

        # Pass 1: Direct imports and inheritance (high confidence)
        self._resolve_imports(codebase_frame)
        self._resolve_inheritance(codebase_frame)

        # Pass 1.5: C++ method-to-class resolution (cross-file CONTAINS edges)
        self._resolve_cpp_method_parents(codebase_frame)

        # Pass 2: Function calls (medium confidence)
        self._resolve_function_calls(codebase_frame)

        # Pass 3: Field usages (Phase 1: Field Usage Tracking)
        self._resolve_field_usages(codebase_frame)

        return self.context.symbol_edges

    def _resolve_imports(self, codebase_frame: AstFrameBase) -> None:
        """
        Resolve import statements.

        Creates IMPORTS edges with confidence based on resolution success.
        Addresses the missing import handling in current implementation.
        """
        for language_frame in codebase_frame.find_children_by_type(FrameNodeType.LANGUAGE):
            self._resolve_imports_for_language(language_frame)

    def _resolve_imports_for_language(self, language_frame: AstFrameBase) -> None:
        """Resolve imports within a specific language."""
        # Get language name for filtering
        language = language_frame.language
        if not language:
            return
            
        # Iterate through processed files and filter by language
        for file_path in self.context.processed_files:
            # Detect language using registry
            file_language = language_registry.detect_language(file_path)
            
            # Only process files that match this language
            if file_language == language:
                self._resolve_imports_for_file_path(file_path, language_frame)

    def _resolve_imports_for_file_path(self, file_path: str, language_frame: AstFrameBase) -> None:
        """
        Resolve imports for a specific file path.

        This is where the sophisticated import resolution happens.
        Uses frame stack for relative import resolution.
        """
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception:
            return  # Skip files that can't be read

        if not file_content:
            return

        # Build context for this file's package
        package_frame = self._find_package_for_file_path(file_path)
        source_frame = package_frame if package_frame else language_frame
        
        if package_frame:
            with self.context.frame_stack.package_context(package_frame):
                with self.context.frame_stack.push_context(language_frame):
                    self._extract_and_resolve_imports(file_path, file_content, language_frame, source_frame)
        else:
            with self.context.frame_stack.push_context(language_frame):
                self._extract_and_resolve_imports(file_path, file_content, language_frame, source_frame)

    def _find_package_for_file_path(self, file_path: str) -> Optional[AstFrameBase]:
        """Find the package that should contain this file based on file path."""
        # Detect language using registry
        language = language_registry.detect_language(file_path)
        if not language:
            return None
            
        # Get language handler to extract package from path
        handler = language_registry.get_handler(language)
        if not handler:
            return None
            
        # Extract package hierarchy from file path
        package_parts = handler.extract_package_hierarchy_from_path(
            file_path,
            self.context.codebase_root
        )
        
        if not package_parts:
            return None
            
        # Build qualified name for the deepest package
        language_frame = self.context.language_frames.get(language)
        if not language_frame:
            return None
            
        qualified_name = language_frame.qualified_name
        for part in package_parts:
            qualified_name = f"{qualified_name}{handler.get_separator()}{part}"
            
        # Look up package in registry
        return self.context.package_registry.get(qualified_name)

    def _extract_and_resolve_imports(self, file_path: str, file_content: str, language_frame: AstFrameBase, source_frame: AstFrameBase) -> None:
        """
        Extract import statements from file content and resolve them using language handler.

        Delegates to language-specific handlers for import extraction.
        
        Args:
            file_path: Path to the source file
            file_content: Content of the file
            language_frame: Language root frame
            source_frame: Package or language frame to use as import source
        """
        if not file_content:
            return

        language = language_frame.language
        handler = language_registry.get_handler(language)

        if not handler:
            return

        # Extract imports using language handler
        imports = handler.extract_imports(file_content)
        
        # Resolve each import
        for import_stmt in imports:
            self._resolve_single_import_with_handler(
                source_frame, import_stmt.import_path, language_frame, handler
            )

    def _resolve_single_import_with_handler(
        self,
        file_frame: AstFrameBase,
        import_path: str,
        language_frame: AstFrameBase,
        handler
    ) -> None:
        """
        Resolve a single import using language handler.

        Args:
            file_frame: File containing the import
            import_path: Import path extracted by handler
            language_frame: Language root frame
            handler: Language handler instance
        """
        confidence = 1.0
        target_frame = None

        # Try different resolution strategies with decreasing confidence

        # 1. Relative import resolution using frame stack
        if import_path.startswith('.'):
            target_frame = self.context.frame_stack.resolve_relative_import(import_path)
            confidence = 0.8 if target_frame else 0.3

        # 2. Absolute import resolution
        if not target_frame:
            target_frame = self._resolve_absolute_import(import_path, language_frame, handler)
            confidence = 0.7 if target_frame else 0.2

        # 3. Create edge if target resolved
        if target_frame:
            edge = AstEdge(
                id=self._next_edge_id(),
                subject_frame=file_frame,
                object_frame=target_frame,
                type=EdgeType.IMPORTS,
                confidence=confidence,
                metadata={
                    'import_path': import_path,
                    'provenance': "resolved" if confidence > 0.5 else "speculative"
                }
            )
            self.context.symbol_edges.append(edge)

    def _resolve_absolute_import(self, import_path: str, language_frame: AstFrameBase, handler) -> Optional[AstFrameBase]:
        """
        Resolve absolute import within the language frame.

        Uses language-specific separator from handler to split import paths.
        This ensures correct resolution for:
        - Python/Java: dot notation (foo.bar.baz)
        - C++/Perl: double-colon notation (foo::bar::baz)
        
        Args:
            import_path: Import path (e.g., "pybind11::pytypes" or "os.path")
            language_frame: Language root frame to search within
            handler: Language handler providing get_separator() method
        """
        # Get language-specific separator (. for Python/Java, :: for C++/Perl)
        separator = handler.get_separator()
        parts = import_path.split(separator)
        current_frame = language_frame

        for part in parts:
            child = current_frame.find_child_by_name(part)
            if not child:
                return None
            current_frame = child

        return current_frame

    def _resolve_external_import(self, import_path: str, language_frame: AstFrameBase) -> AstFrameBase:
        """
        Create external import frame.

        For standard library or external packages.
        """
        return self.context.frame_stack.create_external_import_frame(import_path, language_frame)

    def _create_unknown_import(self, import_path: str, language_frame: AstFrameBase) -> AstFrameBase:
        """
        Create frame for completely unknown imports.
        
        Handles dotted paths by creating intermediate package hierarchy.
        """
        from nabu.parsing.frame_factory import FrameFactory
        
        # Split dotted path
        parts = import_path.split('.')
        
        if len(parts) == 1:
            # Simple case: single package name
            return FrameFactory.create_external_frame(
                frame_type=FrameNodeType.PACKAGE,
                name=import_path,
                qualified_name=f"{language_frame.qualified_name}.{import_path}",
                language=language_frame.language,
                context=self.context,
                confidence=0.1,
                provenance="unknown_import"
            )
        else:
            # Complex case: dotted path - create hierarchy
            return self._ensure_package_path(parts, language_frame)

    def _resolve_inheritance(self, codebase_frame: AstFrameBase) -> None:
        """
        Resolve class inheritance relationships.

        Creates INHERITS edges with high confidence when found.
        Uses class_registry for efficient lookup instead of graph traversal.
        """
        for language_frame in codebase_frame.find_children_by_type(FrameNodeType.LANGUAGE):
            language = language_frame.language
            
            # Snapshot registry to avoid "dictionary changed size during iteration" error
            # (new external classes may be added during _resolve_class_inheritance)
            class_items = list(self.context.class_registry.items())
            
            # Use registry to get all classes for this language - O(n) instead of O(n*m) traversal
            for qualified_name, class_frame in class_items:
                # Filter by language to only process classes in this language tree
                if class_frame.language == language:
                    self._resolve_class_inheritance(class_frame, language_frame)

    def _resolve_cpp_method_parents(self, codebase_frame: AstFrameBase) -> None:
        """
        Resolve C++ method-to-class relationships across files.
        
        C++ separates declarations (.h) from implementations (.cpp).
        This method creates CONTAINS edges from CLASS frames to their 
        method implementations by:
        
        1. Finding C++ CALLABLE frames
        2. Extracting class scope from method signature (ClassName::methodName)
        3. Finding matching CLASS frame by qualified name
        4. Creating CONTAINS edge: CLASS → CALLABLE
        5. Fixing CALLABLE's qualified name
        
        Example:
            CLASS: nabu_nisaba.cpp_root::utils.Logger (from logger.h)
            CALLABLE: nabu_nisaba.cpp_root::utils.log (from logger.cpp)
            Pattern match: "Logger::log" in content
            Creates: CLASS(Logger) -[CONTAINS]-> CALLABLE(log)
            Fixes qualified_name: ::utils.log → ::utils.Logger.log
        """
        import re
        from nabu.core.frame_types import FrameNodeType, EdgeType
        from nabu.core.confidence import ConfidenceCalculator
        
        # Find all C++ CALLABLE frames
        callables = []
        for frame in self._find_all_callables(codebase_frame):
            if frame.language == 'cpp':
                callables.append(frame)
        
        logger.info(f"Resolving C++ method parents for {len(callables)} callables")
        
        resolved_count = 0
        failed_count = 0
        
        for callable_frame in callables:
            # Skip if no content
            if not callable_frame.content:
                continue
            
            # Extract class scope from method signature
            class_name = self._extract_cpp_class_from_signature(callable_frame.content)
            
            if not class_name:
                # Not a class method (free function) or couldn't extract
                continue
            
            # Find CLASS frame with matching name
            class_frame = self._find_cpp_class_by_name(class_name, callable_frame)
            
            if not class_frame:
                # Class not found (external, or parsing issue)
                failed_count += 1
                logger.debug(f"Could not find CLASS '{class_name}' for method '{callable_frame.qualified_name}'")
                continue
            
            # Create CONTAINS edge: CLASS → CALLABLE
            edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
                EdgeType.CONTAINS,
                class_frame.confidence,
                callable_frame.confidence
            )
            
            edge = AstEdge(
                id=self._next_edge_id(),
                subject_frame=class_frame,
                object_frame=callable_frame,
                type=EdgeType.CONTAINS,
                confidence=edge_confidence,
                metadata={'cross_file_resolved': True, 'class_name': class_name}
            )
            
            self.context.symbol_edges.append(edge)
            
            # Add to class's children (for in-memory hierarchy)
            if callable_frame not in class_frame.children:
                class_frame.add_child(callable_frame)
            
            # Fix qualified name: ::utils.log → ::utils.Logger.log
            callable_frame.qualified_name = self._build_cpp_method_qualified_name(
                class_frame.qualified_name,
                callable_frame.name
            )
            
            resolved_count += 1
        
        logger.info(f"Resolved {resolved_count} C++ method-to-class relationships, {failed_count} failed")

    def _extract_cpp_class_from_signature(self, method_content: str) -> Optional[str]:
        """
        Extract class name from C++ method signature.

        Delegated to shared cpp_utils to avoid duplication with RelationshipRepairer.

        Returns:
            Class name or None if not a class method
        """
        return extract_cpp_class_from_signature(method_content)

    def _find_cpp_class_by_name(
        self,
        class_name: str,
        context_frame: AstFrameBase
    ) -> Optional[AstFrameBase]:
        """
        Find C++ CLASS frame by name.
        
        Search strategy:
        1. Look in same language (cpp)
        2. Look in same namespace/package context
        3. Match by class name
        
        Args:
            class_name: Simple class name (e.g., "Logger")
            context_frame: Method frame (for context about language/package)
        
        Returns:
            CLASS frame or None
        """
        # Get language context
        language = context_frame.language
        
        # Search class registry for matches
        candidates = []
        for qualified_name, class_frame in self.context.class_registry.items():
            if class_frame.language == language and class_frame.name == class_name:
                candidates.append(class_frame)
        
        if len(candidates) == 0:
            return None
        elif len(candidates) == 1:
            return candidates[0]
        else:
            # Multiple matches - prefer one in same namespace
            method_qn = context_frame.qualified_name
            
            # Try to find class in same namespace
            for candidate in candidates:
                # Check if class's qualified name shares namespace with method
                class_qn_parts = candidate.qualified_name.split('::')
                method_qn_parts = method_qn.split('::')
                
                # Compare namespace parts (all except last)
                if class_qn_parts[:-1] == method_qn_parts[:-1]:
                    return candidate
            
            # If no namespace match, return first (best effort)
            return candidates[0]

    def _build_cpp_method_qualified_name(
        self,
        class_qualified_name: str,
        method_name: str
    ) -> str:
        """
        Build correct qualified name for C++ method.
        
        Args:
            class_qualified_name: "nabu_nisaba.cpp_root::utils.Logger"
            method_name: "log"
        
        Returns:
            "nabu_nisaba.cpp_root::utils.Logger.log"
            
        Note: Uses '.' separator between class and method (not '::')
        to match existing qualified name patterns in the database.
        """
        # Use dot separator (not ::) to be consistent with Python style
        return f"{class_qualified_name}.{method_name}"

    def _resolve_class_inheritance(self, class_frame: AstFrameBase, language_frame: AstFrameBase) -> None:
        """
        Resolve inheritance for a single class using language handler.

        Delegates to language-specific handlers for base class extraction.
        """
        if not class_frame.content:
            return

        handler = language_registry.get_handler(language_frame.language)
        if not handler:
            return

        # Extract base classes using language handler
        base_classes = handler.extract_base_classes(class_frame.content)

        # Resolve each base class
        for base_class in base_classes:
            if base_class.strip():
                self._resolve_parent_class(class_frame, base_class, language_frame)

    def _resolve_parent_class(self, class_frame: AstFrameBase, parent_name: str, language_frame: AstFrameBase) -> None:
        """Resolve parent class and create INHERITS edge."""
        # Try to find parent class in the same language
        parent_frame = self._find_class_by_name(parent_name, language_frame)

        if not parent_frame:
            # Create external parent with low confidence
            parent_frame = self._create_external_class(parent_name, language_frame)

        # Create INHERITS edge
        edge_confidence = ConfidenceCalculator.calculate_edge_confidence(
            EdgeType.INHERITS, class_frame.confidence, parent_frame.confidence
        )

        edge = AstEdge(
            id=self._next_edge_id(),
            subject_frame=class_frame,
            object_frame=parent_frame,
            type=EdgeType.INHERITS,
            confidence=edge_confidence,
            metadata={'parent_name': parent_name}
        )
        self.context.symbol_edges.append(edge)

    def _find_class_by_name(self, class_name: str, language_frame: AstFrameBase) -> Optional[AstFrameBase]:
        """
        Find class by name in language tree using registry.
        
        Uses class_registry for O(n) lookup instead of recursive graph traversal.
        """
        language = language_frame.language
        
        # Search registry for class with matching name and language
        for qualified_name, class_frame in self.context.class_registry.items():
            if class_frame.language == language and class_frame.name == class_name:
                return class_frame
        
        return None

    def _create_external_class(self, class_name: str, language_frame: AstFrameBase) -> AstFrameBase:
        """
        Create external class frame.
        
        Checks context.class_registry to prevent duplicates.
        
        Handles dotted paths like 'nabu.core.BlockFrame' by:
        1. Splitting into package parts and class name
        2. Creating/finding intermediate package hierarchy via _ensure_package_path
        3. Checking if class already exists globally
        4. Using FrameFactory for creation
        """
        from nabu.parsing.frame_factory import FrameFactory
        
        # Split dotted path: 'nabu.core.SomeClass' -> ['nabu', 'core'], 'SomeClass'
        parts = class_name.split('.')
        
        if len(parts) == 1:
            # Simple case: just a class name with no package path
            simple_name = parts[0]
            qualified_name = f"{language_frame.qualified_name}.{simple_name}"
        else:
            # Complex case: dotted path with packages
            package_parts = parts[:-1]  # e.g., ['nabu', 'core']
            simple_name = parts[-1]      # e.g., 'SomeClass'
            
            # Create or find package hierarchy
            parent_frame = self._ensure_package_path(package_parts, language_frame)
            qualified_name = f"{parent_frame.qualified_name}.{simple_name}"
        
        # Use FrameFactory to create external class with deduplication
        external_class = FrameFactory.create_external_frame(
            frame_type=FrameNodeType.CLASS,
            name=simple_name,
            qualified_name=qualified_name,
            language=language_frame.language,
            context=self.context,
            confidence=0.3,
            provenance="external"
        )
        
        return external_class

    def _ensure_package_path(self, package_parts: List[str], language_frame: AstFrameBase) -> AstFrameBase:
        """
        Ensure package hierarchy exists, creating packages as needed.
        
        Now uses FrameFactory for consistent external frame creation.
        Uses context.package_registry for global lookups to prevent duplicate packages.
        
        For package_parts = ['nabu', 'core'], creates:
        - language_frame.nabu (if not exists globally)
        - language_frame.nabu.core (if not exists globally)
        
        Returns the deepest package frame.
        """
        from nabu.parsing.frame_factory import FrameFactory
        
        current_frame = language_frame
        current_qualified = language_frame.qualified_name
        
        for part in package_parts:
            # Build qualified name for this package level
            next_qualified = f"{current_qualified}.{part}"
            
            # Check global package registry first
            existing = self.context.package_registry.get(next_qualified)
            
            if existing and existing.type == FrameNodeType.PACKAGE:
                # Package exists globally - reuse it
                current_frame = existing
                current_qualified = next_qualified
            else:
                # Package doesn't exist - create it using FrameFactory
                new_package = FrameFactory.create_external_frame(
                    frame_type=FrameNodeType.PACKAGE,
                    name=part,
                    qualified_name=next_qualified,
                    language=language_frame.language,
                    context=self.context,
                    confidence=0.3,
                    provenance="external"
                )
                
                current_frame = new_package
                current_qualified = next_qualified
        
        return current_frame

    def _resolve_function_calls(self, codebase_frame: AstFrameBase) -> None:
        """
        Resolve function call relationships.
        
        Creates CALLS edges by:
        1. Finding all CALLABLE frames
        2. Extracting call sites using language handlers
        3. Resolving call targets to frames
        4. Creating CALLS edges with confidence
        """
        # Find all callable frames in the codebase
        callables = self._find_all_callables(codebase_frame)
        
        for caller_frame in callables:
            # Get language handler for this file
            handler = self._get_handler_for_frame(caller_frame)
            if not handler:
                continue
            
            # Skip if no content or no tree-sitter node
            if not caller_frame.content or not hasattr(caller_frame, '_tree_sitter_node') or not caller_frame._tree_sitter_node:
                continue
            
            # Extract call sites using language handler
            try:
                call_sites = handler.extract_call_sites(
                    caller_frame.content,
                    caller_frame._tree_sitter_node
                )
            except Exception:
                # If extraction fails, continue with next callable
                continue
            
            # Resolve each call site to a target frame
            for callee_name, line_number in call_sites:
                callee_frame = self._resolve_callable_by_name(
                    callee_name,
                    caller_frame
                )
                
                if callee_frame:
                    # Calculate confidence for CALLS edge
                    confidence = ConfidenceCalculator.calculate_edge_confidence(
                        EdgeType.CALLS,
                        caller_frame.confidence,
                        callee_frame.confidence
                    )
                    
                    # Create CALLS edge
                    edge = AstEdge(
                        id=self._next_edge_id(),
                        subject_frame=caller_frame,
                        object_frame=callee_frame,
                        type=EdgeType.CALLS,
                        confidence=confidence,
                        metadata={"line": line_number}
                    )
                    
                    self.context.symbol_edges.append(edge)

    def _resolve_field_usages(self, codebase_frame: AstFrameBase) -> None:
        """
        Resolve field usage relationships.
        
        Creates USES edges by:
        1. Finding all CALLABLE frames
        2. For each CALLABLE, find its parent CLASS frame
        3. Extract field names from CLASS.instance_fields + CLASS.static_fields
        4. Extract field usage sites using language handler
        5. Create USES edges: CALLABLE → CLASS with field metadata
        
        Edge metadata format:
        {
            "field_name": "calculator",
            "access_type": "read",  # "read", "write", or "both"
            "line": 6
        }
        """
        # Find all callable frames in the codebase
        callables = self._find_all_callables(codebase_frame)
        
        logger.info(f"Resolving field usages for {len(callables)} callables")
        
        for callable_frame in callables:
            # Get language handler for this file
            handler = self._get_handler_for_frame(callable_frame)
            if not handler:
                continue
            
            # Skip if no content or no tree-sitter node
            if not callable_frame.content or not hasattr(callable_frame, '_tree_sitter_node') or not callable_frame._tree_sitter_node:
                continue
            
            # Find parent CLASS frame
            parent_class = self._find_parent_class(callable_frame)
            if not parent_class:
                continue  # Not a method (free function), no fields to use
            
            # Extract field names from parent class
            field_names = self._get_field_names_from_class(parent_class)
            if not field_names:
                continue  # No fields in parent class
            
            # Extract field usage sites using language handler
            try:
                field_usages = handler.extract_field_usages(
                    callable_frame.content,
                    callable_frame._tree_sitter_node,
                    field_names
                )
            except Exception as e:
                logger.warning(f"Failed to extract field usages from {callable_frame.qualified_name}: {e}")
                continue
            
            # Create USES edge for each field usage
            for field_name, line_number, access_type, pattern_type in field_usages:
                # Calculate base confidence for USES edge
                base_confidence = ConfidenceCalculator.calculate_edge_confidence(
                    EdgeType.USES,
                    callable_frame.confidence,
                    parent_class.confidence
                )
                
                # Apply pattern-based adjustment
                confidence = adjust_field_usage_confidence(base_confidence, pattern_type)
                
                # Create USES edge
                edge = AstEdge(
                    id=self._next_edge_id(),
                    subject_frame=callable_frame,
                    object_frame=parent_class,
                    type=EdgeType.USES,
                    confidence=confidence,
                    metadata={
                        "field_name": field_name,
                        "access_type": access_type,
                        "line": line_number,
                        "pattern_type": pattern_type
                    }
                )
                
                self.context.symbol_edges.append(edge)
    
    def _find_parent_class(self, callable_frame: AstFrameBase) -> Optional[AstFrameBase]:
        """
        Find the parent CLASS frame for a CALLABLE frame.
        
        Traverses up the frame hierarchy to find the first CLASS frame.
        Returns None if callable is a free function (not a method).
        """
        # Check immediate parent
        if hasattr(callable_frame, 'parent') and callable_frame.parent:
            parent = callable_frame.parent
            
            # Walk up the hierarchy until we find a CLASS
            while parent:
                if parent.type == FrameNodeType.CLASS:
                    return parent
                
                # Move to parent's parent
                if hasattr(parent, 'parent'):
                    parent = parent.parent
                else:
                    break
        
        return None
    
    def _get_field_names_from_class(self, class_frame: AstFrameBase) -> List[str]:
        """
        Extract field names from a CLASS frame.
        
        Combines instance_fields and static_fields into a single list of names.
        """
        from nabu.core.frames import AstClassFrame
        
        if not isinstance(class_frame, AstClassFrame):
            return []
        
        field_names = []
        
        # Extract instance field names
        if class_frame.instance_fields:
            for field_info in class_frame.instance_fields:
                field_names.append(field_info.name)
        
        # Extract static field names
        if class_frame.static_fields:
            for field_info in class_frame.static_fields:
                field_names.append(field_info.name)
        
        return field_names

    def _find_all_callables(self, frame: AstFrameBase) -> List[AstFrameBase]:
        """
        Recursively find all CALLABLE frames in the hierarchy.
        
        Returns:
            List of all callable frames (functions, methods, lambdas)
        """
        callables = []
        visited = set()  # Track visited frames to avoid infinite recursion
        
        def _collect_callables(f: AstFrameBase):
            # Avoid infinite recursion with multi-parent cycles
            frame_id = id(f)
            if frame_id in visited:
                return
            visited.add(frame_id)
            
            if f.type == FrameNodeType.CALLABLE:
                callables.append(f)
            
            # Recurse into children
            if hasattr(f, 'children') and f.children:
                for child in f.children:
                    _collect_callables(child)
        
        _collect_callables(frame)
        return callables
    
    def _get_handler_for_frame(self, frame: AstFrameBase):
        """
        Get the language handler for a frame.
        
        Looks up the language from the frame and returns the appropriate handler.
        """
        if not hasattr(frame, 'language') or not frame.language:
            return None
        
        return language_registry.get_handler(frame.language)
    
    def _resolve_callable_by_name(
        self,
        callee_name: str,
        caller_frame: AstFrameBase
    ) -> Optional[AstFrameBase]:
        """
        Resolve callable name to frame using strategy pattern.

        Delegates to MemoryResolutionStrategy which implements the 3-strategy
        algorithm (exact/context/partial) using in-memory registries.

        Args:
            callee_name: Name of the callable (e.g., 'foo', 'module.func')
            caller_frame: Frame where the call originates (for context)

        Returns:
            The target callable frame if found, None otherwise
        """
        # Strategy 1: Exact match
        result = self.resolution_strategy.resolve_callable_exact(callee_name)
        if result:
            frame = self.context.callable_registry.get(result.qualified_name)
            if frame:
                return frame

        # Strategy 2: Context-based match
        caller_package_qname = self.resolution_strategy.get_package_qualified_name(caller_frame.id)
        if caller_package_qname:
            result = self.resolution_strategy.resolve_callable_with_context(
                callee_name,
                caller_package_qname
            )
            if result:
                frame = self.context.callable_registry.get(result.qualified_name)
                if frame:
                    return frame

        # Strategy 3: Partial match
        simple_name = callee_name.split('.')[-1]
        result = self.resolution_strategy.resolve_callable_partial(simple_name)
        if result:
            frame = self.context.callable_registry.get(result.qualified_name)
            if frame:
                return frame

        return None
    
    def _get_package_qualified_name(self, frame: AstFrameBase) -> Optional[str]:
        """
        Get the qualified name of the package/module containing a frame.
        
        Walks up the hierarchy to find the containing PACKAGE frame.
        """
        current = frame
        visited = set()  # Track visited frames to avoid infinite loops
        
        # Walk up to find containing package
        while current:
            # Avoid infinite loops in multi-parent graphs
            frame_id = id(current)
            if frame_id in visited:
                break
            visited.add(frame_id)
            
            if current.type == FrameNodeType.PACKAGE:
                return current.qualified_name
            
            # Move to parent (use first parent if multiple)
            if hasattr(current, 'parents') and current.parents:
                current = current.parents[0] if current.parents else None
            elif hasattr(current, 'parent') and current.parent:
                current = current.parent
            else:
                break
        
        return None

    def _next_edge_id(self) -> int:
        """Generate next edge ID."""
        return self.context.next_edge_id()
