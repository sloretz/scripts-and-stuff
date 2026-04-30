#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
from datetime import datetime
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


def latest_release_by_source_url(distro_name, target_git_url):
    """
    Finds the current release version of a ROS package based on its source repository URL.

    Args:
        distro_name (str): The name of the ROS distribution to search 
            (e.g., 'humble', 'rolling', 'noetic').
        target_git_url (str): The exact source Git URL of the repository 
            to look up.

    Returns:
        str: The release version string (e.g., '16.0.9-1') if the repository 
            and a corresponding release entry are found.
        None: If the URL is not found in the distribution or if the 
            repository exists but has no release entry.
    """
    dist = fetch_distribution(distro_name)

    # Iterate through all repositories in the distribution
    for repo_name, repo_data in dist.repositories.items():
        source_repo = repo_data.source_repository

        # Check if a source entry exists and matches the target URL
        # TODO(sloretz) normalize URLs?
        if source_repo and source_repo.url == target_git_url:
            # Get the release entry corresponding to this repository
            release_repo = repo_data.release_repository
            if release_repo:
                return release_repo.version
            else:
                # No release, return None
                return None

    # No such repository, return None
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


def repository_list_to_yaml(repos):
    repo_dict = {}
    for repo in repos:
        repo_dict[repo.name] = {
            'type': 'git',
            'url': repo.url,
            'version': repo.version
        }
    return {'repositories': repo_dict}


def parse_pins(pin_args):
    pins = {}
    if pin_args:
        for pin in pin_args:
            if '=' not in pin:
                print(f"Error: Invalid pin format '{pin}'. Expected 'repo_name=version'", file=sys.stderr)
                sys.exit(1)
            name, version = pin.split('=', 1)
            pins[name] = version
    return pins


def parse_arguments():
    parser = argparse.ArgumentParser(description='Find release versions for ROS repositories.')
    parser.add_argument('--rosdistro', required=True, help='The name of the ROS distribution (e.g., humble, rolling).')
    parser.add_argument('--input-repos', help='Path to a file containing target git URLs.')
    parser.add_argument('--pin', action='append', help='Pin a repository to a specific version. Format: repo_name=version')
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.input_repos:
        repos = repos_from_file(args.input_repos)
    else:
        repos = repos_from_ros2_slash_ros2(args.rosdistro)

    pins = parse_pins(args.pin)

    # Check that pinned repos exist in input repos
    repo_names = {repo.name for repo in repos}
    for pinned_name in pins:
        if pinned_name not in repo_names:
            print(f"Error: Pinned repository '{pinned_name}' not found in input repos.", file=sys.stderr)
            sys.exit(1)

    todays_date_and_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"# ROS {args.rosdistro.capitalize()} release distribution file")
    print(f"# Generated on {todays_date_and_time}")

    for pin_name, pin_version in pins.items():
        print(f"# --pin {pin_name}={pin_version}")

    output_repos = []
    for repo in repos:
        if repo.name in pins:
            latest_version = pins[repo.name]
        else:
            latest_version = latest_release_by_source_url(args.rosdistro, repo.url)
            
        if not latest_version:
            print(f"# WARNING: Did not find a release for: {repo.url} in {args.rosdistro}")
            continue
        # Success, include this repo in the output
        repo.version = latest_version
        output_repos.append(repo)

    yaml_data = repository_list_to_yaml(output_repos)
    yaml_string = yaml.dump(yaml_data, sort_keys=False)
    print(yaml_string)


if __name__ == "__main__":
    main()
