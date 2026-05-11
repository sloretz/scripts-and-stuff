#!/usr/bin/env python3

import argparse
import csv
from dataclasses import dataclass
from functools import cache
import sys

from rosdistro import get_index, get_index_url, get_distribution_file
import requests
import yaml


@cache
def fetch_distribution(distro_name):
    index_url = get_index_url()
    index = get_index(index_url)
    return get_distribution_file(index, distro_name)


def get_release_version_by_source_url(distro_name, target_git_url):
    """
    Finds the release version of a ROS package based on its source repository URL.
    """
    dist = fetch_distribution(distro_name)

    for repo_name, repo_data in dist.repositories.items():
        source_repo = repo_data.source_repository

        # Check if a source entry exists and matches the target URL
        if source_repo and source_repo.url == target_git_url:
            release_repo = repo_data.release_repository
            if release_repo and release_repo.version:
                return release_repo.version
            else:
                return None

    return None


@dataclass
class Repository:
    name: str
    url: str
    version: str


def yaml_to_repository_list(data):
    repos = []
    repositories = data.get('repositories', {})
    for name, info in repositories.items():
        url = info.get('url')
        version = info.get('version')
        repos.append(Repository(name=name, url=url, version=version))
    return repos


def repos_from_file(input_repos):
    if input_repos is not None:
        with open(input_repos, 'r') as f:
            data = yaml.safe_load(f)
        return yaml_to_repository_list(data)
    return []


def repos_from_ros2_slash_ros2(distro_name):
    url = f"https://raw.githubusercontent.com/ros2/ros2/refs/heads/{distro_name}/ros2.repos"
    response = requests.get(url)
    response.raise_for_status()
    data = yaml.safe_load(response.text)
    return yaml_to_repository_list(data)


def check_version_space(distro_version, rolling_version):
    """
    Checks if Rolling has a strictly greater minor/major version than the target distro.
    Returns True if Rolling > Distro at the Major.Minor level, providing version space.
    """
    if not distro_version or not rolling_version:
        return False

    try:
        # Strip release tags (e.g., '0.33.2-1' -> '0.33.2')
        d_ver = distro_version.split('-')[0]
        r_ver = rolling_version.split('-')[0]

        # Convert to integers for accurate numeric comparison (e.g., 10 > 9)
        d_parts = tuple(map(int, d_ver.split('.')))
        r_parts = tuple(map(int, r_ver.split('.')))

        if len(d_parts) < 2 or len(r_parts) < 2:
            return False

        d_major, d_minor = d_parts[0], d_parts[1]
        r_major, r_minor = r_parts[0], r_parts[1]

        # Rolling must be strictly greater at the major or minor level
        if r_major > d_major:
            return True
        if r_major == d_major and r_minor > d_minor:
            return True

        # If r_major < d_major OR (r_major == d_major and r_minor <= d_minor), there's no space.
        return False

    except ValueError:
        # Fallback to False if version components aren't cleanly numeric
        return False


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Check if there is sufficient version space between a ROS distro and Rolling.'
    )
    parser.add_argument('--rosdistro', required=True, help='The name of the target ROS distribution (e.g., lyrical).')
    parser.add_argument('--repos', help='Path to a .repos file containing target git URLs.')
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.repos:
        repos = repos_from_file(args.repos)
    else:
        repos = repos_from_ros2_slash_ros2(args.rosdistro)

    # Write output as CSV to stdout
    writer = csv.writer(sys.stdout)
    header = [
        'git_url',
        f'{args.rosdistro}_version',
        'rolling_version',
        f'{args.rosdistro}_has_version_space'
    ]
    writer.writerow(header)

    for repo in repos:
        distro_version = get_release_version_by_source_url(args.rosdistro, repo.url)
        rolling_version = get_release_version_by_source_url('rolling', repo.url)

        has_space = check_version_space(distro_version, rolling_version)

        writer.writerow([
            repo.url,
            distro_version if distro_version else 'None',
            rolling_version if rolling_version else 'None',
            'TRUE' if has_space else 'FALSE'
        ])


if __name__ == "__main__":
    main()
