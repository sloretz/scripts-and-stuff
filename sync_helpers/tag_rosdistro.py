#!/usr/bin/env python3

import argparse
from datetime import date
import os
import subprocess
import sys
import tempfile


def parse_arguments():
    """Parse command-line arguments for the script."""
    parser = argparse.ArgumentParser(
        description='Tag rosdistro repository at the last commit that changed a distribution file.'
    )
    parser.add_argument(
        '--rosdistro',
        required=True,
        help='The name of the ROS distribution (e.g., lyrical, humble, rolling).'
    )
    parser.add_argument(
        '--date',
        help='The date to use for the tag (format: YYYY-MM-DD). If unspecified, the current date is used.'
    )
    return parser.parse_args()


def clone_repository():
    """Clone the rosdistro repository from GitHub into the current directory."""
    try:
        subprocess.run(
            ['git', 'clone', '-b', 'master', 'git@github.com:ros/rosdistro.git', '.'],
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone rosdistro repository: {e}") from e


def print_last_commit_log(file_path):
    """Print the last commit log for the specified file path."""
    try:
        subprocess.run(
            ['git', 'log', '-n', '1', '--', file_path],
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to show git log for {file_path}: {e}") from e


def get_last_commit_hash(file_path):
    """Retrieve the hash of the last commit modifying the specified file."""
    try:
        result = subprocess.run(
            ['git', 'log', '-n', '1', '--format=format:%H', '--', file_path],
            capture_output=True,
            text=True,
            check=True
        )
        commit_hash = result.stdout.strip()
        if not commit_hash:
            raise ValueError(f"Could not retrieve commit hash for {file_path}")
        return commit_hash
    except (subprocess.CalledProcessError, ValueError) as e:
        raise RuntimeError(f"Failed to retrieve commit hash: {e}") from e


def git_checkout(commit_hash):
    """Check out the repository to the specified commit hash."""
    try:
        subprocess.run(
            ['git', 'checkout', commit_hash],
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to check out commit {commit_hash}: {e}") from e


def git_tag(tag_name):
    """Create a git tag with the specified tag name."""
    try:
        subprocess.run(
            ['git', 'tag', tag_name],
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to create tag {tag_name}: {e}") from e


def main():
    args = parse_arguments()
    rosdistro = args.rosdistro.lower()
    
    if args.date:
        date_str = args.date
    else:
        date_str = date.today().strftime('%Y-%m-%d')
    
    tag_name = f"{rosdistro}/{date_str}"
    
    repo_dir = tempfile.mkdtemp(prefix='rosdistro_')
    os.chdir(repo_dir)
    
    try:
        print("Cloning rosdistro...")
        clone_repository()

        distribution_file = f"{rosdistro}/distribution.yaml"
        
        # Check if the distribution file exists in the repo
        if not os.path.exists(distribution_file):
            raise RuntimeError(f"Distribution file '{distribution_file}' does not exist in the repository.")

        print(f"Last commit log for {distribution_file}:")
        print_last_commit_log(distribution_file)

        commit_hash = get_last_commit_hash(distribution_file)

        print(f"\nChecking out commit {commit_hash}...")
        git_checkout(commit_hash)

        # Create tag
        print(f"Tagging with {tag_name}...")
        git_tag(tag_name)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print("-----------------------------")
    print("If this looks good, then run")
    print("-----------------------------")
    print(f"cd {repo_dir}")
    print(f"git push origin {tag_name}")


if __name__ == '__main__':
    main()
