# ROS Regression Visualizer

A Python CLI tool that visualizes relationships between failing ROS packages on a ROS buildfarm status page and the most recent package releases as a [Mermaid](https://mermaid.js.org/) flowchart diagram.

When investigating regressions before a ROS distribution sync, dozens of failing packages on the status page are often caused by only one or two newly released upstream packages. This tool parses the status page and the `rosdistro` distribution cache to trace dependency paths from failing packages to all recent releases.

## Installation

From the repository root, install into your virtual environment:

```bash
./env3/bin/pip install -e "./ros_regression_visualizer[test]"
```

## Usage

```bash
# Visualize all REGRESSION packages on the ROS Lyrical status page
ros-regression-visualizer --status-page https://repo.ros2.org/status_page/ros_lyrical_default.html

# Or pass a status page URL with an explicit ?q= filter
ros-regression-visualizer --status-page "https://repo.ros2.org/status_page/ros_lyrical_default.html?q=REGRESSION"

# Open an interactive GUI window (mouse-wheel zoom, click-and-drag pan, Reset View button)
ros-regression-visualizer --status-page "https://repo.ros2.org/status_page/ros_lyrical_default.html?q=REGRESSION" --gui

# Use a locally downloaded status page and cache file
ros-regression-visualizer \
  --status-page ros_lyrical_default.html \
  --cache lyrical-cache.yaml.gz \
  --markdown
```

### Node Categories in the Diagram

- **Failing + New Release (`failing_new`)**: Package has a newer version in `rosdistro` than in `main` (released since the last sync) **and** is failing to build.
- **Root Failing (`root_failing`)**: Package version is unchanged since the last sync, all of its dependencies built, and its own build is failing.
- **Blocked Failing (`blocked_failing`)**: Package is failing because one or more of its dependencies failed to build.
- **New Release (`new_release`)**: Package has a newer version in `rosdistro` than in `main`, built successfully, and is depended upon by a failing package.
- **Intermediate (`intermediate`)**: Unchanged, healthy package along a dependency path between a failing package and a new release.

## Running Tests

```bash
./env3/bin/pytest ros_regression_visualizer/tests
```
