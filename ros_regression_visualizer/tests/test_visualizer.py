"""Unit tests for ros_regression_visualizer."""

from __future__ import annotations

from ros_regression_visualizer.cli import parse_args
from ros_regression_visualizer.distro_data import DistroData
from ros_regression_visualizer.graph_builder import (
    NodeCategory,
    build_regression_dags,
    transitive_reduce,
)
from ros_regression_visualizer.graphviz_gui import (
    compute_fit_transform,
    compute_graphviz_layout,
    render_graphviz_dot,
)
from ros_regression_visualizer.mermaid import render_mermaid_dags
from ros_regression_visualizer.status_page import (
    AptRepoStatus,
    filter_packages_by_query,
    infer_distro_name,
    parse_status_page_arg,
    parse_status_page_html,
)


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>ROS packages for Lyrical - 2026-09-30 14:31:04 -0800</title>
</head>
<body>
  <h2>ROS packages for Lyrical</h2>
  <table>
    <thead>
      <tr>
        <th class="sortable"><div>Name</div></th>
        <th class="sortable"><div>Repo</div></th>
        <th class="sortable"><div>Version</div></th>
        <th class="sortable"><div>Status</div></th>
        <th class="sortable"><div>Maintainer</div></th>
        <th><div title="Ubuntu Resolute source">Rsource</div></th>
        <th><div title="Ubuntu Resolute amd64">R64</div></th>
      </tr>
    </thead>
    <tbody>
<tr><td><div><a href="https://index.ros.org/p/gtsam#lyrical">gtsam</a></div> <span class="ht">SYNC</span></td><td><div class="repo"><a href="https://github.com/borglab/gtsam/tree/develop">gtsam</a></div></td><td><span>4.3.1-3</span></td><td><span class="developed"/></td><td class="main"><div><a href="mailto:gtsam@lists.gatech.edu">Frank Dellaert</a></div></td><td><a class="e">4.3.1-3resolute</a><a class="e">4.3.1-3resolute</a><a class="l">4.3.0-5resolute</a></td><td><a class="e">4.3.1-3resolute.20260929.155545</a><a class="e">4.3.1-3resolute.20260929.155545</a><a class="l">4.3.0-5resolute.20260728.174508</a></td></tr>
<tr><td><div><a href="https://index.ros.org/p/rtabmap#lyrical">rtabmap</a></div> <span class="ht">DIFF SYNC REGRESSION</span></td><td><div class="repo"><a href="https://github.com/introlab/rtabmap/tree/lyrical-devel">rtabmap</a></div></td><td><span>0.23.7-1</span></td><td><span class="maintained"/></td><td class="main"><div><a href="mailto:matlabbe@gmail.com">Mathieu Labbe</a></div></td><td><a class="e">0.23.7-1resolute</a><a class="e">0.23.7-1resolute</a><a class="e">0.23.7-1resolute</a></td><td><a class="m"/><a class="m"/><a class="e">0.23.7-1resolute.20260915.082129</a></td></tr>
<tr><td><div><a href="https://index.ros.org/p/rtabmap_conversions#lyrical">rtabmap_conversions</a></div> <span class="ht">DIFF SYNC REGRESSION</span></td><td><div class="repo"><a href="https://github.com/introlab/rtabmap_ros/tree/lyrical-devel">rtabmap_ros</a></div></td><td><span>0.23.7-1</span></td><td><span class="maintained"/></td><td class="main"><div><a href="mailto:matlabbe@gmail.com">Mathieu Labbe</a></div></td><td><a class="e">0.23.7-1resolute</a><a class="e">0.23.7-1resolute</a><a class="e">0.23.7-1resolute</a></td><td><a class="m"/><a class="m"/><a class="e">0.23.7-1resolute.20260915.143622</a></td></tr>
<tr><td><div><a href="https://index.ros.org/p/pose_cov_ops#lyrical">pose_cov_ops</a></div> <span class="ht">DIFF SYNC REGRESSION</span></td><td><div class="repo"><a href="https://github.com/mrpt-ros-pkg/pose_cov_ops/tree/master">pose_cov_ops</a></div></td><td><span>0.5.0-1</span></td><td><span class="maintained"/></td><td class="main"><div><a href="mailto:joseluisblancoc@gmail.com">Jose-Luis Blanco-Claraco</a></div></td><td><a class="e">0.5.0-1resolute</a><a class="l">0.4.0-3resolute</a><a class="l">0.4.0-3resolute</a></td><td><a class="m"/><a class="m"/><a class="l">0.4.0-3resolute.20260915.145227</a></td></tr>
<tr><td><div><a href="https://index.ros.org/p/roboplan_core#lyrical">roboplan_core</a></div> <span class="ht">SYNC</span></td><td><div class="repo"><a href="https://github.com/open-planning/roboplan/tree/main">roboplan</a></div></td><td><span>0.7.0-1</span></td><td><span class="developed"/></td><td class="main"><div><a href="mailto:sebas.a.castro@gmail.com">Sebastian Castro</a></div></td><td><a class="e">0.7.0-1resolute</a><a class="e">0.7.0-1resolute</a><a class="m"/></td><td><a class="e">0.7.0-1resolute.20260921.085126</a><a class="e">0.7.0-1resolute.20260921.085126</a><a class="m"/></td></tr>
    </tbody>
  </table>
</body>
</html>
"""


def test_parse_status_page_arg() -> None:
    url, q = parse_status_page_arg(
        "https://repo.ros2.org/status_page/ros_lyrical_default.html?q=REGRESSION"
    )
    assert url == "https://repo.ros2.org/status_page/ros_lyrical_default.html"
    assert q == "REGRESSION"

    url2, q2 = parse_status_page_arg(
        "https://repo.ros2.org/status_page/ros_lyrical_default.html"
    )
    assert url2 == "https://repo.ros2.org/status_page/ros_lyrical_default.html"
    assert q2 is None


def test_infer_distro_name() -> None:
    assert infer_distro_name(SAMPLE_HTML) == "lyrical"
    assert (
        infer_distro_name("", "https://repo.ros2.org/status_page/ros_jazzy_default.html")
        == "jazzy"
    )


def test_parse_status_page_html_and_properties() -> None:
    pkgs = parse_status_page_html(SAMPLE_HTML)
    assert set(pkgs.keys()) == {
        "gtsam",
        "rtabmap",
        "rtabmap_conversions",
        "pose_cov_ops",
        "roboplan_core",
    }

    gtsam = pkgs["gtsam"]
    assert not gtsam.is_regression
    assert not gtsam.is_failing
    assert gtsam.is_new_release
    assert gtsam.previous_version == "4.3.0-5"
    assert gtsam.version == "4.3.1-3"

    rtabmap = pkgs["rtabmap"]
    assert rtabmap.is_regression
    assert rtabmap.is_failing
    assert not rtabmap.is_new_release
    assert rtabmap.previous_version is None

    pose_cov_ops = pkgs["pose_cov_ops"]
    assert pose_cov_ops.is_regression
    assert pose_cov_ops.is_failing
    assert pose_cov_ops.is_new_release
    assert pose_cov_ops.previous_version == "0.4.0-3"

    roboplan_core = pkgs["roboplan_core"]
    assert not roboplan_core.is_regression
    assert not roboplan_core.is_failing
    assert roboplan_core.is_new_release
    assert roboplan_core.previous_version is None


def test_filter_packages_by_query() -> None:
    pkgs = parse_status_page_html(SAMPLE_HTML)
    regressions = filter_packages_by_query(pkgs, None)
    assert regressions == {"rtabmap", "rtabmap_conversions", "pose_cov_ops"}

    red_pkgs = filter_packages_by_query(pkgs, "RED")
    assert red_pkgs == {"rtabmap", "rtabmap_conversions", "pose_cov_ops", "roboplan_core"}

    rtabmap_regs = filter_packages_by_query(pkgs, "REGRESSION+rtabmap")
    assert rtabmap_regs == {"rtabmap", "rtabmap_conversions"}


def test_build_regression_dags_and_mermaid() -> None:
    pkgs = parse_status_page_html(SAMPLE_HTML)
    distro_data = DistroData(
        distro_name="lyrical",
        dependencies={
            "rtabmap_conversions": {"rtabmap", "gtsam"},
            "rtabmap": {"gtsam"},
            "gtsam": set(),
            "pose_cov_ops": set(),
            "roboplan_core": set(),
        },
        release_versions={k: v.version for k, v in pkgs.items()},
        package_repositories={k: v.repo_name for k, v in pkgs.items()},
    )
    targets = filter_packages_by_query(pkgs, "REGRESSION")
    dags = build_regression_dags(targets, pkgs, distro_data)

    # Expect 2 connected components: {pose_cov_ops} and {rtabmap_conversions, rtabmap, gtsam}
    assert len(dags) == 2

    all_nodes = {k: v for dag in dags for k, v in dag.nodes.items()}
    assert (
        all_nodes["pose_cov_ops"].category
        == NodeCategory.ROOT_FAILING_NEW_RELEASE
    )
    assert (
        all_nodes["rtabmap_conversions"].category
        == NodeCategory.BLOCKED_UNCHANGED
    )
    assert (
        all_nodes["rtabmap"].category == NodeCategory.ROOT_FAILING_UNCHANGED
    )
    assert (
        all_nodes["gtsam"].category == NodeCategory.HEALTHY_NEW_RELEASE
    )

    # Transitive reduction removes shortcut edge (rtabmap_conversions -> gtsam)
    all_edges = [e for dag in dags for e in dag.edges]
    assert ("rtabmap_conversions", "rtabmap") in all_edges
    assert ("rtabmap", "gtsam") in all_edges
    assert ("rtabmap_conversions", "gtsam") not in all_edges

    mermaid_str = render_mermaid_dags(dags)
    assert "flowchart TD" in mermaid_str
    assert "pkg_rtabmap_conversions --> pkg_rtabmap" in mermaid_str
    assert "pkg_rtabmap --> pkg_gtsam" in mermaid_str
    assert "4.3.0-5 -> 4.3.1-3" in mermaid_str


def test_apt_repo_status_clean_version() -> None:
    st = AptRepoStatus("l", "4.3.0-5resolute.20260728.174508")
    assert st.clean_version == "4.3.0-5"
    assert st.build_timestamp == "20260728.174508"


def test_transitive_reduce() -> None:
    adj = {
        "a": {"b", "c"},
        "b": {"c"},
        "c": set(),
    }
    reduced = transitive_reduce(adj)
    assert reduced == {
        "a": {"b"},
        "b": {"c"},
        "c": set(),
    }


def test_graphviz_layout_and_fit_transform() -> None:
    pkgs = parse_status_page_html(SAMPLE_HTML)
    distro_data = DistroData(
        distro_name="lyrical",
        dependencies={
            "rtabmap_conversions": {"rtabmap"},
            "rtabmap": {"gtsam"},
            "gtsam": set(),
            "pose_cov_ops": set(),
            "roboplan_core": set(),
        },
        release_versions={k: v.version for k, v in pkgs.items()},
        package_repositories={k: v.repo_name for k, v in pkgs.items()},
    )
    targets = filter_packages_by_query(pkgs, "REGRESSION")
    dags = build_regression_dags(targets, pkgs, distro_data)

    dot_str = render_graphviz_dot(dags)
    assert '"rtabmap_conversions" -> "rtabmap";' in dot_str
    assert '"rtabmap" -> "gtsam";' in dot_str

    layout = compute_graphviz_layout(dags)
    assert layout.width > 0
    assert layout.height > 0
    assert len(layout.nodes) == 4
    assert len(layout.edges) == 2

    # Wide graph in square window -> fills horizontally (offset_x == 0, offset_y > 0)
    scale_h, off_x_h, off_y_h = compute_fit_transform(
        canvas_width=1000.0,
        canvas_height=1000.0,
        graph_width=500.0,
        graph_height=250.0,
    )
    assert scale_h == 2.0
    assert off_x_h == 0.0
    assert off_y_h == 250.0

    # Tall graph in square window -> fills vertically (offset_x > 0, offset_y == 0)
    scale_v, off_x_v, off_y_v = compute_fit_transform(
        canvas_width=1000.0,
        canvas_height=1000.0,
        graph_width=250.0,
        graph_height=500.0,
    )
    assert scale_v == 2.0
    assert off_x_v == 250.0
    assert off_y_v == 0.0


def test_cli_gui_arg() -> None:
    args = parse_args(
        [
            "--status-page",
            "https://repo.ros2.org/status_page/ros_lyrical_default.html",
            "--gui",
        ]
    )
    assert args.gui is True

