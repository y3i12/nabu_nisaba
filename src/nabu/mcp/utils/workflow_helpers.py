"""
Utility functions for workflow automation tools.

Provides common functionality for risk assessment, visualization generation,
and relevance ranking used across workflow tools.
"""

from typing import Any, Dict, List, Tuple, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def calculate_risk_score(
    centrality_score: float,
    core_score: float,
    coverage_score: float,
    external_score: float,
    weights: Dict[str, float] = None
) -> Tuple[float, str]:
    """
    Calculate composite risk score and tier.
    
    Args:
        centrality_score: How connected is this element? (0.0-1.0)
        core_score: Is this in critical path? (0.0-1.0)
        coverage_score: Test coverage quality (0.0-1.0)
        external_score: External dependencies (0.0-1.0)
        weights: Optional custom weights for factors (default: centrality=0.35, core=0.35, coverage=0.20, external=0.10)
        
    Returns:
        Tuple of (composite_score, risk_tier)
    """
    if weights is None:
        weights = {
            "centrality": 0.35,
            "core": 0.35,
            "coverage": 0.20,
            "external": 0.10
        }
    
    # Calculate weighted composite
    composite = (
        weights["centrality"] * centrality_score +
        weights["core"] * core_score +
        weights["coverage"] * coverage_score +
        weights["external"] * external_score
    )
    
    # Map to tier
    if composite > 0.75:
        tier = "HIGH"
    elif composite > 0.5:
        tier = "MEDIUM-HIGH"
    elif composite > 0.3:
        tier = "MEDIUM"
    else:
        tier = "LOW"
    
    return round(composite, 2), tier


def generate_mermaid_graph(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    graph_type: str = 'TD',
    max_nodes: int = 20
) -> str:
    """
    Generate Mermaid diagram from graph data.
    
    Args:
        nodes: List of node dicts with 'id', 'label', optional 'style'
        edges: List of edge dicts with 'from', 'to', optional 'label'
        graph_type: Mermaid graph direction ('TD', 'LR', 'BT', 'RL')
        max_nodes: Maximum nodes to include (truncate if exceeded)
        
    Returns:
        Mermaid diagram string
    """
    if len(nodes) > max_nodes:
        logger.warning(f"Truncating graph: {len(nodes)} nodes > {max_nodes} max")
        nodes = nodes[:max_nodes]
    
    lines = [f"graph {graph_type}"]
    
    # Create node ID mapping
    node_id_map = {}
    for i, node in enumerate(nodes):
        node_id = f"N{i}"
        node_id_map[node['id']] = node_id
        
        label = node.get('label', str(node['id']))
        # Escape special characters in labels
        label = label.replace('"', '\\"').replace('[', '\\[').replace(']', '\\]')
        
        # Add node definition
        lines.append(f"    {node_id}[\"{label}\"]")
        
        # Add style if specified
        if 'style' in node:
            style = node['style']
            if style == 'target':
                lines.append(f"    style {node_id} fill:#f9f,stroke:#333,stroke-width:3px")
            elif style == 'high_risk':
                lines.append(f"    style {node_id} fill:#faa,stroke:#333")
            elif style == 'medium_risk':
                lines.append(f"    style {node_id} fill:#ffa,stroke:#333")
            elif style == 'low_risk':
                lines.append(f"    style {node_id} fill:#afa,stroke:#333")
    
    # Add edges
    for edge in edges:
        from_id = edge.get('from')
        to_id = edge.get('to')
        
        # Skip if nodes not in map (truncated)
        if from_id not in node_id_map or to_id not in node_id_map:
            continue
        
        from_node = node_id_map[from_id]
        to_node = node_id_map[to_id]
        
        if 'label' in edge:
            label = edge['label']
            lines.append(f"    {from_node} -->|{label}| {to_node}")
        else:
            lines.append(f"    {from_node} --> {to_node}")
    
    return "\n".join(lines)


def rank_by_relevance(
    frames: List[Dict[str, Any]],
    keywords: List[str],
    centrality_data: Dict[str, float] = None
) -> List[Tuple[Dict[str, Any], float]]:
    """
    Rank frames by relevance to keywords.
    
    Scoring factors:
    - Keyword matching in name (40%)
    - Centrality in call graph (30%)
    - Content keyword matching (20%)
    - File path matching (10%)
    
    Args:
        frames: List of frame dictionaries
        keywords: List of keywords to match against
        centrality_data: Optional dict mapping frame IDs to centrality scores
        
    Returns:
        List of (frame, relevance_score) tuples, sorted by score descending
    """
    if centrality_data is None:
        centrality_data = {}
    
    # Normalize keywords to lowercase
    keywords_lower = [kw.lower() for kw in keywords]
    
    scored_frames = []
    
    for frame in frames:
        score = 0.0
        
        # Factor 1: Keyword matching in name (40%)
        name = frame.get('name', '').lower()
        name_words = name.replace('_', ' ').split()
        name_matches = sum(1 for kw in keywords_lower if kw in name_words or kw in name)
        if keywords_lower:
            score += 0.4 * (name_matches / len(keywords_lower))
        
        # Factor 2: Centrality score (30%)
        frame_id = frame.get('id', '')
        centrality = centrality_data.get(frame_id, 0.0)
        score += 0.3 * centrality
        
        # Factor 3: Content keyword matching (20%)
        content = frame.get('content', '').lower()
        if content:
            content_matches = sum(1 for kw in keywords_lower if kw in content)
            if keywords_lower:
                score += 0.2 * min(1.0, content_matches / len(keywords_lower))
        
        # Factor 4: File path matching (10%)
        file_path = frame.get('file_path', '').lower()
        if any(kw in file_path for kw in keywords_lower):
            score += 0.1
        
        scored_frames.append((frame, score))
    
    # Sort by score descending
    scored_frames.sort(key=lambda x: x[1], reverse=True)
    
    return scored_frames


def calculate_centrality_score(caller_count: int, max_callers: int = 20) -> float:
    """
    Calculate normalized centrality score based on caller count.
    
    Args:
        caller_count: Number of callers for this element
        max_callers: Maximum expected callers (for normalization)
        
    Returns:
        Centrality score (0.0-1.0)
    """
    return min(1.0, caller_count / max_callers)


def calculate_core_score(file_path: str, core_patterns: List[str] = None) -> float:
    """
    Calculate score indicating if element is in core/critical path.
    
    Args:
        file_path: Path to the file
        core_patterns: Patterns indicating core code (default: ['core/', 'mcp/', 'main'])
        
    Returns:
        Core score (0.0-1.0)
    """
    if core_patterns is None:
        core_patterns = ['core/', 'mcp/', 'main', 'server/', 'api/']
    
    file_path_lower = file_path.lower()
    
    # Check for core patterns
    core_matches = sum(1 for pattern in core_patterns if pattern in file_path_lower)
    
    # Check for peripheral patterns (negative indicators)
    peripheral_patterns = ['test/', 'tests/', 'util/', 'utils/', 'helper/', 'helpers/']
    peripheral_matches = sum(1 for pattern in peripheral_patterns if pattern in file_path_lower)
    
    if peripheral_matches > 0:
        return 0.2  # Low score for peripheral code
    
    if core_matches > 0:
        return 0.9  # High score for core code
    
    return 0.5  # Medium score for ambiguous


def extract_code_snippet(
    content: str,
    start_line: int,
    end_line: int,
    context_lines: int = 3
) -> str:
    """
    Extract code snippet with optional context lines.
    
    Args:
        content: Full file content
        start_line: Start line (1-indexed)
        end_line: End line (1-indexed, inclusive)
        context_lines: Number of context lines before/after
        
    Returns:
        Code snippet string
    """
    lines = content.split('\n')
    
    # Adjust to 0-indexed
    start_idx = max(0, start_line - 1 - context_lines)
    end_idx = min(len(lines), end_line + context_lines)
    
    snippet_lines = lines[start_idx:end_idx]
    
    # Add line numbers
    numbered_lines = []
    for i, line in enumerate(snippet_lines, start=start_idx + 1):
        numbered_lines.append(f"{i:4d} | {line}")
    
    return '\n'.join(numbered_lines)


def find_test_files_for_class(
    class_name: str,
    project_root: Path,
    test_patterns: List[str] = None
) -> List[Path]:
    """
    Find test files related to a class using file patterns.
    
    Args:
        class_name: Name of the class
        project_root: Root directory of the project
        test_patterns: Test file patterns (default: standard patterns)
        
    Returns:
        List of test file paths
    """
    if test_patterns is None:
        test_patterns = [
            f"test_{class_name.lower()}.py",
            f"test*{class_name.lower()}*.py",
            f"*_test_{class_name.lower()}.py",
            f"{class_name.lower()}_test.py"
        ]
    
    test_files = []
    
    # Search in common test directories
    test_dirs = [
        project_root / "test",
        project_root / "tests",
        project_root / "src" / "test",
        project_root / "src" / "tests"
    ]
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
        
        for pattern in test_patterns:
            matching_files = list(test_dir.rglob(pattern))
            test_files.extend(matching_files)
    
    # Remove duplicates
    return list(set(test_files))


def aggregate_affected_files(dependency_tree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aggregate unique affected files from dependency tree.
    
    Args:
        dependency_tree: Tree structure with depth_1_callers, depth_2_callers, etc.
        
    Returns:
        List of unique file info dicts with affected methods
    """
    file_map: Dict[str, Dict[str, Any]] = {}
    
    # Process all depth levels
    for key in dependency_tree:
        if not key.startswith("depth_"):
            continue
        
        callers = dependency_tree[key]
        for caller in callers:
            file_path = caller.get('file_path', '')
            if not file_path:
                continue
            
            if file_path not in file_map:
                file_map[file_path] = {
                    "file_path": file_path,
                    "affected_methods": set(),
                    "call_count": 0
                }
            
            method_name = caller.get('name', '')
            if method_name:
                file_map[file_path]["affected_methods"].add(method_name)
            
            file_map[file_path]["call_count"] += 1
    
    # Convert sets to lists
    result = []
    for file_info in file_map.values():
        file_info["affected_methods"] = sorted(list(file_info["affected_methods"]))
        result.append(file_info)
    
    # Sort by call count (most affected first)
    result.sort(key=lambda x: x["call_count"], reverse=True)
    
    return result


def generate_change_recommendations(
    risk_data: Dict[str, Any],
    coverage_data: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Generate recommendations based on risk and coverage analysis.
    
    Args:
        risk_data: Risk assessment results
        coverage_data: Test coverage analysis
        
    Returns:
        Dict with safe_patterns, risky_patterns, mitigation_strategies
    """
    recommendations = {
        "safe_change_patterns": [],
        "risky_change_patterns": [],
        "mitigation_strategies": []
    }
    
    risk_level = risk_data.get("overall_risk", "MEDIUM")
    composite_score = risk_data.get("composite_risk_score", 0.5)
    has_tests = coverage_data.get("has_direct_tests", False)
    
    # Safe patterns (always applicable)
    recommendations["safe_change_patterns"].extend([
        "Add new optional parameters with defaults (backward compatible)",
        "Improve error messages (no signature change)",
        "Add logging or comments (documentation improvements)",
        "Optimize internal implementation without changing interface"
    ])
    
    # Risky patterns based on risk level
    if composite_score > 0.7:
        recommendations["risky_change_patterns"].extend([
            "Changing method signatures - will affect many call sites",
            "Changing return types - breaks consumer contracts",
            "Removing error handling - could crash dependent code",
            "Removing methods - breaking change for consumers"
        ])
    elif composite_score > 0.5:
        recommendations["risky_change_patterns"].extend([
            "Changing method signatures - verify all callers",
            "Modifying behavior - ensure backward compatibility",
            "Adding required parameters - update call sites"
        ])
    
    # Mitigation strategies
    if not has_tests:
        recommendations["mitigation_strategies"].append(
            "Add comprehensive tests before making changes"
        )
    
    if composite_score > 0.6:
        recommendations["mitigation_strategies"].extend([
            "Consider deprecation warnings before breaking changes",
            "Create new version of method (e.g., execute_v2) for major changes",
            "Add integration tests covering all affected paths",
            "Coordinate with team before modifying core components"
        ])
    else:
        recommendations["mitigation_strategies"].extend([
            "Review existing tests and update as needed",
            "Consider adding tests for edge cases",
            "Document changes clearly in commit messages"
        ])
    
    return recommendations
