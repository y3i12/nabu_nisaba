"""
Command-line interface for nabu MCP introspection and utilities.

Provides commands for discovering tools, inspecting schemas, and debugging.
"""

import click
import json
import sys
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

from nisaba import ToolRegistry
from nisaba.cli import (
    OutputFormat,
    format_tool_list,
    format_context_list,
    validate_file_or_exit,
    validate_dir_or_exit
)
from nabu.mcp.config.nabu_config import NabuConfig, NabuContext
from nabu.mcp.tools.base import NabuTool


@click.group()
@click.version_option()
def cli():
    """Nabu MCP command-line interface for tool introspection and utilities."""
    pass


@cli.group()
def prompt():
    """Commands for inspecting MCP system prompts."""
    pass


@prompt.command("show")
@click.option(
    "--db-path",
    type=click.Path(),
    default=None,
    help="Path to KuzuDB database (optional, uses generic examples if not provided)"
)
@click.option(
    "--repo-path",
    type=click.Path(),
    default=".",
    help="Repository path (default: current directory)"
)
@click.option(
    "--context",
    default="default",
    help="Context name or path to context YAML file (default: 'default')"
)
@click.option(
    "--format",
    type=click.Choice(["text", "raw"]),
    default="text",
    help="Output format: 'text' for pretty printing, 'raw' for plain markdown"
)
@click.option(
    "--dev-mode",
    is_flag=True,
    help="Enable dev-only tools in the prompt"
)
def prompt_show(db_path: str, repo_path: str, context: str, format: str, dev_mode: bool):
    """
    Display the system prompt that would be sent to the LLM.

    This command shows the complete MCP instructions including tool
    documentation, schema information, and workflow examples.

    Examples:
        nabu prompt show
        nabu prompt show --db-path ./nabu.kuzu
        nabu prompt show --context minimal
        nabu prompt show --format raw > prompt.md
        nabu prompt show --dev-mode
    """
    from nabu.mcp.factory_impl import NabuMCPFactorySingleProcess

    try:
        # Load context
        contexts_dir = Path(__file__).parent / "config" / "contexts"
        try:
            if context.endswith(".yml") or context.endswith(".yaml"):
                ctx = NabuContext.from_yaml(Path(context))
            else:
                ctx = NabuContext.load(context, contexts_dir=contexts_dir)
        except FileNotFoundError as e:
            click.echo(f"❌ Error: Context '{context}' not found", err=True)
            click.echo(f"\nAvailable contexts:", err=True)
            if contexts_dir.exists():
                for ctx_file in sorted(contexts_dir.glob("*.yml")):
                    click.echo(f"   • {ctx_file.stem}", err=True)
            sys.exit(1)

        # Create config
        config = NabuConfig(
            db_path=Path(db_path) if db_path else None,
            repo_path=Path(repo_path),
            context=ctx,
            dev_mode=dev_mode,
            log_level="ERROR"  # Suppress logs during prompt generation
        )

        # Suppress logging during prompt generation
        #logging.getLogger("nabu").setLevel(logging.ERROR)
        #logging.getLogger("nisaba").setLevel(logging.ERROR)

        # Create factory (but don't start server)
        click.echo("🔄 Generating system prompt...", err=True)
        factory = NabuMCPFactorySingleProcess(config)

        # Generate instructions
        instructions = factory._get_initial_instructions()

        click.echo("✅ Prompt generated successfully\n", err=True)

        # Output based on format
        if format == "raw":
            # Raw markdown output (suitable for piping/saving)
            click.echo(instructions)
        else:
            # Use nisaba's markdown printer with fallback
            OutputFormat.print_markdown(instructions, fallback_to_plain=True)

        # Show metadata
        if format == "text":
            click.echo("\n" + "=" * 80, err=True)
            click.echo(f"📊 Prompt Statistics:", err=True)
            click.echo(f"   • Length: {len(instructions):,} characters", err=True)
            click.echo(f"   • Approx tokens: {len(instructions) // 4:,} (rough estimate)", err=True)
            click.echo(f"   • Context: {ctx.name}", err=True)
            click.echo(f"   • Enabled tools: {len(ctx.enabled_tools)}", err=True)
            if db_path:
                click.echo(f"   • Database: {db_path}", err=True)
            else:
                click.echo(f"   • Database: Not provided (using generic examples)", err=True)
            click.echo("=" * 80 + "\n", err=True)

    except Exception as e:
        click.echo(f"\n❌ Error generating prompt: {e}", err=True)
        logging.getLogger(__name__).error(f"Prompt generation failed: {e}", exc_info=True)
        sys.exit(1)


@cli.group()
def tools():
    """Commands for discovering and inspecting MCP tools."""
    pass


@tools.command("list")
@click.option(
    "--all", "-a", 
    "show_all", 
    is_flag=True, 
    help="Include optional tools"
)
@click.option(
    "--dev", 
    is_flag=True, 
    help="Include dev-only tools"
)
@click.option(
    "--optional-only",
    is_flag=True,
    help="Show only optional tools"
)
@click.option(
    "--format",
    type=click.Choice(["text", "json", "names-only"]),
    default="text",
    help="Output format"
)
def tools_list(show_all: bool, dev: bool, optional_only: bool, format: str):
    """
    List available nabu MCP tools.
    
    Examples:
        nabu tools list
        nabu tools list --all
        nabu tools list --optional-only
        nabu tools list --format json
        nabu tools list --format names-only
    """
    registry = ToolRegistry(tool_base_class=NabuTool, module_prefix="nabu.mcp.tools")
    
    # Determine which tools to show
    if optional_only:
        tool_names = registry.get_optional_tool_names()
    elif show_all:
        tool_names = registry.get_all_tool_names()
    else:
        tool_names = registry.get_default_enabled_tool_names()
    
    # Filter dev tools if not requested
    if not dev:
        dev_tools = set(registry.get_dev_only_tool_names())
        tool_names = [name for name in tool_names if name not in dev_tools]
    
    # Sort alphabetically
    tool_names = sorted(tool_names)
    
    # Format output using nisaba utility
    output = format_tool_list(
        tools=tool_names,
        registry=registry,
        format_type=format,
        show_descriptions=True,
        show_tags=True
    )
    click.echo(output)

    if format == "text":
        click.echo(f"ℹ️  Use 'nabu tools info <name>' for detailed information about a specific tool\n")


@tools.command("info")
@click.argument("tool_name")
@click.option(
    "--format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format"
)
@click.option(
    "--show-examples",
    is_flag=True,
    help="Show usage examples if available"
)
def tools_info(tool_name: str, format: str, show_examples: bool):
    """
    Show detailed information about a specific tool.
    
    Examples:
        nabu tools info query
        nabu tools info fts_query --format json
        nabu tools info reindex --show-examples
    """
    registry = ToolRegistry(tool_base_class=NabuTool, module_prefix="nabu.mcp.tools")

    if not registry.is_valid_tool_name(tool_name):
        OutputFormat.print_error(
            f"Unknown tool '{tool_name}'",
            suggestions=[f"Available tools: {', '.join(sorted(registry.get_all_tool_names()))}"]
        )
        sys.exit(1)
    
    tool_class = registry.get_tool_class(tool_name)
    schema = tool_class.get_tool_schema()
    
    # JSON format
    if format == "json":
        output = {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["parameters"],
            "metadata": {
                "is_optional": tool_class.is_optional(),
                "is_dev_only": tool_class.is_dev_only(),
                "is_mutating": tool_class.is_mutating()
            }
        }
        click.echo(json.dumps(output, indent=2))
        return
    
    # YAML format
    if format == "yaml":
        try:
            import yaml
            output = {
                "name": schema["name"],
                "description": schema["description"],
                "parameters": schema["parameters"],
                "metadata": {
                    "is_optional": tool_class.is_optional(),
                    "is_dev_only": tool_class.is_dev_only(),
                    "is_mutating": tool_class.is_mutating()
                }
            }
            click.echo(yaml.dump(output, default_flow_style=False, sort_keys=False))
        except ImportError:
            click.echo("❌ Error: PyYAML not installed. Install with: pip install pyyaml", err=True)
            sys.exit(1)
        return
    
    # Text format (default)
    OutputFormat.print_header(f"Tool: {schema['name']}", emoji="🔧")
    
    # Description
    click.echo(f"\n📝 Description:")
    description = schema['description']
    for line in description.split('\n'):
        click.echo(f"   {line}")
    
    # Metadata tags
    tags = []
    if tool_class.is_optional():
        tags.append("Optional (disabled by default)")
    if tool_class.is_dev_only():
        tags.append("Dev-only (requires --dev-mode)")
    if tool_class.is_mutating():
        tags.append("Mutating (modifies database)")
    
    if tags:
        click.echo(f"\n🏷️  Tags:")
        for tag in tags:
            click.echo(f"   • {tag}")
    
    # Parameters
    params = schema['parameters']
    if params['properties']:
        click.echo(f"\n📥 Parameters:")
        required_params = set(params.get('required', []))
        
        for param_name, param_spec in params['properties'].items():
            is_required = param_name in required_params
            required_str = "required" if is_required else "optional"
            
            param_type = param_spec.get('type', 'any')
            default = param_spec.get('default')
            default_str = f", default={repr(default)}" if default is not None else ""
            
            click.echo(f"\n   • {param_name} ({param_type}, {required_str}{default_str})")
            
            param_desc = param_spec.get('description', '')
            if param_desc:
                for line in param_desc.split('\n'):
                    click.echo(f"     {line}")
    else:
        click.echo(f"\n📥 Parameters: None")
    
    click.echo("\n" + "=" * 80 + "\n")


@cli.group()
def context():
    """Commands for managing and inspecting contexts."""
    pass


@context.command("list")
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format"
)
def context_list(format: str):
    """
    List available contexts.
    
    Examples:
        nabu context list
        nabu context list --format json
    """
    contexts_dir = Path(__file__).parent / "config" / "contexts"

    if not contexts_dir.exists():
        OutputFormat.print_error("Contexts directory not found")
        sys.exit(1)

    context_files = list(contexts_dir.glob("*.yml"))

    # Build contexts list
    contexts_data = []
    for ctx_file in sorted(context_files):
        try:
            ctx = NabuContext.from_yaml(ctx_file)
            contexts_data.append({
                "name": ctx.name,
                "description": ctx.description,
                "enabled_tools_count": len(ctx.enabled_tools),
                "disabled_tools_count": len(ctx.disabled_tools)
            })
        except Exception as e:
            contexts_data.append({
                "name": ctx_file.stem,
                "error": str(e)
            })

    # Format output using nisaba utility
    output = format_context_list(contexts_data, format_type=format)
    click.echo(output)


@context.command("show")
@click.argument("context_name")
@click.option(
    "--format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format"
)
def context_show(context_name: str, format: str):
    """
    Show details of a specific context.
    
    Examples:
        nabu context show default
        nabu context show development --format json
    """
    contexts_dir = Path(__file__).parent / "config" / "contexts"

    try:
        ctx = NabuContext.load(context_name, contexts_dir=contexts_dir)
    except FileNotFoundError as e:
        OutputFormat.print_error(str(e))
        sys.exit(1)
    
    if format == "json":
        output = {
            "name": ctx.name,
            "description": ctx.description,
            "enabled_tools": sorted(list(ctx.enabled_tools)),
            "disabled_tools": sorted(list(ctx.disabled_tools)),
            "tool_config_overrides": ctx.tool_config_overrides
        }
        click.echo(json.dumps(output, indent=2))
        return
    
    if format == "yaml":
        try:
            import yaml
            output = {
                "name": ctx.name,
                "description": ctx.description,
                "enabled_tools": sorted(list(ctx.enabled_tools)),
                "disabled_tools": sorted(list(ctx.disabled_tools)),
                "tool_config_overrides": ctx.tool_config_overrides
            }
            click.echo(yaml.dump(output, default_flow_style=False, sort_keys=False))
        except ImportError:
            click.echo("❌ Error: PyYAML not installed", err=True)
            sys.exit(1)
        return
    
    # Text format
    OutputFormat.print_header(f"Context: {ctx.name}", emoji="📋")
    
    if ctx.description:
        click.echo(f"\n📝 Description:")
        click.echo(f"   {ctx.description}")
    
    click.echo(f"\n✅ Enabled Tools ({len(ctx.enabled_tools)}):")
    for tool in sorted(ctx.enabled_tools):
        click.echo(f"   • {tool}")
    
    if ctx.disabled_tools:
        click.echo(f"\n❌ Disabled Tools ({len(ctx.disabled_tools)}):")
        for tool in sorted(ctx.disabled_tools):
            click.echo(f"   • {tool}")
    
    if ctx.tool_config_overrides:
        click.echo(f"\n⚙️  Tool Config Overrides:")
        for tool, config in ctx.tool_config_overrides.items():
            click.echo(f"   • {tool}: {config}")

    click.echo("\n" + "=" * 80 + "\n")


@cli.group()
def db():
    """Commands for database operations."""
    pass


@db.command("reindex")
@click.option(
    "--db-path",
    type=click.Path(),
    required=True,
    help="Path to KuzuDB database file"
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True),
    required=True,
    help="Path to repository to index"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Log level for reindex operation"
)
def db_reindex(db_path: str, repo_path: str, log_level: str):
    """
    Rebuild the KuzuDB database from scratch.
    
    This performs a complete re-indexing of the codebase by parsing
    all files and recreating the database. Use with caution as this
    will replace the existing database.
    
    Examples:
        nabu db reindex --db-path ./nabu.kuzu --repo-path .
        nabu db reindex --db-path ./nabu.kuzu --repo-path /path/to/code --log-level DEBUG
    """
    from pathlib import Path
    import nabu.main
    from nabu.db import KuzuConnectionManager
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    db_path_obj = Path(db_path)
    repo_path_obj = Path(repo_path)

    # Validate paths
    validate_dir_or_exit(repo_path_obj, f"Repository path does not exist: {repo_path}")

    if db_path_obj.is_dir():
        OutputFormat.print_error(f"Database path must be a file, not a directory: {db_path}")
        sys.exit(1)
    
    # Ensure db directory exists
    db_path_obj.parent.mkdir(exist_ok=True, parents=True)
    
    try:
        click.echo(f"🔄 Reindexing repository: {repo_path_obj.resolve()}")
        click.echo(f"📊 Target database: {db_path_obj}")
        
        # Remove existing database if it exists
        if db_path_obj.exists():
            db_path_obj.unlink()
            db_path_obj.with_suffix(".wal").unlink(missing_ok=True)
            db_path_obj.with_suffix(".wal.shadow").unlink(missing_ok=True)
            logger.info("Removed existing database file")
        
        # Start reindex
        start_time = time.time()
        nabu.main.parse_codebase(
            codebase_path=str(repo_path_obj.resolve()),
            output_db=str(db_path_obj)
        )
        elapsed = time.time() - start_time
        
        # Get stats
        db_manager = KuzuConnectionManager.get_instance(str(db_path_obj))
        result = db_manager.execute("MATCH (n:Frame) RETURN n.type as type, count(*) as count")

        click.echo(f"\n✅ Database reindexed successfully in {elapsed:.2f}s")
        click.echo(f"📁 Database location: {db_path_obj.resolve()}")

        if result:
            df = result.get_as_df()
            click.echo(f"\n📊 Frame Statistics:")
            total_frames = 0
            for _, row in df.iterrows():
                count = int(row['count'])
                total_frames += count
                click.echo(f"   • {row['type']}: {count}")
            click.echo(f"\n   Total frames: {total_frames}")

        db_manager.close()

    except Exception as e:
        click.echo(f"\n❌ Error during reindex: {e}", err=True)
        logger.error(f"Reindex failed: {e}", exc_info=True)
        sys.exit(1)


@db.command("health-check")
@click.option(
    "--db-path",
    type=click.Path(exists=True),
    required=True,
    help="Path to KuzuDB database file"
)
def db_health_check(db_path: str):
    """
    Perform health check on the database.

    Tests database connection and query execution to verify
    the database is accessible and functioning correctly.

    Examples:
        nabu db health-check --db-path ./nabu.kuzu
    """
    from pathlib import Path
    from nabu.db import KuzuConnectionManager

    db_path_obj = Path(db_path)

    validate_file_or_exit(db_path_obj, f"Database does not exist: {db_path}")
    
    try:
        click.echo(f"🏥 Running health check on: {db_path_obj.resolve()}")
        
        db_manager = KuzuConnectionManager.get_instance(str(db_path_obj))
        result = db_manager.execute("MATCH (n:Frame) RETURN count(n) as count LIMIT 1")
        
        if result:
            df = result.get_as_df()
            frame_count = int(df.iloc[0]['count'])

            click.echo(f"\n✅ Database is healthy")
            click.echo(f"   • Connection: OK")
            click.echo(f"   • Frame count: {frame_count}")
            click.echo(f"   • Database path: {db_path_obj.resolve()}")
        else:
            click.echo(f"⚠️  Database accessible but returned no results", err=True)
            sys.exit(1)

        db_manager.close()

    except Exception as e:
        OutputFormat.print_error(
            f"Health check failed: {e}",
            suggestions=[
                "Verify database file is not corrupted",
                f"Try running: nabu db reindex --db-path {db_path} --repo-path <path>"
            ]
        )
        sys.exit(1)


@db.command("stats")
@click.option(
    "--db-path",
    type=click.Path(exists=True),
    required=True,
    help="Path to KuzuDB database file"
)
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format"
)
def db_stats(db_path: str, format: str):
    """
    Show database statistics.

    Display detailed statistics about the database including
    frame counts by type, edge counts, and other metadata.

    Examples:
        nabu db stats --db-path ./nabu.kuzu
        nabu db stats --db-path ./nabu.kuzu --format json
    """
    from pathlib import Path
    from nabu.db import KuzuConnectionManager

    db_path_obj = Path(db_path)

    validate_file_or_exit(db_path_obj, f"Database does not exist: {db_path}")
    
    try:
        db_manager = KuzuConnectionManager.get_instance(str(db_path_obj))
        
        # Get frame statistics
        frame_result = db_manager.execute("MATCH (n:Frame) RETURN n.type as type, count(*) as count")

        # Get edge statistics - count each relationship type separately
        edge_types = ["CONTAINS", "IMPORTS", "CALLS", "INHERITS", "IMPLEMENTS", "USES"]
        edge_counts = {}
        for edge_type in edge_types:
            try:
                result = db_manager.execute(f"MATCH ()-[r:{edge_type}]->() RETURN count(*) as count")
                if result:
                    df = result.get_as_df()
                    count = int(df.iloc[0]['count'])
                    if count > 0:
                        edge_counts[edge_type] = count
            except:
                pass  # Edge type doesn't exist in this database
        
        stats_data = {
            "database_path": str(db_path_obj.resolve()),
            "frames": {},
            "edges": edge_counts
        }

        total_frames = 0
        if frame_result:
            df = frame_result.get_as_df()
            for _, row in df.iterrows():
                count = int(row['count'])
                stats_data["frames"][row['type']] = count
                total_frames += count

        stats_data["total_frames"] = total_frames
        stats_data["total_edges"] = sum(edge_counts.values())
        
        # Output
        if format == "json":
            click.echo(json.dumps(stats_data, indent=2))
        else:
            OutputFormat.print_header("Database Statistics", emoji="📊")
            click.echo(f"\n📁 Database: {stats_data['database_path']}")

            click.echo(f"\n📦 Frames by Type (Total: {total_frames}):")
            for frame_type, count in sorted(stats_data["frames"].items(), key=lambda x: -x[1]):
                click.echo(f"   • {frame_type}: {count}")

            click.echo(f"\n🔗 Edges by Type (Total: {stats_data['total_edges']}):")
            for edge_type, count in sorted(stats_data["edges"].items(), key=lambda x: -x[1]):
                click.echo(f"   • {edge_type}: {count}")

            click.echo("\n" + "=" * 80 + "\n")
        
        db_manager.close()

    except Exception as e:
        OutputFormat.print_error(f"Error retrieving statistics: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
