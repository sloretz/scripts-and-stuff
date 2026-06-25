import requests
from github import Github

class GitHubClient:
    """Handles communications with the GitHub API."""

    def __init__(self, token: str):
        self.token = token
        self._g = Github(token)

    def fetch_changed_files(self, owner: str, repo_name: str, pr_num: int) -> list:
        """Fetches the list of files changed in a pull request."""
        repo = self._g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_num)
        return list(pr.get_files())

    def get_pr_commits(self, owner: str, repo_name: str, pr_num: int) -> tuple[str, str]:
        """Returns the base and head SHAs for the pull request."""
        repo = self._g.get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_num)
        return pr.base.sha, pr.head.sha

    def fetch_raw_content(self, owner: str, repo_name: str, sha: str, filename: str) -> str:
        """Downloads the raw text content of a file at a specific commit."""
        headers = {"Authorization": f"token {self.token}"} if self.token else {}
        url = f"https://raw.githubusercontent.com/{owner}/{repo_name}/{sha}/{filename}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text
