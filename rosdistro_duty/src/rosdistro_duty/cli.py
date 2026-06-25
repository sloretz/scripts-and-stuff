import argparse
import sys
import re
from .credentials import CredentialsManager
from .github_client import GitHubClient
from .distro_analyzer import DistroDiffAnalyzer
from .repository import LocalRepository
from .inspector import PackageInspector
from .reviewer import GeminiReviewer
from .reporter import MarkdownReportGenerator

def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Parses a GitHub pull request URL and returns (owner, repo, pr_number)."""
    pattern = r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, url)
    if not match:
        raise ValueError(f"Invalid GitHub Pull Request URL: {url}")
    owner, repo, pr_num = match.groups()
    return owner, repo, int(pr_num)

def get_target_repositories(
    github_client: GitHubClient,
    diff_analyzer: DistroDiffAnalyzer,
    owner: str,
    repo_name: str,
    pr_num: int,
) -> dict[str, dict]:
    """Finds all new/modified source repositories in the pull request."""
    # Get base and head shas to fetch raw contents
    base_sha, head_sha = github_client.get_pr_commits(owner, repo_name, pr_num)
    
    # Get the files changed
    changed_files = github_client.fetch_changed_files(owner, repo_name, pr_num)
    
    target_repos = {}
    for file in changed_files:
        if not file.filename.endswith("distribution.yaml"):
            continue

        print(f"Analyzing changes in {file.filename}...", file=sys.stderr)

        # Fetch file contents at head and base commits
        head_content = github_client.fetch_raw_content(owner, repo_name, head_sha, file.filename)
        try:
            base_content = github_client.fetch_raw_content(owner, repo_name, base_sha, file.filename)
        except Exception:
            base_content = ""

        # Diff distribution.yaml files
        repos = diff_analyzer.find_modified_repositories(head_content, base_content)
        target_repos.update(repos)
        
    return target_repos


def review_repository(
    repo_id: str,
    source_meta: dict,
    reviewer: GeminiReviewer,
    reporter: MarkdownReportGenerator,
) -> None:
    """Clones, inspects, reviews, and reports on a single repository."""
    url = source_meta.get("url")
    version = source_meta.get("version", "master")

    if not url:
        print(
            f"Warning: Repository '{repo_id}' does not have a source URL. Skipping.",
            file=sys.stderr,
        )
        return

    # Create a temporary directory for cloning via context manager
    with LocalRepository(url=url, version=version) as local_repo:
        if not local_repo.cloned_successfully:
            print(
                f"Error: Cloning repository '{repo_id}' from {url} (version: {version}) failed: {local_repo.error_message}",
                file=sys.stderr,
                flush=True,
            )
            return

        # Inspect the cloned repo
        inspector = PackageInspector(repo_path=local_repo.path)
        inspection_results = inspector.inspect()

        # Run Gemini review
        if inspection_results.packages:
            gemini_results = reviewer.review_packages(repo_id, inspection_results.packages)
        else:
            gemini_results = {
                "packages": [],
                "overall_license_evaluation": {
                    "osi_approved": False,
                    "comments": "No ROS packages (package.xml) found in the repository.",
                },
            }

        # Generate and print the report
        report = reporter.generate(
            repo_id=repo_id,
            url=url,
            version=version,
            inspection=inspection_results,
            gemini_results=gemini_results,
        )
        print(report)


def main():
    parser = argparse.ArgumentParser(
        description="Review new package additions in a rosdistro Pull Request."
    )
    parser.add_argument(
        "pr_url",
        help="The GitHub Pull Request URL (e.g., https://github.com/ros/rosdistro/pull/51902)",
    )
    args = parser.parse_args()

    # Retrieve credentials
    creds = CredentialsManager()
    github_token = creds.get_github_token()
    gemini_key = creds.get_gemini_api_key()

    # Parse PR URL
    owner, repo_name, pr_num = parse_pr_url(args.pr_url)

    # Instantiate decoupled clients
    github_client = GitHubClient(token=github_token)
    diff_analyzer = DistroDiffAnalyzer()
    reviewer = GeminiReviewer(api_key=gemini_key)
    reporter = MarkdownReportGenerator()

    # Find modified repos in the PR
    target_repos = get_target_repositories(
        github_client, diff_analyzer, owner, repo_name, pr_num
    )

    if not target_repos:
        print(
            "No new or modified source repositories found in the pull request.",
            file=sys.stderr,
        )
        sys.exit(0)

    print(
        f"Found {len(target_repos)} modified repository/repositories to review.",
        file=sys.stderr,
    )

    # Process each target repository
    for repo_id, source_meta in target_repos.items():
        review_repository(repo_id, source_meta, reviewer, reporter)


if __name__ == "__main__":
    main()
