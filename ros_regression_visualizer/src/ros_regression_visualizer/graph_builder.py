"""Build dependency DAGs connecting failing ROS packages to recent releases."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .distro_data import DistroData
from .status_page import PackageStatus


class NodeCategory(Enum):
    """Classification of a package node by build status and release status."""

    ROOT_FAILING_NEW_RELEASE = "root_failing_new"
    ROOT_FAILING_UNCHANGED = "root_failing"
    BLOCKED_NEW_RELEASE = "blocked_new"
    BLOCKED_UNCHANGED = "blocked_failing"
    HEALTHY_NEW_RELEASE = "new_release"
    INTERMEDIATE_UNCHANGED = "intermediate"


@dataclass(frozen=True)
class GraphNode:
    """A ROS package node in the regression visualization DAG."""

    name: str
    repo_name: str
    version: str
    previous_version: str | None
    category: NodeCategory
    is_regression: bool
    is_failing: bool
    is_root_failing: bool
    is_new_release: bool


@dataclass
class RegressionDAG:
    """A single connected DAG component of failing packages and new releases."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)


def _compute_reachability(
    adj: dict[str, set[str]],
) -> dict[str, set[str]]:
    """Compute transitive reachability for each node in a directed graph."""
    reach: dict[str, set[str]] = {}
    for start in adj:
        visited: set[str] = set()
        stack = list(adj.get(start, set()))
        while stack:
            curr = stack.pop()
            if curr not in visited:
                visited.add(curr)
                stack.extend(adj.get(curr, set()) - visited)
        reach[start] = visited
    return reach


def transitive_reduce(adj: dict[str, set[str]]) -> dict[str, set[str]]:
    """Return the transitive reduction of a directed acyclic graph (or general digraph).

    An edge `u -> v` is removed if there is another neighbor `w` of `u` (`w != v`)
    such that `v` is reachable from `w` without using the direct edge `(u, v)`.
    """
    reach = _compute_reachability(adj)
    reduced: dict[str, set[str]] = {u: set() for u in adj}
    for u, neighbors in adj.items():
        for v in neighbors:
            if any(
                v in reach.get(w, set()) and u not in reach.get(w, set())
                for w in neighbors
                if w != v
            ):
                continue
            reduced[u].add(v)
    return reduced


def build_regression_dags(
    target_packages: set[str],
    status_map: dict[str, PackageStatus],
    distro_data: DistroData,
    *,
    stop_at_first_new_release: bool = True,
    expand_only_root_failures: bool = True,
    apply_transitive_reduction: bool = True,
) -> list[RegressionDAG]:
    """Build one or more dependency DAGs from failing packages to new releases.

    Args:
        target_packages: Initial set of packages selected from the status page
            (e.g. packages matching `?q=REGRESSION`).
        status_map: Mapping of package name to `PackageStatus` from the status page.
        distro_data: Dependency and release metadata from `rosdistro`.
        stop_at_first_new_release: If True, do not expand dependencies beneath a
            healthy (non-failing) new release package.
        expand_only_root_failures: If True, only search through unchanged healthy
            intermediate packages starting from root failing packages (failing
            packages that have no failing dependencies).
        apply_transitive_reduction: If True, remove redundant shortcut edges `u -> v`
            when an indirect path `u -> ... -> v` exists in the subgraph.

    Returns:
        A list of `RegressionDAG` instances, one per connected component.
    """
    deps_map = distro_data.dependencies

    def is_pkg_failing(pkg_name: str) -> bool:
        st = status_map.get(pkg_name)
        return st.is_failing if st is not None else False

    def is_pkg_new(pkg_name: str) -> bool:
        st = status_map.get(pkg_name)
        return st.is_new_release if st is not None else False

    # Step 1: Find all failing packages reachable from `target_packages`
    failing_nodes: set[str] = set(target_packages)
    stack = list(target_packages)
    while stack:
        u = stack.pop()
        for v in deps_map.get(u, set()):
            if is_pkg_failing(v) and v not in failing_nodes:
                failing_nodes.add(v)
                stack.append(v)

    if not failing_nodes:
        return []

    # Step 2: Identify root failing packages (failing packages with no failing deps)
    root_failing_nodes = {
        u for u in failing_nodes if not (deps_map.get(u, set()) & failing_nodes)
    }

    # Step 3: Forward reachability to find paths to new releases
    seed_nodes = root_failing_nodes if expand_only_root_failures else failing_nodes
    forward_nodes: set[str] = set(failing_nodes)
    stack = list(seed_nodes)

    # Also always allow direct new-release dependencies of any failing node
    for u in failing_nodes:
        for v in deps_map.get(u, set()):
            if is_pkg_new(v):
                forward_nodes.add(v)
                if not stop_at_first_new_release:
                    stack.append(v)

    while stack:
        u = stack.pop()
        if (
            stop_at_first_new_release
            and is_pkg_new(u)
            and u not in failing_nodes
        ):
            continue
        for v in deps_map.get(u, set()):
            if v not in forward_nodes:
                forward_nodes.add(v)
                stack.append(v)

    # Step 4: Backward reachability from targets (failing nodes + new releases)
    # so we only keep intermediate unchanged packages that actually lead to a
    # new release (or failing package).
    target_leaves = {
        u for u in forward_nodes if u in failing_nodes or is_pkg_new(u)
    }

    rev_adj: dict[str, set[str]] = {u: set() for u in forward_nodes}
    for u in forward_nodes:
        if (
            stop_at_first_new_release
            and is_pkg_new(u)
            and u not in failing_nodes
        ):
            continue
        if (
            expand_only_root_failures
            and u in failing_nodes
            and u not in root_failing_nodes
        ):
            # For non-root failing packages, keep edges to failing nodes and direct new releases
            for v in deps_map.get(u, set()):
                if v in failing_nodes or is_pkg_new(v):
                    rev_adj[v].add(u)
            continue
        for v in deps_map.get(u, set()):
            if v in forward_nodes:
                rev_adj[v].add(u)

    kept_nodes: set[str] = set(target_leaves)
    stack = list(target_leaves)
    while stack:
        v = stack.pop()
        for u in rev_adj.get(v, set()):
            if u not in kept_nodes:
                kept_nodes.add(u)
                stack.append(u)

    # Step 5: Build adjacency map on `kept_nodes`
    adj: dict[str, set[str]] = {u: set() for u in kept_nodes}
    for u in kept_nodes:
        if (
            stop_at_first_new_release
            and is_pkg_new(u)
            and u not in failing_nodes
        ):
            continue
        if (
            expand_only_root_failures
            and u in failing_nodes
            and u not in root_failing_nodes
        ):
            for v in deps_map.get(u, set()):
                if v in kept_nodes and (v in failing_nodes or is_pkg_new(v)):
                    adj[u].add(v)
            continue
        for v in deps_map.get(u, set()):
            if v in kept_nodes:
                adj[u].add(v)

    if apply_transitive_reduction:
        adj = transitive_reduce(adj)

    # Step 6: Build GraphNode metadata for each kept node
    graph_nodes: dict[str, GraphNode] = {}
    for pkg_name in sorted(kept_nodes):
        st = status_map.get(pkg_name)
        repo_name = (
            st.repo_name
            if (st and st.repo_name)
            else distro_data.package_repositories.get(pkg_name, "")
        )
        version = (
            st.version
            if (st and st.version)
            else distro_data.release_versions.get(pkg_name, "")
        )
        prev_ver = st.previous_version if st else None
        is_reg = st.is_regression if st else False
        failing = pkg_name in failing_nodes or is_pkg_failing(pkg_name)
        root_fail = failing and (pkg_name in root_failing_nodes)
        new_rel = is_pkg_new(pkg_name)

        if root_fail and new_rel:
            category = NodeCategory.ROOT_FAILING_NEW_RELEASE
        elif root_fail and not new_rel:
            category = NodeCategory.ROOT_FAILING_UNCHANGED
        elif failing and new_rel:
            category = NodeCategory.BLOCKED_NEW_RELEASE
        elif failing:
            category = NodeCategory.BLOCKED_UNCHANGED
        elif new_rel:
            category = NodeCategory.HEALTHY_NEW_RELEASE
        else:
            category = NodeCategory.INTERMEDIATE_UNCHANGED

        graph_nodes[pkg_name] = GraphNode(
            name=pkg_name,
            repo_name=repo_name,
            version=version,
            previous_version=prev_ver,
            category=category,
            is_regression=is_reg,
            is_failing=failing,
            is_root_failing=root_fail,
            is_new_release=new_rel,
        )

    # Step 7: Partition into connected components (weakly connected DAGs)
    undirected: dict[str, set[str]] = {u: set() for u in kept_nodes}
    for u, nbrs in adj.items():
        for v in nbrs:
            undirected[u].add(v)
            undirected[v].add(u)

    visited_comp: set[str] = set()
    dags: list[RegressionDAG] = []
    for start in sorted(kept_nodes):
        if start in visited_comp:
            continue
        comp_nodes: set[str] = set()
        comp_stack = [start]
        while comp_stack:
            curr = comp_stack.pop()
            if curr not in visited_comp:
                visited_comp.add(curr)
                comp_nodes.add(curr)
                comp_stack.extend(undirected[curr] - visited_comp)

        sorted_comp = sorted(comp_nodes)
        dag_nodes = {u: graph_nodes[u] for u in sorted_comp}
        dag_edges: list[tuple[str, str]] = []
        for u in sorted_comp:
            for v in sorted(adj.get(u, set())):
                if v in dag_nodes:
                    dag_edges.append((u, v))
        dags.append(RegressionDAG(nodes=dag_nodes, edges=dag_edges))

    return dags
