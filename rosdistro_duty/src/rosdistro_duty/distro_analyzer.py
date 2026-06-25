import yaml

class DistroDiffAnalyzer:
    """Analyzes differences between two versions of a rosdistro distribution.yaml file."""

    def find_modified_repositories(self, head_content: str, base_content: str) -> dict[str, dict]:
        """
        Compares head and base distribution.yaml contents.
        Returns a dictionary of new or modified repository source stanzas:
        { 'repo_name': { 'type': 'git', 'url': '...', 'version': '...' } }
        """
        head_data = yaml.safe_load(head_content) or {}
        base_data = yaml.safe_load(base_content) or {}

        head_repos = head_data.get("repositories", {})
        base_repos = base_data.get("repositories", {})

        modified_repos = {}
        for r_name, r_meta in head_repos.items():
            source_meta = r_meta.get("source")
            if not source_meta:
                continue

            base_repo_meta = base_repos.get(r_name)
            if not base_repo_meta:
                modified_repos[r_name] = source_meta
            else:
                base_source_meta = base_repo_meta.get("source")
                if not base_source_meta or base_source_meta != source_meta:
                    modified_repos[r_name] = source_meta

        return modified_repos
