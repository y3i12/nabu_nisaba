"""
Frame factory for creating and managing frame instances.

Centralizes frame instantiation logic, class selection, and deduplication.
"""
from typing import Optional, Dict, Type, Callable

from nabu.core.frames import (
    AstFrameBase, AstClassFrame, AstCallableFrame, AstPackageFrame,
    AstLanguageFrame, AstCodebaseFrame
)
from nabu.core.frame_types import FrameNodeType
from nabu.parsing.raw_extraction import RawNode


class FrameFactory:
    """
    Factory for creating specialized frame instances with deduplication.
    
    Centralizes:
    - Frame class selection based on frame type
    - Registry-based deduplication for CLASS, CALLABLE, PACKAGE
    - Multi-parent relationship management
    """
    
    # Map frame types to specialized frame classes
    _FRAME_CLASSES: Dict[FrameNodeType, Type[AstFrameBase]] = {
        FrameNodeType.CODEBASE: AstCodebaseFrame,
        FrameNodeType.LANGUAGE: AstLanguageFrame,
        FrameNodeType.PACKAGE: AstPackageFrame,
        FrameNodeType.CLASS: AstClassFrame,
        FrameNodeType.CALLABLE: AstCallableFrame,
        # All other types (control flow, etc.) default to AstFrameBase
    }
    
    # Map frame types to their deduplication registries
    # Registry accessor functions take CodebaseContext and return the appropriate registry dict
    _DEDUP_REGISTRIES: Dict[FrameNodeType, Callable] = {
        FrameNodeType.CLASS: lambda ctx: ctx.class_registry,
        FrameNodeType.CALLABLE: lambda ctx: ctx.callable_registry,
        FrameNodeType.PACKAGE: lambda ctx: ctx.package_registry,
    }
    
    @classmethod
    def create_frame(
        cls,
        frame_type: FrameNodeType,
        name: Optional[str],
        qualified_name: Optional[str],
        raw_node: RawNode,
        language: str,
        context: 'CodebaseContext',
    ) -> AstFrameBase:
        """
        Create frame instance with automatic deduplication.
        
        Args:
            frame_type: Type of frame to create
            name: Frame name
            qualified_name: Fully qualified name
            raw_node: Source raw node with location metadata
            language: Programming language
            context: Codebase context containing registries
            
        Returns:
            AstFrameBase: New or existing frame instance
        """
        # Control flow frames use location-based deduplication (file+byte position)
        if frame_type.is_control_flow():
            location_key = f"{raw_node.file_path}:{raw_node.start_byte}:{raw_node.end_byte}"
            
            if location_key in context.control_flow_registry:
                existing_frame = context.control_flow_registry[location_key]
                
                # Check if content changed (for incremental updates)
                if existing_frame.content != raw_node.content:
                    cls._update_frame_content(existing_frame, raw_node, language)
                
                # Reuse existing frame - ensure current context is parent (multi-parent support)
                if context.frame_stack.current_frame:
                    context.frame_stack.current_frame.add_child(existing_frame)
                return existing_frame
            
            # Create new control flow frame
            frame = cls._instantiate_frame(
                frame_type, name, qualified_name, raw_node, language
            )
            context.control_flow_registry[location_key] = frame
            return frame
        
        # Semantic frames (CLASS, CALLABLE, PACKAGE) use qualified_name deduplication
        if frame_type in cls._DEDUP_REGISTRIES and qualified_name:
            registry = cls._DEDUP_REGISTRIES[frame_type](context)
            
            if qualified_name in registry:
                existing_frame = registry[qualified_name]
                
                # Verify correct type (safety check)
                expected_class = cls._FRAME_CLASSES.get(frame_type, AstFrameBase)
                if isinstance(existing_frame, expected_class):
                    # Check if content changed (for incremental updates)
                    if existing_frame.content != raw_node.content:
                        cls._update_frame_content(existing_frame, raw_node, language)
                    
                    # Reuse existing frame - ensure current context is parent (multi-parent support)
                    if context.frame_stack.current_frame:
                        context.frame_stack.current_frame.add_child(existing_frame)
                    return existing_frame
        
        # Create new frame instance
        frame = cls._instantiate_frame(
            frame_type, name, qualified_name, raw_node, language
        )
        
        # Register in appropriate registry if applicable
        if frame_type in cls._DEDUP_REGISTRIES and qualified_name:
            registry = cls._DEDUP_REGISTRIES[frame_type](context)
            registry[qualified_name] = frame
        
        return frame

    @classmethod
    def _update_frame_content(
        cls,
        frame: AstFrameBase,
        raw_node: RawNode,
        language: str,
    ) -> None:
        """
        Update existing frame with new content from raw_node.
        
        Called when a cached frame is reused but the source code has changed.
        Updates content, location, tree-sitter node, structured info, and recomputes ID.
        
        Args:
            frame: Existing frame to update
            raw_node: New raw node with updated content
            language: Programming language
        """
        # Update basic content and location
        frame.content = raw_node.content
        frame.start_line = raw_node.start_line
        frame.end_line = raw_node.end_line
        frame.start_byte = raw_node.start_byte
        frame.end_byte = raw_node.end_byte
        
        # Update tree-sitter node for call site extraction
        if hasattr(raw_node, 'ts_node') and raw_node.ts_node:
            frame._tree_sitter_node = raw_node.ts_node
        else:
            # Clear stale tree-sitter node
            if hasattr(frame, '_tree_sitter_node'):
                frame._tree_sitter_node = None
        
        # Re-extract structured information using language handler
        from nabu.language_handlers.registry import language_registry
        from nabu.core.frames import AstClassFrame, AstCallableFrame
        
        handler = language_registry.get_handler(language)
        
        if handler and raw_node.content:
            ts_node = raw_node.ts_node if hasattr(raw_node, 'ts_node') else None
            
            # Update class-specific fields
            if frame.type == FrameNodeType.CLASS and isinstance(frame, AstClassFrame):
                frame.instance_fields = handler.extract_instance_fields(raw_node.content, ts_node)
                frame.static_fields = handler.extract_static_fields(raw_node.content, ts_node)
            
            # Update callable-specific fields
            elif frame.type == FrameNodeType.CALLABLE and isinstance(frame, AstCallableFrame):
                frame.parameters = handler.extract_parameters(raw_node.content, ts_node)
                frame.return_type = handler.extract_return_type(raw_node.content)
        
        # Recompute ID based on new content (critical for incremental update diff detection)
        frame.compute_id()
    
    @classmethod
    def _instantiate_frame(
        cls,
        frame_type: FrameNodeType,
        name: Optional[str],
        qualified_name: Optional[str],
        raw_node: RawNode,
        language: str,
    ) -> AstFrameBase:
        """
        Instantiate frame of appropriate type.
        
        Args:
            frame_type: Type of frame to create
            name: Frame name
            qualified_name: Fully qualified name
            raw_node: Source raw node with location metadata
            language: Programming language
            
        Returns:
            New frame instance with computed ID
        """
        # Select appropriate frame class
        frame_class = cls._FRAME_CLASSES.get(frame_type, AstFrameBase)
        
        # Selective content storage for control flows (first line only)
        if frame_type.is_control_flow():
            # Extract only the control statement line (not the body)
            first_line = raw_node.content.split('\n')[0] if raw_node.content else None
            frame_content = first_line
        else:
            # Full content for semantic frames
            frame_content = raw_node.content
        
        # Create instance with temporary ID (will be computed after)
        frame = frame_class(
            id="temp",  # Temporary - will be computed
            type=frame_type,
            name=name,
            qualified_name=qualified_name,
            content=frame_content,
            start_line=raw_node.start_line,
            end_line=raw_node.end_line,
            start_byte=raw_node.start_byte,
            end_byte=raw_node.end_byte,
            file_path=raw_node.file_path,
            language=language,
            confidence=1.0,
            provenance="parsed"
        )
        
        # Extract structured information using language handler
        from nabu.language_handlers.registry import language_registry
        from nabu.core.frames import AstClassFrame, AstCallableFrame
        
        handler = language_registry.get_handler(language)
        
        if handler and raw_node.content:
            # Pass ts_node for accurate decorator detection
            ts_node = raw_node.ts_node if hasattr(raw_node, 'ts_node') else None
            
            if frame_type == FrameNodeType.CLASS and isinstance(frame, AstClassFrame):
                frame.instance_fields = handler.extract_instance_fields(raw_node.content, ts_node)
                frame.static_fields = handler.extract_static_fields(raw_node.content, ts_node)
            
            elif frame_type == FrameNodeType.CALLABLE and isinstance(frame, AstCallableFrame):
                frame.parameters = handler.extract_parameters(raw_node.content, ts_node)
                frame.return_type = handler.extract_return_type(raw_node.content)
        
        # Store tree-sitter node directly for call site extraction
        # Note: tree-sitter nodes cannot be weakly referenced
        if hasattr(raw_node, 'ts_node') and raw_node.ts_node:
            frame._tree_sitter_node = raw_node.ts_node
        
        # Compute unique ID based on frame content
        frame.compute_id()
        
        # Cache heading for DB storage (compute once, use many times)
        frame._cached_heading = frame.heading
        
        return frame
    
    @classmethod
    def requires_deduplication(cls, frame_type: FrameNodeType) -> bool:
        """
        Check if frame type requires deduplication via registry.
        
        Args:
            frame_type: Frame type to check
            
        Returns:
            True if this frame type should be deduplicated
        """
        return frame_type in cls._DEDUP_REGISTRIES
    
    @classmethod
    def get_frame_class(cls, frame_type: FrameNodeType) -> Type[AstFrameBase]:
        """
        Get the specialized frame class for a given frame type.
        
        Args:
            frame_type: Frame type
            
        Returns:
            Frame class (AstClassFrame, AstCallableFrame, or AstFrameBase)
        """
        return cls._FRAME_CLASSES.get(frame_type, AstFrameBase)

    @classmethod
    def create_external_frame(
        cls,
        frame_type: FrameNodeType,
        name: str,
        qualified_name: str,
        language: str,
        context: 'CodebaseContext',
        confidence: float = 0.3,
        provenance: str = "external"
    ) -> AstFrameBase:
        """
        Create external/unknown frame with low confidence.
        
        Used by SymbolResolver for creating frames for external dependencies
        (libraries, unresolved imports, etc.) that aren't in the parsed codebase.
        
        Args:
            frame_type: Type of frame to create (CLASS, PACKAGE, etc.)
            name: Simple name (not qualified)
            qualified_name: Fully qualified name
            language: Programming language
            context: Codebase context containing registries
            confidence: Confidence level (default 0.3 for external)
            provenance: Provenance string (default "external")
            
        Returns:
            AstFrameBase: New or existing frame instance
        """
        # Check deduplication registry if applicable
        if frame_type in cls._DEDUP_REGISTRIES and qualified_name:
            registry = cls._DEDUP_REGISTRIES[frame_type](context)
            
            if qualified_name in registry:
                existing_frame = registry[qualified_name]
                # Verify correct type (safety check)
                expected_class = cls._FRAME_CLASSES.get(frame_type, AstFrameBase)
                if isinstance(existing_frame, expected_class):
                    return existing_frame
        
        # Create new external frame instance
        frame_class = cls._FRAME_CLASSES.get(frame_type, AstFrameBase)
        
        frame = frame_class(
            id="temp",  # Temporary - will be computed
            type=frame_type,
            name=name,
            qualified_name=qualified_name,
            confidence=confidence,
            provenance=provenance,
            language=language,
            file_path="<external_or_unresolved>",  # Mark as external
            metadata={'created_by': 'symbol_resolver'}
        )
        
        # Compute stable ID based on frame properties
        frame.compute_id()
        
        # Register in appropriate registry if applicable
        if frame_type in cls._DEDUP_REGISTRIES and qualified_name:
            registry = cls._DEDUP_REGISTRIES[frame_type](context)
            registry[qualified_name] = frame
        
        # Store in external frames list
        context.external_frames.append(frame)
        
        return frame
