"""Command-line interface for ros_regression_visualizer."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import sys

from .distro_data import extract_distro_data, load_distribution_cache
from .graph_builder import build_regression_dags
from .graphviz_gui import launch_gui
from .mermaid import render_mermaid_dags
from .status_page import (
    fetch_status_page,
    filter_packages_by_query,
    infer_distro_name,
    parse_status_page_arg,
    parse_status_page_html,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Visualize relationships between failing ROS packages on a buildfarm "
            "status page and recent package releases as a Mermaid diagram."
        )
    )
    parser.add_argument(
        "--status-page",
        required=True,
        help=(
            "URL or local path to a ROS buildfarm status page "
            "(e.g. https://repo.ros2.org/status_page/ros_lyrical_default.html "
            "or https://repo.ros2.org/status_page/ros_lyrical_default.html?q=REGRESSION)."
        ),
    )
    parser.add_argument(
        "-q",
        "--query",
        default=None,
        help=(
            "Override the status page query filter (defaults to the ?q=... parameter "
            "in --status-page, or 'REGRESSION' if none is present)."
        ),
    )
    parser.add_argument(
        "--rosdistro",
        default=None,
        help="ROS distribution name (inferred from the status page if omitted).",
    )
    parser.add_argument(
        "--cache",
        default=None,
        help=(
            "Optional URL or local path to the rosdistro cache file "
            "(e.g. lyrical-cache.yaml.gz). Fetched via rosdistro index if omitted."
        ),
    )
    parser.add_argument(
        "--direction",
        choices=["TD", "TB", "BT", "RL", "LR"],
        default="TD",
        help="Diagram direction (default: TD).",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open an interactive GUI window rendering the diagram using Graphviz.",
    )
    parser.add_argument(
        "--split-dags",
        action="store_true",
        help="Emit a separate Mermaid diagram for each connected DAG component.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Wrap Mermaid diagram(s) in ```mermaid code fences.",
    )
    parser.add_argument(
        "--include-transitive-new-releases",
        action="store_true",
        help=(
            "Continue traversing dependencies beneath healthy new releases to show "
            "all transitive new releases."
        ),
    )
    parser.add_argument(
        "--expand-blocked-failures",
        action="store_true",
        help=(
            "Also traverse through unchanged healthy intermediate packages from "
            "blocked failing packages, not only from root failing packages."
        ),
    )
    parser.add_argument(
        "--no-transitive-reduction",
        action="store_true",
        help="Do not perform transitive reduction on the dependency DAG edges.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Optional output file path (defaults to stdout when --gui is not set).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint for ros-regression-visualizer."""
    args = parse_args(argv)

    base_url_or_path, url_query = parse_status_page_arg(args.status_page)
    effective_query = args.query if args.query is not None else url_query

    try:
        html = fetch_status_page(base_url_or_path)
        distro_name = (
            args.rosdistro.lower()
            if args.rosdistro
            else infer_distro_name(html, base_url_or_path)
        )
        status_map = parse_status_page_html(html)
        target_packages = filter_packages_by_query(status_map, effective_query)

        cache = load_distribution_cache(
            distro_name=distro_name,
            cache_url_or_path=args.cache,
        )
        distro_data = extract_distro_data(cache)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    dags = build_regression_dags(
        target_packages=target_packages,
        status_map=status_map,
        distro_data=distro_data,
        stop_at_first_new_release=not args.include_transitive_new_releases,
        expand_only_root_failures=not args.expand_blocked_failures,
        apply_transitive_reduction=not args.no_transitive_reduction,
    )

    output_text = render_mermaid_dags(
        dags,
        direction=args.direction,
        combine_into_single_diagram=not args.split_dags,
        markdown_fences=args.markdown,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text + "\n")
    elif not args.gui:
        print(output_text)

    if args.gui:
        try:
            launch_gui(dags, direction=args.direction, distro_name=distro_name)
        except Exception as exc:
            print(f"Error launching GUI: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
