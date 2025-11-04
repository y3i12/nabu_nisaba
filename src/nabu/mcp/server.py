#!/usr/bin/env python3
"""
Nabu MCP Server - Entry point for Model Context Protocol server.

Provides tools for querying and analyzing code graphs via KuzuDB.
"""

import argparse
import logging
import sys
from pathlib import Path

from nabu.mcp.config.nabu_config import NabuConfig, NabuContext
from nabu.mcp.factory_impl import NabuMCPFactorySingleProcess

logger = logging.getLogger("nabu_mcp")





def main() -> None:
    """Main entry point for nabu MCP server."""
    parser = argparse.ArgumentParser(
        description="Nabu MCP Server - Code graph analysis via KuzuDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single codebase (backward compatible)
  %(prog)s --db-path ./nabu.kuzu --repo-path ./src/

  # Multiple codebases
  %(prog)s \
    --codebase my_project:/path/to/code:/path/to/my.kuzu:active \
    --codebase target_lib:/path/to/lib:/path/to/lib.kuzu:reference:false \
    --codebase api_ref:/path/to/api:/path/to/api.kuzu:readonly:false
    
  # Multiple codebases with explicit active
  %(prog)s \
    --codebase my_project:/path/to/code:/path/to/my.kuzu \
    --codebase target_lib:/path/to/lib:/path/to/lib.kuzu \
    --active my_project
        """
    )
    
    # Multi-codebase arguments
    parser.add_argument(
        "--codebase",
        action="append",
        help=(
            "Register a codebase. Format: name:repo_path:db_path[:role[:watch_enabled]]. "
            "Can be specified multiple times. First one is active by default."
        )
    )
    
    parser.add_argument(
        "--active",
        type=str,
        help="Set active codebase (overrides first codebase default)"
    )
    
    # BACKWARD COMPATIBILITY: Keep old flags
    parser.add_argument(
        "--db-path",
        type=Path,
        help="[DEPRECATED] Path to KuzuDB database (use --codebase instead)"
    )
    
    parser.add_argument(
        "--repo-path",
        type=Path,
        help="[DEPRECATED] Path to repository to index (use --codebase instead)"
    )
    
    parser.add_argument(
        "--context",
        type=str,
        default="default",
        help="Context name or path to context YAML file (default: 'default')"
    )
    
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Enable development mode with extra tools and verbose logging"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )

    parser.add_argument(
        "--enable-http",
        action="store_true",
        default=False,
        help="Enable HTTP transport in addition to STDIO (default: STDIO only)"
    )

    parser.add_argument(
        "--http-port",
        type=int,
        default=8000,
        help="HTTP transport port (default: 8000)"
    )

    args = parser.parse_args()
    
    # Validate: must have either --codebase or both --db-path and --repo-path
    if not args.codebase and not (args.db_path and args.repo_path):
        logger.error(
            "Must specify either --codebase (new) or both --db-path and --repo-path (legacy)"
        )
        sys.exit(1)
    
    # Validate codebases exist
    try:
        config = NabuConfig.from_args(args)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Override dual transport settings from CLI
    config.enable_http_transport = args.enable_http
    config.http_port = args.http_port

    # Validate repo paths exist and ensure db directories exist
    for name, cb_config in config.codebases.items():
        if not cb_config.repo_path.exists():
            logger.error(f"Repository path for '{name}' does not exist: {cb_config.repo_path}")
            sys.exit(1)
        
        # Ensure db directory exists
        cb_config.db_path.parent.mkdir(exist_ok=True, parents=True)
    
    # Create factory
    factory = NabuMCPFactorySingleProcess(config)
    
    # Create and run MCP server
    logger.info("Nabu MCP server starting on stdio transport...")
    logger.info(f"Registered codebases: {list(config.codebases.keys())}")
    logger.info(f"Active codebase: {config.active_codebase}")
    
    mcp_server = factory.create_mcp_server(host=args.host, port=args.port)
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
