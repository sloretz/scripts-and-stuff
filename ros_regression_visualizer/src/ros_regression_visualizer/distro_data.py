"""Fetch and parse ROS distribution release and dependency metadata using rosdistro."""

from __future__ import annotations

from dataclasses import dataclass, field
import gzip
from urllib.parse import urlparse

from catkin_pkg.package import parse_package_string
import requests
import rosdistro
import yaml


@dataclass
class DistroData:
    """Release and dependency information for a ROS distribution.

    Attributes:
        distro_name: Name of the ROS distribution (e.g. 'lyrical').
        dependencies: Mapping from package name to the set of ROS packages in the
            same distribution that it depends on.
        release_versions: Mapping from package name to its released version in
            the rosdistro distribution file.
        package_repositories: Mapping from package name to its repository name.
    """

    distro_name: str
    dependencies: dict[str, set[str]] = field(default_factory=dict)
    release_versions: dict[str, str] = field(default_factory=dict)
    package_repositories: dict[str, str] = field(default_factory=dict)


def load_distribution_cache(
    distro_name: str,
    cache_url_or_path: str | None = None,
    index_url: str | None = None,
) -> rosdistro.DistributionCache:
    """Load a `rosdistro.DistributionCache` from the rosdistro index or a local/remote path."""
    if cache_url_or_path:
        parsed = urlparse(cache_url_or_path)
        if parsed.scheme in ("http", "https"):
            response = requests.get(cache_url_or_path, timeout=60.0)
            response.raise_for_status()
            raw_bytes = response.content
            if cache_url_or_path.endswith(".gz"):
                yaml_text = gzip.decompress(raw_bytes).decode("utf-8")
            else:
                yaml_text = raw_bytes.decode("utf-8")
            data = yaml.safe_load(yaml_text)
        else:
            path = parsed.path if parsed.scheme == "file" else cache_url_or_path
            if path.endswith(".gz"):
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
        return rosdistro.DistributionCache(distro_name, data)

    effective_index_url = index_url or rosdistro.get_index_url()
    index = rosdistro.get_index(effective_index_url)
    if distro_name not in index.distributions:
        raise ValueError(
            f"ROS distribution '{distro_name}' not found in rosdistro index at {effective_index_url}"
        )
    return rosdistro.get_distribution_cache(index, distro_name)


def extract_distro_data(
    cache: rosdistro.DistributionCache,
    include_test_depends: bool = True,
) -> DistroData:
    """Extract package dependencies and release versions from a `DistributionCache`."""
    dist_file = cache.distribution_file
    distro_name = dist_file.name

    release_versions: dict[str, str] = {}
    package_repositories: dict[str, str] = {}

    for repo_name, repo_spec in dist_file.repositories.items():
        rel_repo = repo_spec.release_repository
        if rel_repo is None:
            continue
        repo_version = rel_repo.version or ""
        for pkg_name in rel_repo.package_names:
            release_versions[pkg_name] = repo_version
            package_repositories[pkg_name] = repo_name

    raw_deps: dict[str, set[str]] = {}
    for pkg_name, xml_str in cache.release_package_xmls.items():
        if not xml_str:
            continue
        pkg = parse_package_string(xml_str)
        dep_objs = (
            pkg.build_depends
            + pkg.buildtool_depends
            + pkg.build_export_depends
            + pkg.buildtool_export_depends
            + pkg.exec_depends
        )
        if include_test_depends:
            dep_objs = dep_objs + pkg.test_depends

        raw_deps[pkg_name] = {d.name for d in dep_objs if d.name != pkg_name}

    known_ros_packages = set(raw_deps.keys()) | set(release_versions.keys())
    dependencies: dict[str, set[str]] = {
        pkg_name: (deps & known_ros_packages) - {pkg_name}
        for pkg_name, deps in raw_deps.items()
    }

    return DistroData(
        distro_name=distro_name,
        dependencies=dependencies,
        release_versions=release_versions,
        package_repositories=package_repositories,
    )
