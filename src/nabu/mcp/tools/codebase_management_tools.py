"""Codebase management tools for multi-codebase support."""

from nabu.mcp.tools.base import NabuTool
from nisaba.tools.base_tool import BaseToolResponse


class ActivateCodebaseTool(NabuTool):
    """Switch active codebase for subsequent queries."""
    
    async def execute(self, codebase: str) -> BaseToolResponse:
        """
        Activate a codebase by name.
        
        Sets the specified codebase as active. Subsequent tool calls will
        default to this codebase unless explicitly overridden.
        
        :param codebase: Name of codebase to activate
        :return: Confirmation with codebase details
        :meta pitch: Switch active codebase context
        :meta when: When you want to explore a different codebase
        """
        import time
        start_time = time.time()
        
        # Validate codebase exists
        if codebase not in self.config.codebases:
            available = list(self.config.codebases.keys())
            return self.response_error(f"Unknown codebase: {codebase}, available: {', '.join(available)}")
        
        # Update active codebase
        old_active = self.config.active_codebase
        self.config.active_codebase = codebase
        
        # Update factory's backward-compatibility pointers
        self.factory.db_manager = self.factory.db_managers[codebase]
        if codebase in self.factory.incremental_updaters:
            self.factory.incremental_updater = self.factory.incremental_updaters[codebase]
        
        cb_config = self.config.codebases[codebase]
        
        return self.response_success(f"codebase changed from `{old_active}` to `{codebase}` ({str(cb_config.repo_path)})")


class ListCodebasesTool(NabuTool):
    """List all registered codebases with their configurations."""
    
    async def execute(self) -> BaseToolResponse:
        """
        List all registered codebases.
        
        Returns information about all registered codebases including their
        paths, roles, and active status.
        
        :return: List of codebase configurations
        :meta pitch: View all registered codebases
        :meta when: When you need to see available codebases
        """
        import time
        start_time = time.time()
        
        codebases = []
        for name, cb_config in self.config.codebases.items():
            codebases.append({
                "name": name,
                "role": cb_config.role,
                "is_active": name == self.config.active_codebase,
                "repo_path": str(cb_config.repo_path),
                "db_path": str(cb_config.db_path),
                "watch_enabled": cb_config.watch_enabled
            })
        
        return self.response_success({
            "codebases": codebases,
            "active_codebase": self.config.active_codebase,
            "total_count": len(codebases)
        })
