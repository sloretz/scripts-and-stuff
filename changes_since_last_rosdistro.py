#!/usr/bin/env python3
"""Create a CSV file showing new commits in a ROS distribution since a previous rosdistro.

Notice: This script has been vibe coded with Gemini.

This script takes paths to repository files (YAML files common in ROS 2) for two
ROS distributions (new and old) and compares them, outputting probably new commits to a CSV file.
"""

import argparse
from collections.abc import Iterator
import csv
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import cached_property
import re
import subprocess
import tempfile
import yaml


@dataclass
class Repository:
    """Data class representing a repository in a ROS 2 repos file.

    Assuming git repositories.
    """

    name: str
    url: str
    branch: str


class ModifiedFile:
    """Represents a file modified in a git commit."""

    def __init__(
        self,
        repo_path: str,
        commit_hash: str,
        filename: str,
        added_lines: int,
        removed_lines: int,
    ) -> None:
        self._repo_path = repo_path
        self._commit_hash = commit_hash
        self.filename = filename
        self.added_lines = added_lines
        self.removed_lines = removed_lines

    @cached_property
    def modified_lines(self) -> int:
        return self.added_lines + self.removed_lines

    @cached_property
    def patch(self) -> str:
        """Get the diff/patch for this specific file."""
        result = subprocess.run(
            [
                "git",
                "show",
                "--format=",
                self._commit_hash,
                "--",
                self.filename,
            ],
            cwd=self._repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


class Commit:
    """Represents a git commit with cached accessors for its metadata and changes."""

    def __init__(self, repo_path: str, commit_hash: str) -> None:
        self._repo_path = repo_path
        self.hash = commit_hash

    @cached_property
    def message(self) -> str:
        """Get the commit message."""
        result = subprocess.run(
            ["git", "log", "--format=%B", "-n", "1", self.hash],
            cwd=self._repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    @cached_property
    def first_message_line(self) -> str:
        """Get the first line of the commit message."""
        return self.message.splitlines()[0] if self.message else ""

    @cached_property
    def modified_files(self) -> list[ModifiedFile]:
        """Get the list of files modified in this commit."""
        result = subprocess.run(
            ["git", "show", "--numstat", "--format=", self.hash],
            cwd=self._repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        files = []
        for line in result.stdout.splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) == 3:
                add_str, rem_str, filename = parts
                try:
                    added = int(add_str)
                except ValueError:
                    added = 0
                try:
                    removed = int(rem_str)
                except ValueError:
                    removed = 0
                files.append(
                    ModifiedFile(
                        self._repo_path, self.hash, filename, added, removed
                    )
                )
        return files

    @cached_property
    def added_lines(self) -> int:
        return sum(f.added_lines for f in self.modified_files)

    @cached_property
    def removed_lines(self) -> int:
        return sum(f.removed_lines for f in self.modified_files)

    @cached_property
    def modified_lines(self) -> int:
        return sum(f.modified_lines for f in self.modified_files)


def commits_are_probably_same(commit1: Commit, commit2: Commit) -> bool:
    """Fuzzy comparison to check if two commits are probably the same change.

    Checks if commit messages have string similarity up to a hard coded threshold.
    """
    if commit1.hash == commit2.hash:
        return True

    title1 = commit1.first_message_line.strip()
    title2 = commit2.first_message_line.strip()

    if not title1 and not title2:
        return True
    if not title1 or not title2:
        return False

    files1 = {f.filename for f in commit1.modified_files}
    files2 = {f.filename for f in commit2.modified_files}
    if files1 != files2:
        return False

    # Strip PR numbers like (#105) or (backport #104) before similarity check
    clean1 = re.sub(r"\s*\(#\d+\)|\s*\(backport #\d+\)", "", title1).strip().lower()
    clean2 = re.sub(r"\s*\(#\d+\)|\s*\(backport #\d+\)", "", title2).strip().lower()

    return SequenceMatcher(None, clean1, clean2).ratio() >= 0.50


def is_probably_release_commit(commit: Commit) -> bool:
    """Check if a commit is likely a release/version bump or changelog update commit."""
    if commit.modified_files:
        release_files = {"package.xml", "CHANGELOG.rst".lower(), "setup.py"}
        if all(
            f.filename.split("/")[-1].lower() in release_files
            for f in commit.modified_files
        ):
            return True

    return False


class ClonedRepository:
    """Manages a temporary clone of a git repository.

    The clone is stored in a temporary directory that is cleaned up when the
    instance is garbage collected.
    """

    def __init__(self, url: str, branch: str) -> None:
        """Clone a git repository into a temporary directory.

        Args:
            url (str): The Git repository URL.
            branch (str): The branch to clone.
        """
        self.url = url
        self.branch = branch
        self._temp_dir = tempfile.TemporaryDirectory()
        self.path = self._temp_dir.name

        subprocess.run(
            ["git", "clone", "--branch", branch, url, self.path],
            check=True,
        )

    def find_common_ancestor(self, branch1: str, branch2: str) -> str:
        """Find the commit hash of the common ancestor between two branches.

        Args:
            branch1 (str): First branch name.
            branch2 (str): Second branch name.

        Returns:
            str: The commit hash of the common ancestor.
        """
        for b in (branch1, branch2):
            subprocess.run(
                ["git", "fetch", "origin", f"{b}:{b}"],
                cwd=self.path,
                capture_output=True,
            )

        result = subprocess.run(
            ["git", "merge-base", branch1, branch2],
            cwd=self.path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def iterate_commits(
        self, from_commit: str, to_branch: str
    ) -> Iterator[Commit]:
        """Yield Commit instances from from_commit (exclusive) to to_branch (inclusive).

        Args:
            from_commit (str): The starting commit hash.
            to_branch (str): The ending branch name.

        Yields:
            Commit: Commit instances.

        Raises:
            ValueError: If from_commit is not an ancestor of to_branch.
        """
        try:
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", from_commit, to_branch],
                cwd=self.path,
                check=True,
            )
        except subprocess.CalledProcessError:
            raise ValueError(
                f"Commit {from_commit} is not an ancestor of {to_branch}"
            )

        result = subprocess.run(
            ["git", "rev-list", "--reverse", f"{from_commit}..{to_branch}"],
            cwd=self.path,
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            if line.strip():
                yield Commit(self.path, line.strip())


def parse_repos_file(file_path: str) -> list[Repository]:
    """Parse a YAML file containing repository information.

    Args:
        file_path (str): Path to the YAML file on disk.

    Returns:
        list[Repository]: A list of Repository class instances.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    repos = []
    if not data or "repositories" not in data:
        return repos

    for name, info in data["repositories"].items():
        repos.append(
            # Assuming all repositories are git repositories
            Repository(
                name=name,
                url=info.get("url", ""),
                branch=info.get("version", ""),
            )
        )
    return repos


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        argparse.Namespace: The parsed arguments containing `new_rosdistro` and
        `old_rosdistro`.
    """
    parser = argparse.ArgumentParser(
        description="Create a CSV file showing new commits in a ROS distribution since a previous rosdistro."
    )
    parser.add_argument(
        "--new-rosdistro",
        required=True,
        help="Path to the repository YAML file for the new ROS distribution.",
    )
    parser.add_argument(
        "--old-rosdistro",
        required=True,
        help="Path to the repository YAML file for the old ROS distribution.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output CSV file.",
    )
    return parser.parse_args()


def find_matching_repo(
    repo: Repository, repo_list: list[Repository]
) -> Repository | None:
    """Find a repository with a matching name and URL in a list of repositories.

    Args:
        repo (Repository): The repository to match.
        repo_list (list[Repository]): The list of repositories to search within.

    Returns:
        Repository | None: The matching repository if found, None otherwise.
    """
    for r in repo_list:
        if r.name == repo.name and r.url == repo.url:
            return r
    return None


def main() -> None:
    """Main entry point for the script."""
    args = parse_arguments()
    old_repos = parse_repos_file(args.old_rosdistro)
    new_repos = parse_repos_file(args.new_rosdistro)

    with open(args.output, mode="w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["name", "url", "commit_hash", "first_message_line"])

        for new_repo in new_repos:
            matching_old = find_matching_repo(new_repo, old_repos)
            if matching_old:
                print(f"\nFound match for {new_repo.name}")
            else:
                print(f"\nNo match found for {new_repo.name}, skipping")
                continue
            print(f"Cloning {new_repo.url} @ {new_repo.branch}")
            cloned_repo = ClonedRepository(url=new_repo.url, branch=new_repo.branch)

            base_commit = cloned_repo.find_common_ancestor(new_repo.branch, matching_old.branch)
            print(f"Found common ancestor between {new_repo.branch} and {matching_old.branch}: {base_commit}")
            old_commits = [c for c in cloned_repo.iterate_commits(from_commit=base_commit, to_branch=matching_old.branch) if not is_probably_release_commit(c)]
            new_commits = [c for c in cloned_repo.iterate_commits(from_commit=base_commit, to_branch=new_repo.branch) if not is_probably_release_commit(c)]
            print(f"Found {len(old_commits)} old and {len(new_commits)} new commits to search")

            print("\n--- Old Commits ---")
            for commit in old_commits:
                print(f"[{commit.hash[:7]}] {commit.first_message_line} (files: {len(commit.modified_files)}, +{commit.added_lines}/-{commit.removed_lines})")

            print("\n--- New Commits ---")
            for commit in new_commits:
                print(f"[{commit.hash[:7]}] {commit.first_message_line} (files: {len(commit.modified_files)}, +{commit.added_lines}/-{commit.removed_lines})")

            print("\n--- Probably Same Commits ---")
            for old_c in old_commits:
                for new_c in new_commits:
                    if commits_are_probably_same(old_c, new_c):
                        print(f"Old [{old_c.hash[:7]}] '{old_c.first_message_line}' <==> New [{new_c.hash[:7]}] '{new_c.first_message_line}'")

            print("\n--- Probably New Commits ---")
            for new_c in new_commits:
                if not any(commits_are_probably_same(old_c, new_c) for old_c in old_commits):
                    print(f"[{new_c.hash[:7]}] {new_c.first_message_line} (files: {len(new_c.modified_files)}, +{new_c.added_lines}/-{new_c.removed_lines})")
                    csv_writer.writerow([new_repo.name, new_repo.url, new_c.hash, new_c.first_message_line])
            # Stuff happens. Flush after every repo to save progress.
            csv_file.flush()


if __name__ == "__main__":
    main()
