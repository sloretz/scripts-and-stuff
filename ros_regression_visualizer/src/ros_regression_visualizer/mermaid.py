"""Generate Mermaid flowchart diagrams from ROS regression dependency DAGs."""

from __future__ import annotations

import re

from .graph_builder import GraphNode, NodeCategory, RegressionDAG


CLASS_DEFS: list[str] = [
    "classDef root_failing_new fill:#ffb3b3,stroke:#990000,stroke-width:3px,color:#000000;",
    "classDef root_failing fill:#ffd9b3,stroke:#cc3300,stroke-width:2px,color:#000000;",
    "classDef blocked_new fill:#f2d9ff,stroke:#730099,stroke-width:2px,stroke-dasharray: 5 5,color:#000000;",
    "classDef blocked_failing fill:#fff2e6,stroke:#cc6600,stroke-width:1px,stroke-dasharray: 5 5,color:#333333;",
    "classDef new_release fill:#cce5ff,stroke:#0052cc,stroke-width:2px,color:#000000;",
    "classDef intermediate fill:#f2f2f2,stroke:#8c8c8c,stroke-width:1px,color:#333333;",
]


def _safe_node_id(pkg_name: str) -> str:
    """Return a Mermaid-safe node identifier that avoids keyword collisions."""
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", pkg_name)
    return f"pkg_{sanitized}"


def _format_node_label(node: GraphNode) -> str:
    """Format the text label for a package node in the Mermaid diagram."""
    parts = [node.name]
    if node.is_new_release:
        if node.previous_version and node.version:
            parts.append(f"({node.previous_version} -> {node.version}) [NEW RELEASE]")
        elif node.version:
            parts.append(f"(new: {node.version}) [NEW RELEASE]")
        else:
            parts.append("[NEW RELEASE]")
    elif node.version:
        parts.append(f"({node.version}) [UNCHANGED]")
    else:
        parts.append("[UNCHANGED]")

    if node.is_root_failing:
        parts.append("[ROOT FAILING]")
    elif node.is_failing:
        parts.append("[BLOCKED]")
    else:
        parts.append("[BUILT]")

    escaped = " ".join(part.replace('"', "'") for part in parts)
    return f'"{escaped}"'


def render_mermaid_dag(
    dag: RegressionDAG,
    direction: str = "TD",
) -> str:
    """Render a single `RegressionDAG` as a Mermaid flowchart string."""
    lines: list[str] = [f"flowchart {direction}"]
    for class_def in CLASS_DEFS:
        lines.append(f"    {class_def}")

    for pkg_name, node in sorted(dag.nodes.items()):
        node_id = _safe_node_id(pkg_name)
        label = _format_node_label(node)
        lines.append(f"    {node_id}[{label}]:::{node.category.value}")

    for src, dst in dag.edges:
        src_id = _safe_node_id(src)
        dst_id = _safe_node_id(dst)
        lines.append(f"    {src_id} --> {dst_id}")

    return "\n".join(lines)


def render_mermaid_dags(
    dags: list[RegressionDAG],
    direction: str = "TD",
    *,
    combine_into_single_diagram: bool = True,
    markdown_fences: bool = False,
) -> str:
    """Render one or more `RegressionDAG` components into Mermaid diagram text.

    Args:
        dags: List of `RegressionDAG` components.
        direction: Flowchart direction ('TD', 'LR', etc.).
        combine_into_single_diagram: If True, emit a single `flowchart` block
            containing all DAG components. If False, emit a separate diagram per
            connected DAG component.
        markdown_fences: If True, wrap each Mermaid diagram in ```mermaid fences.
    """
    if not dags:
        empty = f'flowchart {direction}\n    empty["No matching failing packages found"]'
        if markdown_fences:
            return f"```mermaid\n{empty}\n```"
        return empty

    if combine_into_single_diagram:
        merged_nodes: dict[str, GraphNode] = {}
        merged_edges: list[tuple[str, str]] = []
        for dag in dags:
            merged_nodes.update(dag.nodes)
            merged_edges.extend(dag.edges)
        combined = render_mermaid_dag(
            RegressionDAG(nodes=merged_nodes, edges=merged_edges),
            direction=direction,
        )
        if markdown_fences:
            return f"```mermaid\n{combined}\n```"
        return combined

    blocks: list[str] = []
    for dag in dags:
        rendered = render_mermaid_dag(dag, direction=direction)
        if markdown_fences:
            blocks.append(f"```mermaid\n{rendered}\n```")
        else:
            blocks.append(rendered)
    return "\n\n".join(blocks)
