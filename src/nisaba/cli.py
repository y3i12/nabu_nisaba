"""
CLI utilities and base classes for MCP command-line interfaces.

Provides:
- AutoRegisteringGroup: Class-based command registration pattern
- OutputFormat: Formatting utilities for text/json/yaml output
- Base command group classes for common MCP patterns
- Utility functions for validation and formatting
"""

import sys
from pathlib import Path
from typing import Any, List, Optional, Dict

import click


class AutoRegisteringGroup(click.Group):
    """
    A click.Group subclass that automatically registers any click.Command
    attributes defined on the class into the group.

    After initialization, it inspects its own class for attributes that are
    instances of click.Command (typically created via @click.command) and
    calls self.add_command(cmd) on each. This lets you define your commands
    as static methods on the subclass for IDE-friendly organization without
    manual registration.

    Example:
        class MyCommands(AutoRegisteringGroup):
            def __init__(self):
                super().__init__(name="mygroup", help="My commands")

            @staticmethod
            @click.command("list")
            def list_items():
                click.echo("Listing items...")
    """

    def __init__(self, name: str, help: str):
        super().__init__(name=name, help=help)
        # Scan class attributes for click.Command instances and register them.
        for attr in dir(self.__class__):
            cmd = getattr(self.__class__, attr)
            if isinstance(cmd, click.Command):
                self.add_command(cmd)


class OutputFormat:
    """Utilities for formatting CLI output in different formats."""

    @staticmethod
    def format_json(data: dict, **kwargs) -> str:
        """Format data as JSON with pretty printing."""
        import json
        return json.dumps(data, indent=kwargs.get('indent', 2))

    @staticmethod
    def format_yaml(data: dict, **kwargs) -> str:
        """
        Format data as YAML (requires pyyaml).

        Raises:
            ImportError: If PyYAML is not installed
        """
        try:
            import yaml
            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        except ImportError:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")

    @staticmethod
    def print_header(title: str, width: int = 80, emoji: str = ""):
        """
        Print formatted header with optional emoji and separator.

        Args:
            title: Header title
            width: Width of separator line (default 80)
            emoji: Optional emoji prefix
        """
        prefix = f"{emoji} " if emoji else ""
        click.echo(f"\n{prefix}{title}")
        click.echo("=" * width)

    @staticmethod
    def print_separator(width: int = 80):
        """Print separator line."""
        click.echo("\n" + "=" * width + "\n")

    @staticmethod
    def print_error(message: str, suggestions: Optional[List[str]] = None):
        """
        Print error message with optional suggestions.

        Args:
            message: Error message
            suggestions: Optional list of suggestions to display
        """
        click.echo(f"❌ Error: {message}", err=True)
        if suggestions:
            click.echo("\nSuggestions:", err=True)
            for suggestion in suggestions:
                click.echo(f"   • {suggestion}", err=True)

    @staticmethod
    def print_markdown(content: str, fallback_to_plain: bool = True):
        """
        Print markdown with rich if available, fall back to plain text.

        Args:
            content: Markdown content to print
            fallback_to_plain: If True, fall back to plain text on ImportError

        Raises:
            ImportError: If rich is not installed and fallback_to_plain is False
        """
        try:
            from rich.markdown import Markdown
            from rich.console import Console
            console = Console()
            console.print(Markdown(content))
        except ImportError:
            if fallback_to_plain:
                click.echo(content)
            else:
                raise ImportError("rich not installed. Install with: pip install rich")


class ToolsCommandGroup(AutoRegisteringGroup):
    """
    Base class for 'tools' command groups across MCPs.

    Provides common structure for tool listing and inspection.
    Subclasses should implement tool_registry property.
    """

    def __init__(self):
        super().__init__(
            name="tools",
            help="Commands for discovering and inspecting MCP tools."
        )

    @property
    def tool_registry(self):
        """Override this to return the tool registry instance."""
        raise NotImplementedError("Subclasses must implement tool_registry property")


class ContextCommandGroup(AutoRegisteringGroup):
    """
    Base class for 'context' command groups across MCPs.

    Provides common structure for context management.
    Subclasses should implement context_config property.
    """

    def __init__(self):
        super().__init__(
            name="context",
            help="Commands for managing and inspecting contexts."
        )

    @property
    def context_config(self):
        """Override this to return the context configuration class."""
        raise NotImplementedError("Subclasses must implement context_config property")


class PromptCommandGroup(AutoRegisteringGroup):
    """
    Base class for 'prompt' command groups across MCPs.

    Provides common structure for prompt inspection.
    """

    def __init__(self):
        super().__init__(
            name="prompt",
            help="Commands for inspecting and managing MCP prompts."
        )


def format_tool_list(
    tools: List[str],
    registry: Any,
    format_type: str = "text",
    show_descriptions: bool = True,
    show_tags: bool = True
) -> str:
    """
    Format a list of tools for output.

    Args:
        tools: List of tool names
        registry: Tool registry instance
        format_type: "text", "json", or "names-only"
        show_descriptions: Include tool descriptions (text format only)
        show_tags: Include tool tags (text format only)

    Returns:
        Formatted string ready for output
    """
    if format_type == "names-only":
        return "\n".join(sorted(tools))

    if format_type == "json":
        import json
        tools_data = []
        for name in sorted(tools):
            tool_class = registry.get_tool_class(name)
            tool_info = {"name": name}

            if hasattr(tool_class, 'get_tool_description'):
                tool_info["description"] = tool_class.get_tool_description()
            if hasattr(tool_class, 'is_optional'):
                tool_info["is_optional"] = tool_class.is_optional()
            if hasattr(tool_class, 'is_dev_only'):
                tool_info["is_dev_only"] = tool_class.is_dev_only()
            if hasattr(tool_class, 'is_mutating'):
                tool_info["is_mutating"] = tool_class.is_mutating()

            tools_data.append(tool_info)
        return json.dumps(tools_data, indent=2)

    # Text format
    output_lines = [f"\n📋 Available Tools ({len(tools)} tools)\n", "=" * 80]

    for name in sorted(tools):
        tool_class = registry.get_tool_class(name)
        description = None
        if hasattr(tool_class, 'get_tool_description'):
            description = tool_class.get_tool_description()

        tags = []
        if show_tags:
            if hasattr(tool_class, 'is_optional') and tool_class.is_optional():
                tags.append("optional")
            if hasattr(tool_class, 'is_dev_only') and tool_class.is_dev_only():
                tags.append("dev-only")
            if hasattr(tool_class, 'is_mutating') and tool_class.is_mutating():
                tags.append("mutating")

        tag_str = f" [{', '.join(tags)}]" if tags else ""
        output_lines.append(f"\n  • {name}{tag_str}")

        if show_descriptions and description:
            desc_lines = description.split('\n')
            for line in desc_lines[:3]:  # First 3 lines
                if len(line) > 70:
                    output_lines.append(f"    {line[:70]}...")
                else:
                    output_lines.append(f"    {line}")

    output_lines.append("\n" + "=" * 80 + "\n")
    return "\n".join(output_lines)


def validate_file_or_exit(path: Path, error_message: Optional[str] = None) -> None:
    """
    Validate that a file exists, exit with error if not.

    Args:
        path: Path to validate
        error_message: Custom error message (optional)
    """
    if not path.exists():
        msg = error_message or f"File does not exist: {path}"
        OutputFormat.print_error(msg)
        sys.exit(1)


def validate_dir_or_exit(path: Path, error_message: Optional[str] = None) -> None:
    """
    Validate that a directory exists, exit with error if not.

    Args:
        path: Path to validate
        error_message: Custom error message (optional)
    """
    if not path.exists():
        msg = error_message or f"Directory does not exist: {path}"
        OutputFormat.print_error(msg)
        sys.exit(1)
    if not path.is_dir():
        OutputFormat.print_error(f"Path is not a directory: {path}")
        sys.exit(1)


def format_context_list(contexts: List[Dict[str, Any]], format_type: str = "text") -> str:
    """
    Format a list of contexts for output.

    Args:
        contexts: List of context dictionaries
        format_type: "text" or "json"

    Returns:
        Formatted string ready for output
    """
    if format_type == "json":
        import json
        return json.dumps(contexts, indent=2)

    # Text format
    output_lines = ["\n📁 Available Contexts\n", "=" * 80]

    for ctx in sorted(contexts, key=lambda x: x.get('name', '')):
        name = ctx.get('name', 'unknown')
        description = ctx.get('description', '')
        enabled_tools = ctx.get('enabled_tools_count', 0)
        disabled_tools = ctx.get('disabled_tools_count', 0)

        output_lines.append(f"\n  • {name}")
        if description:
            output_lines.append(f"    {description}")
        output_lines.append(f"    Tools enabled: {enabled_tools}")
        if disabled_tools:
            output_lines.append(f"    Tools disabled: {disabled_tools}")

    output_lines.append("\n" + "=" * 80 + "\n")
    return "\n".join(output_lines)


# ============================================================================
# Nisaba CLI Commands
# ============================================================================

@click.group()
@click.version_option()
def cli():
    """Nisaba - Augments management and proxy for Claude Code."""
    pass


@cli.group()
def augments():
    """Manage augments for dynamic context loading."""
    pass


@augments.command("list")
def augments_list():
    """List all available augments grouped by category."""
    from nisaba.augments import AugmentManager

    # Use default augments directory
    augments_dir = Path.cwd() / ".nisaba" / "augments"
    composed_file = Path.cwd() / ".nisaba" / "nisaba_composed_augments.md"

    if not augments_dir.exists():
        OutputFormat.print_error(
            f"Augments directory not found: {augments_dir}",
            suggestions=[
                "Create augments directory with: mkdir -p .nisaba/augments",
                "Or run from a project with nisaba augments setup"
            ]
        )
        sys.exit(1)

    manager = AugmentManager(augments_dir, composed_file)
    augments_data = manager.show_augments()

    if not augments_data:
        click.echo("No augments available.")
        return

    OutputFormat.print_header("Available Augments", emoji="📚")

    total = sum(len(augment_list) for augment_list in augments_data.values())
    click.echo(f"\n{total} augments across {len(augments_data)} groups:\n")

    for group_name in sorted(augments_data.keys()):
        click.echo(f"\n  {group_name}:")
        for augment_name in sorted(augments_data[group_name]):
            click.echo(f"    • {augment_name}")

    click.echo("\n" + "=" * 80 + "\n")


@augments.command("activate")
@click.argument("patterns", nargs=-1, required=True)
@click.option("--exclude", multiple=True, help="Patterns to exclude")
def augments_activate(patterns, exclude):
    """Activate augments matching patterns."""
    from nisaba.augments import AugmentManager

    augments_dir = Path.cwd() / ".nisaba" / "augments"
    composed_file = Path.cwd() / ".nisaba" / "nisaba_composed_augments.md"

    if not augments_dir.exists():
        OutputFormat.print_error(f"Augments directory not found: {augments_dir}")
        sys.exit(1)

    manager = AugmentManager(augments_dir, composed_file)

    try:
        result = manager.activate_augments(list(patterns), list(exclude))

        click.echo(f"✅ Activated {len(result['loaded'])} augments")

        if result['loaded']:
            click.echo("\nLoaded:")
            for augment in result['loaded']:
                click.echo(f"  • {augment}")

        if result.get('dependencies'):
            click.echo(f"\nDependencies ({len(result['dependencies'])}):")
            for augment in result['dependencies']:
                click.echo(f"  • {augment}")

        click.echo(f"\n📝 Augments written to: {composed_file}")

    except Exception as e:
        OutputFormat.print_error(f"Failed to activate augments: {e}")
        sys.exit(1)


@augments.command("deactivate")
@click.argument("patterns", nargs=-1, required=True)
def augments_deactivate(patterns):
    """Deactivate augments matching patterns."""
    from nisaba.augments import AugmentManager

    augments_dir = Path.cwd() / ".nisaba" / "augments"
    composed_file = Path.cwd() / ".nisaba" / "nisaba_composed_augments.md"

    if not augments_dir.exists():
        OutputFormat.print_error(f"Augments directory not found: {augments_dir}")
        sys.exit(1)

    manager = AugmentManager(augments_dir, composed_file)

    try:
        result = manager.deactivate_augments(list(patterns))

        click.echo(f"✅ Deactivated {len(result['unloaded'])} augments")

        if result['unloaded']:
            click.echo("\nUnloaded:")
            for augment in result['unloaded']:
                click.echo(f"  • {augment}")

        click.echo(f"\n📝 Augments written to: {composed_file}")

    except Exception as e:
        OutputFormat.print_error(f"Failed to deactivate augments: {e}")
        sys.exit(1)


@cli.group()
def servers():
    """MCP server discovery and management."""
    pass


@servers.command("list")
def servers_list():
    """List active MCP servers."""
    from nisaba.mcp_registry import MCPServerRegistry

    registry_path = Path.cwd() / ".nisaba" / "mcp_servers.json"

    if not registry_path.exists():
        click.echo("No MCP servers registered.")
        return

    try:
        registry = MCPServerRegistry(registry_path)
        servers = registry.list_servers()

        if not servers:
            click.echo("No active MCP servers found.")
            return

        OutputFormat.print_header(f"Active MCP Servers ({len(servers)})", emoji="📡")

        for server_id, info in servers.items():
            click.echo(f"\n  • {info['name']} (PID: {info['pid']})")
            if info.get('http', {}).get('enabled'):
                click.echo(f"    HTTP: {info['http']['url']}")
            click.echo(f"    Started: {info['started_at']}")
            click.echo(f"    CWD: {info['cwd']}")

        click.echo("\n" + "=" * 80 + "\n")

    except Exception as e:
        OutputFormat.print_error(f"Error reading registry: {e}")
        sys.exit(1)


# Register claude wrapper command
from nisaba.wrapper import create_claude_wrapper_command
cli.add_command(create_claude_wrapper_command())


if __name__ == "__main__":
    cli()
