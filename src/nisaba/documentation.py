"""Tool documentation generation for MCP servers."""

from typing import Callable, Optional, List, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from nisaba.registry import ToolRegistry


class ToolDocumentationGenerator:
    """
    Generic tool documentation generator for MCP servers.

    Generates markdown documentation for all enabled tools,
    with customizable categorization and formatting.
    """

    def __init__(
        self,
        registry: "ToolRegistry",
        enabled_tools: List[str],
        categorize_fn: Optional[Callable[[str, type], str]] = None
    ):
        """
        Initialize documentation generator.

        Args:
            registry: Tool registry to get tool classes
            enabled_tools: List of enabled tool names
            categorize_fn: Optional function to categorize tools
                          Signature: (tool_name, tool_class) -> category_name
                          Default: Single "Tools" category
        """
        self.registry = registry
        self.enabled_tools = enabled_tools
        self.categorize_fn = categorize_fn or self._default_categorize

    def _default_categorize(self, tool_name: str, tool_class: type) -> str:
        """Default categorization: single 'Tools' category."""
        return "default"

    def generate_documentation(self) -> str:
        """
        Generate markdown documentation for all enabled tools.

        Returns:
            Markdown-formatted tool documentation
        """
        # Categorize tools
        categories: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}

        for tool_name in self.enabled_tools:
            tool_class = self.registry.get_tool_class(tool_name)
            schema = tool_class.get_tool_schema()

            category = self.categorize_fn(tool_name, tool_class)
            if category not in categories:
                categories[category] = []
            categories[category].append((tool_name, schema))

        # Build markdown
        lines = ["## Available Tools\n"]

        # Generate documentation for each category
        for category, tools in categories.items():
            if category != "default":
                # Format category name (capitalize first letter of each word)
                category_title = " ".join(word.capitalize() for word in category.split("_"))
                lines.append(f"### {category_title}\n")

            for tool_name, schema in tools:
                tool_class = self.registry.get_tool_class(tool_name)
                pitch = tool_class.get_tool_pitch()

                if pitch:
                    # Use pitch with optional emoji
                    meta = schema.get('meta', {})
                    emoji = meta.get('emoji', '')
                    emoji_str = f"{emoji} " if emoji else ""
                    lines.append(f"**`{tool_name}`** {emoji_str}**{pitch}**\n")
                else:
                    # Fallback to first line of description
                    description = schema.get('description', '')
                    first_line = description.split('\n')[0] if description else "No description"
                    lines.append(f"**`{tool_name}`** - {first_line}\n")

                # Optionally add "when to use" hint
                if 'meta' in schema and 'when' in schema['meta']:
                    lines.append(f"*When to use:* {schema['meta']['when']}\n")

                lines.append("")

        # Generate additional sections for tool examples, tips, and patterns
        all_tools = []
        for tools in categories.values():
            all_tools.extend(tools)

        # Tool Usage Examples section
        examples_found = False
        examples_lines = []
        for tool_name, schema in all_tools:
            tool_class = self.registry.get_tool_class(tool_name)
            examples = tool_class.get_tool_examples()
            if examples:
                if not examples_found:
                    examples_lines.append("## Tool Usage Examples\n")
                    examples_found = True
                examples_lines.append(f"### {tool_name}\n")
                examples_lines.append(examples)
                examples_lines.append("")

        if examples_found:
            lines.extend(examples_lines)

        # Tool-Specific Tips section
        tips_found = False
        tips_lines = []
        for tool_name, schema in all_tools:
            tool_class = self.registry.get_tool_class(tool_name)
            tips = tool_class.get_tool_tips()
            if tips:
                if not tips_found:
                    tips_lines.append("## Tool-Specific Tips\n")
                    tips_found = True
                tips_lines.append(f"### {tool_name}\n")
                tips_lines.append(tips)
                tips_lines.append("")

        if tips_found:
            lines.extend(tips_lines)

        # Common Patterns section
        patterns_found = False
        patterns_lines = []
        for tool_name, schema in all_tools:
            tool_class = self.registry.get_tool_class(tool_name)
            patterns = tool_class.get_tool_patterns()
            if patterns:
                if not patterns_found:
                    patterns_lines.append("## Common Patterns\n")
                    patterns_found = True
                patterns_lines.append(f"### {tool_name}\n")
                patterns_lines.append(patterns)
                patterns_lines.append("")

        if patterns_found:
            lines.extend(patterns_lines)

        return "\n".join(lines)

    @staticmethod
    def format_tool_parameters(parameters: dict) -> str:
        """
        Format tool parameters as markdown.

        Args:
            parameters: Tool parameters dict from schema

        Returns:
            Markdown-formatted parameter documentation
        """
        if not parameters.get('properties'):
            return "*(No parameters)*\n"

        lines = ["**Parameters:**"]
        props = parameters['properties']
        required = parameters.get('required', [])

        for param_name, param_info in props.items():
            param_type = param_info.get('type', 'any')
            param_desc = param_info.get('description', '')
            is_required = param_name in required
            default = param_info.get('default')

            req_marker = "*(required)*" if is_required else f"*(optional, default: {default})*"

            lines.append(f"- `{param_name}` ({param_type}) {req_marker}: {param_desc}")

        return "\n".join(lines) + "\n"
