"""Nabu MCP configuration dataclasses."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict

# Import from framework
from nisaba import MCPContext, MCPConfig

# Import CodebaseConfig
from nabu.mcp.config.codebase_config import CodebaseConfig


@dataclass
class NabuContext(MCPContext):
    """
    Nabu-specific context configuration.

    Extends MCPContext with no additional fields currently.
    """
    pass


@dataclass
class NabuConfig(MCPConfig):
    """
    Nabu MCP server configuration.

    Extends MCPConfig with nabu-specific database and FTS settings.
    """

    # Nabu-specific: Multiple codebase support
    codebases: Dict[str, CodebaseConfig] = field(default_factory=dict)
    active_codebase: Optional[str] = None
    


    # Nabu-specific: FTS defaults
    fts_default_top: int = 25
    fts_default_context_lines: int = 3
    fts_default_max_snippets: int = 5

    # Nabu-specific: File watcher settings (now per-codebase, these are global defaults)
    watch_debounce_seconds: float = 5.0
    extra_ignore_patterns: Optional[List[str]] = None
    watch_extensions: Optional[List[str]] = None

    # Override server name
    server_name: str = "nabu_mcp"

    # Override context with NabuContext
    context: NabuContext = field(default_factory=lambda: NabuContext.load_default(
        contexts_dir=Path(__file__).parent / "contexts"
    ))

    @classmethod
    def from_args(cls, args) -> "NabuConfig":
        """Create config from argparse arguments."""
        # Load context if specified
        contexts_dir = Path(__file__).parent / "contexts"

        if hasattr(args, 'context') and args.context:
            context = NabuContext.load(args.context, contexts_dir=contexts_dir)
        else:
            context = NabuContext.load_default(contexts_dir=contexts_dir)

        # Extract watch settings from context's extra config
        extra_config = getattr(context, '_extra_config', {})

        # Parse multiple codebases from args
        codebases = {}
        active_codebase = None
        
        if hasattr(args, 'codebase') and args.codebase:
            # Multi-codebase mode
            for i, codebase_spec in enumerate(args.codebase):
                try:
                    cb_config = CodebaseConfig.from_string(codebase_spec)
                    codebases[cb_config.name] = cb_config
                    
                    # First one is active by default
                    if i == 0:
                        active_codebase = cb_config.name
                except ValueError as e:
                    raise ValueError(f"Invalid codebase specification: {e}")
            
            # Override with explicit --active if provided
            if hasattr(args, 'active') and args.active:
                if args.active not in codebases:
                    raise ValueError(f"Active codebase '{args.active}' not found in registered codebases")
                active_codebase = args.active
                
        else:
            # BACKWARD COMPATIBILITY: Single codebase mode (old CLI)
            if hasattr(args, 'db_path') and hasattr(args, 'repo_path'):
                cb_config = CodebaseConfig(
                    name="default",
                    repo_path=Path(args.repo_path),
                    db_path=Path(args.db_path),
                    role="active",
                    watch_enabled=extra_config.get('watch_enabled', False)
                )
                codebases["default"] = cb_config
                active_codebase = "default"

        return cls(
            codebases=codebases,
            active_codebase=active_codebase,
            dev_mode=getattr(args, 'dev_mode', False),
            log_level=getattr(args, 'log_level', 'INFO'),
            context=context,
            watch_debounce_seconds=extra_config.get('watch_debounce_seconds', 5.0),
            extra_ignore_patterns=extra_config.get('extra_ignore_patterns'),
            watch_extensions=extra_config.get('watch_extensions')
        )
    
    def get_active_codebase_config(self) -> Optional[CodebaseConfig]:
        """Get configuration for currently active codebase."""
        if self.active_codebase and self.active_codebase in self.codebases:
            return self.codebases[self.active_codebase]
        return None


