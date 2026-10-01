"""Graphviz-based layout and interactive Tkinter GUI for ROS regression DAGs."""

from __future__ import annotations

from dataclasses import dataclass, field
import glob
import json
import os
import re
import shutil
import subprocess
import tkinter as tk
from typing import Any

from .graph_builder import GraphNode, NodeCategory, RegressionDAG


NODE_STYLES: dict[NodeCategory, dict[str, Any]] = {
    NodeCategory.ROOT_FAILING_NEW_RELEASE: {
        "fill": "#ffb3b3",
        "outline": "#990000",
        "width": 3.0,
        "dash": None,
        "text_color": "#000000",
        "legend": "Root Failing + New Release",
    },
    NodeCategory.ROOT_FAILING_UNCHANGED: {
        "fill": "#ffd9b3",
        "outline": "#cc3300",
        "width": 2.0,
        "dash": None,
        "text_color": "#000000",
        "legend": "Root Failing (Unchanged)",
    },
    NodeCategory.BLOCKED_NEW_RELEASE: {
        "fill": "#f2d9ff",
        "outline": "#730099",
        "width": 2.0,
        "dash": (5, 4),
        "text_color": "#000000",
        "legend": "Blocked + New Release",
    },
    NodeCategory.BLOCKED_UNCHANGED: {
        "fill": "#fff2e6",
        "outline": "#cc6600",
        "width": 1.5,
        "dash": (5, 4),
        "text_color": "#333333",
        "legend": "Blocked (Unchanged)",
    },
    NodeCategory.HEALTHY_NEW_RELEASE: {
        "fill": "#cce5ff",
        "outline": "#0052cc",
        "width": 2.0,
        "dash": None,
        "text_color": "#000000",
        "legend": "Built + New Release",
    },
    NodeCategory.INTERMEDIATE_UNCHANGED: {
        "fill": "#f2f2f2",
        "outline": "#8c8c8c",
        "width": 1.0,
        "dash": None,
        "text_color": "#333333",
        "legend": "Built (Unchanged)",
    },
}


@dataclass
class LayoutNode:
    """Positioned node from Graphviz layout (in points, origin at top-left)."""

    name: str
    label: str
    category: NodeCategory
    x: float
    y: float
    width: float
    height: float


@dataclass
class LayoutEdge:
    """Positioned directed edge spline from Graphviz layout (in points, origin at top-left)."""

    tail: str
    head: str
    points: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class GraphLayout:
    """Complete 2D layout computed by Graphviz dot."""

    width: float
    height: float
    nodes: list[LayoutNode] = field(default_factory=list)
    edges: list[LayoutEdge] = field(default_factory=list)


def _format_dot_node_label(node: GraphNode) -> str:
    """Format a multi-line label for a Graphviz node showing both release and build status."""
    lines = [node.name]
    if node.is_new_release:
        if node.previous_version and node.version:
            lines.append(f"{node.previous_version} -> {node.version} [NEW RELEASE]")
        elif node.version:
            lines.append(f"new: {node.version} [NEW RELEASE]")
        else:
            lines.append("[NEW RELEASE]")
    elif node.version:
        lines.append(f"{node.version} [UNCHANGED]")
    else:
        lines.append("[UNCHANGED]")

    if node.is_root_failing:
        lines.append("[ROOT FAILING]")
    elif node.is_failing:
        lines.append("[BLOCKED]")
    else:
        lines.append("[BUILT]")

    return "\n".join(lines)


def render_graphviz_dot(
    dags: list[RegressionDAG],
    direction: str = "TD",
) -> str:
    """Render one or more `RegressionDAG`s into a Graphviz DOT string."""
    rankdir_map = {
        "TD": "TB",
        "TB": "TB",
        "BT": "BT",
        "LR": "LR",
        "RL": "RL",
    }
    rankdir = rankdir_map.get(direction.upper(), "TB")

    lines = [
        "digraph G {",
        f"  rankdir={rankdir};",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, margin="0.15,0.08"];',
        "  edge [arrowhead=normal];",
    ]

    merged_nodes: dict[str, GraphNode] = {}
    merged_edges: list[tuple[str, str]] = []
    for dag in dags:
        merged_nodes.update(dag.nodes)
        merged_edges.extend(dag.edges)

    if not merged_nodes:
        lines.append('  empty [label="No matching failing packages found"];')
    else:
        for pkg_name, node in sorted(merged_nodes.items()):
            label = _format_dot_node_label(node).replace('"', '\\"').replace("\n", "\\n")
            lines.append(f'  "{pkg_name}" [label="{label}"];')

        for src, dst in merged_edges:
            lines.append(f'  "{src}" -> "{dst}";')

    lines.append("}")
    return "\n".join(lines)


def _sample_cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 10,
) -> list[tuple[float, float]]:
    """Sample points along a cubic Bezier segment."""
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = (
            (mt**3) * p0[0]
            + 3.0 * (mt**2) * t * p1[0]
            + 3.0 * mt * (t**2) * p2[0]
            + (t**3) * p3[0]
        )
        y = (
            (mt**3) * p0[1]
            + 3.0 * (mt**2) * t * p1[1]
            + 3.0 * mt * (t**2) * p2[1]
            + (t**3) * p3[1]
        )
        pts.append((x, y))
    return pts


def _parse_graphviz_spline(
    pos_str: str,
    bb_height: float,
) -> list[tuple[float, float]]:
    """Parse a Graphviz spline `pos` string into top-left origin `(x, y)` coordinates."""
    start_pt: tuple[float, float] | None = None
    end_pt: tuple[float, float] | None = None
    ctrl_pts: list[tuple[float, float]] = []

    for token in pos_str.split():
        if token.startswith("s,"):
            parts = token[2:].split(",")
            if len(parts) == 2:
                start_pt = (float(parts[0]), bb_height - float(parts[1]))
        elif token.startswith("e,"):
            parts = token[2:].split(",")
            if len(parts) == 2:
                end_pt = (float(parts[0]), bb_height - float(parts[1]))
        else:
            parts = token.split(",")
            if len(parts) == 2:
                ctrl_pts.append((float(parts[0]), bb_height - float(parts[1])))

    sampled: list[tuple[float, float]] = []
    if start_pt is not None:
        sampled.append(start_pt)

    if len(ctrl_pts) >= 4 and (len(ctrl_pts) - 1) % 3 == 0:
        for i in range(0, len(ctrl_pts) - 1, 3):
            seg = _sample_cubic_bezier(
                ctrl_pts[i], ctrl_pts[i + 1], ctrl_pts[i + 2], ctrl_pts[i + 3]
            )
            if sampled:
                sampled.extend(seg[1:])
            else:
                sampled.extend(seg)
    else:
        sampled.extend(ctrl_pts)

    if end_pt is not None:
        sampled.append(end_pt)

    return sampled


def compute_graphviz_layout(
    dags: list[RegressionDAG],
    direction: str = "TD",
) -> GraphLayout:
    """Compute 2D layout for the given DAGs using Graphviz `dot -Tjson0`."""
    if shutil.which("dot") is None:
        raise RuntimeError(
            "Graphviz 'dot' executable not found on PATH. Please install graphviz."
        )

    dot_src = render_graphviz_dot(dags, direction=direction)
    result = subprocess.run(
        ["dot", "-Tjson0"],
        input=dot_src,
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(result.stdout)

    bb_str = data.get("bb", "0,0,100,100")
    bb_parts = [float(x) for x in bb_str.split(",")]
    bb_width = max(1.0, bb_parts[2] - bb_parts[0])
    bb_height = max(1.0, bb_parts[3] - bb_parts[1])

    merged_nodes: dict[str, GraphNode] = {}
    for dag in dags:
        merged_nodes.update(dag.nodes)

    gvid_to_name: dict[int, str] = {}
    layout_nodes: list[LayoutNode] = []

    for obj in data.get("objects", []):
        if "pos" not in obj:
            continue
        name = obj.get("name", "")
        gvid = obj.get("_gvid")
        if isinstance(gvid, int):
            gvid_to_name[gvid] = name

        cx_str, cy_str = obj["pos"].split(",")
        cx = float(cx_str)
        cy = bb_height - float(cy_str)
        w_pts = float(obj.get("width", 1.0)) * 72.0
        h_pts = float(obj.get("height", 0.5)) * 72.0

        graph_node = merged_nodes.get(name)
        if graph_node is not None:
            label = _format_dot_node_label(graph_node)
            category = graph_node.category
        else:
            label = obj.get("label", name).replace("\\n", "\n")
            category = NodeCategory.INTERMEDIATE_UNCHANGED

        layout_nodes.append(
            LayoutNode(
                name=name,
                label=label,
                category=category,
                x=cx,
                y=cy,
                width=w_pts,
                height=h_pts,
            )
        )

    layout_edges: list[LayoutEdge] = []
    for edge in data.get("edges", []):
        pos_str = edge.get("pos", "")
        if not pos_str:
            continue
        tail_name = gvid_to_name.get(edge.get("tail", -1), "")
        head_name = gvid_to_name.get(edge.get("head", -1), "")
        pts = _parse_graphviz_spline(pos_str, bb_height)
        if len(pts) >= 2:
            layout_edges.append(
                LayoutEdge(tail=tail_name, head=head_name, points=pts)
            )

    return GraphLayout(
        width=bb_width,
        height=bb_height,
        nodes=layout_nodes,
        edges=layout_edges,
    )


def _ensure_display_env() -> None:
    """Populate DISPLAY and XAUTHORITY on Linux Xwayland sessions if missing."""
    if os.environ.get("DISPLAY"):
        return
    if os.path.exists("/tmp/.X11-unix/X0"):
        os.environ["DISPLAY"] = ":0"
        if not os.environ.get("XAUTHORITY"):
            uid = os.getuid()
            matches = glob.glob(f"/run/user/{uid}/.mutter-Xwaylandauth.*")
            if matches:
                os.environ["XAUTHORITY"] = matches[0]


class RegressionVisualizerGUI:
    """Interactive Tkinter GUI window displaying a Graphviz-laid-out DAG."""

    BASE_FONT_PIXEL_SIZE = 13

    def __init__(
        self,
        layout: GraphLayout,
        title: str = "ROS Regression Visualizer",
    ) -> None:
        _ensure_display_env()
        self.layout = layout
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1200x850")

        # Top toolbar with a single button to reset the visualization + legend swatches
        toolbar = tk.Frame(self.root, padx=6, pady=4)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.reset_button = tk.Button(
            toolbar,
            text="Reset View",
            command=self.reset_view,
        )
        self.reset_button.pack(side=tk.LEFT, padx=(0, 12))

        for style in NODE_STYLES.values():
            swatch = tk.Label(
                toolbar,
                text=style["legend"],
                bg=style["fill"],
                fg=style["text_color"],
                padx=6,
                pady=2,
                relief=tk.SOLID,
                bd=1,
                font=("Helvetica", 9),
            )
            swatch.pack(side=tk.LEFT, padx=3)

        # Interactive canvas
        self.canvas = tk.Canvas(
            self.root,
            bg="#ffffff",
            highlightthickness=0,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.scale: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self._drag_last_x: int = 0
        self._drag_last_y: int = 0
        self._initial_fit_done: bool = False

        self._text_items: list[int] = []
        self._rect_items: list[tuple[int, float]] = []
        self._edge_items: list[int] = []

        self._draw_initial_items()
        self._bind_events()

    def _draw_initial_items(self) -> None:
        """Draw all edges and nodes at base coordinates (scale=1.0, offset=(0, 0))."""
        self.canvas.delete("all")
        self._text_items.clear()
        self._rect_items.clear()
        self._edge_items.clear()

        # Draw edges first so nodes sit on top
        for edge in self.layout.edges:
            flat_coords: list[float] = []
            for px, py in edge.points:
                flat_coords.extend((px, py))
            line_id = self.canvas.create_line(
                *flat_coords,
                fill="#555555",
                width=1.5,
                arrow=tk.LAST,
                arrowshape=(8, 10, 4),
            )
            self._edge_items.append(line_id)

        # Draw nodes
        for node in self.layout.nodes:
            style = NODE_STYLES.get(
                node.category, NODE_STYLES[NodeCategory.INTERMEDIATE_UNCHANGED]
            )
            x0 = node.x - node.width / 2.0
            y0 = node.y - node.height / 2.0
            x1 = node.x + node.width / 2.0
            y1 = node.y + node.height / 2.0

            rect_kwargs: dict[str, Any] = {
                "fill": style["fill"],
                "outline": style["outline"],
                "width": style["width"],
            }
            if style["dash"]:
                rect_kwargs["dash"] = style["dash"]

            rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, **rect_kwargs)
            self._rect_items.append((rect_id, float(style["width"])))

            text_id = self.canvas.create_text(
                node.x,
                node.y,
                text=node.label,
                fill=style["text_color"],
                font=("Helvetica", -self.BASE_FONT_PIXEL_SIZE),
                justify=tk.CENTER,
            )
            self._text_items.append(text_id)

        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

    def _bind_events(self) -> None:
        """Bind mouse pan, wheel zoom, and initial window configure events."""
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        # Linux X11/Wayland scroll wheel button events
        self.canvas.bind("<Button-4>", self._on_scroll_up)
        self.canvas.bind("<Button-5>", self._on_scroll_down)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, event: tk.Event[Any]) -> None:
        if not self._initial_fit_done and event.width > 10 and event.height > 10:
            self._initial_fit_done = True
            self.reset_view()

    def _on_mouse_down(self, event: tk.Event[Any]) -> None:
        self._drag_last_x = event.x
        self._drag_last_y = event.y

    def _on_mouse_drag(self, event: tk.Event[Any]) -> None:
        dx = event.x - self._drag_last_x
        dy = event.y - self._drag_last_y
        self._drag_last_x = event.x
        self._drag_last_y = event.y
        self.pan(dx, dy)

    def _on_mouse_wheel(self, event: tk.Event[Any]) -> None:
        if event.delta > 0:
            self.zoom_at(event.x, event.y, 1.15)
        elif event.delta < 0:
            self.zoom_at(event.x, event.y, 1.0 / 1.15)

    def _on_scroll_up(self, event: tk.Event[Any]) -> None:
        self.zoom_at(event.x, event.y, 1.15)

    def _on_scroll_down(self, event: tk.Event[Any]) -> None:
        self.zoom_at(event.x, event.y, 1.0 / 1.15)

    def pan(self, dx: float, dy: float) -> None:
        """Translate all canvas items by `(dx, dy)` pixels."""
        self.canvas.move("all", dx, dy)
        self.offset_x += dx
        self.offset_y += dy

    def zoom_at(self, pivot_x: float, pivot_y: float, factor: float) -> None:
        """Zoom all canvas items by `factor` around `(pivot_x, pivot_y)`."""
        new_scale = self.scale * factor
        if new_scale < 0.02 or new_scale > 30.0:
            return

        self.canvas.scale("all", pivot_x, pivot_y, factor, factor)
        self.scale = new_scale
        self.offset_x = pivot_x + (self.offset_x - pivot_x) * factor
        self.offset_y = pivot_y + (self.offset_y - pivot_y) * factor
        self._update_scaled_styles()

    def _update_scaled_styles(self) -> None:
        """Update font sizes, border widths, and arrow shapes to match `self.scale`."""
        pixel_font = int(round(self.BASE_FONT_PIXEL_SIZE * self.scale))
        if pixel_font < 3:
            for text_id in self._text_items:
                self.canvas.itemconfigure(text_id, state="hidden")
        else:
            font_spec = ("Helvetica", -pixel_font)
            for text_id in self._text_items:
                self.canvas.itemconfigure(text_id, state="normal", font=font_spec)

        for rect_id, base_w in self._rect_items:
            scaled_w = max(1.0, base_w * self.scale)
            self.canvas.itemconfigure(rect_id, width=scaled_w)

        edge_w = max(1.0, 1.5 * self.scale)
        a1 = max(3, int(round(8 * self.scale)))
        a2 = max(4, int(round(10 * self.scale)))
        a3 = max(2, int(round(4 * self.scale)))
        for edge_id in self._edge_items:
            self.canvas.itemconfigure(
                edge_id, width=edge_w, arrowshape=(a1, a2, a3)
            )

    def reset_view(self) -> None:
        """Reset zoom and pan so the diagram fills the window horizontally or vertically."""
        self.root.update_idletasks()
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())

        target_scale, target_offset_x, target_offset_y = compute_fit_transform(
            canvas_width=cw,
            canvas_height=ch,
            graph_width=self.layout.width,
            graph_height=self.layout.height,
        )

        # Undo current offset, apply relative scale around (0, 0), then move to target offset
        self.canvas.move("all", -self.offset_x, -self.offset_y)
        rel_scale = target_scale / self.scale
        self.canvas.scale("all", 0.0, 0.0, rel_scale, rel_scale)
        self.canvas.move("all", target_offset_x, target_offset_y)

        self.scale = target_scale
        self.offset_x = target_offset_x
        self.offset_y = target_offset_y
        self._update_scaled_styles()

    def run(self) -> None:
        """Start the Tkinter main event loop."""
        self.root.mainloop()


def compute_fit_transform(
    canvas_width: float,
    canvas_height: float,
    graph_width: float,
    graph_height: float,
) -> tuple[float, float, float]:
    """Compute `(scale, offset_x, offset_y)` so the graph fills the window horizontally or vertically."""
    gw = max(1.0, graph_width)
    gh = max(1.0, graph_height)
    cw = max(1.0, canvas_width)
    ch = max(1.0, canvas_height)

    scale = min(cw / gw, ch / gh)
    offset_x = (cw - gw * scale) / 2.0
    offset_y = (ch - gh * scale) / 2.0
    return scale, offset_x, offset_y


def launch_gui(
    dags: list[RegressionDAG],
    direction: str = "TD",
    distro_name: str = "",
) -> None:
    """Compute Graphviz layout and open the interactive GUI window."""
    layout = compute_graphviz_layout(dags, direction=direction)
    title = (
        f"ROS Regression Visualizer - {distro_name.capitalize()}"
        if distro_name
        else "ROS Regression Visualizer"
    )
    gui = RegressionVisualizerGUI(layout=layout, title=title)
    gui.run()
