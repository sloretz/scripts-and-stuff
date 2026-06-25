import os
import keyring

class CredentialsManager:
    """Manages retrieving API tokens and keys from the environment or keyring."""

    def get_github_token(self) -> str:
        """Retrieves the GitHub API key from the environment or keyring."""
        if "GITHUB_TOKEN" in os.environ:
            return os.environ["GITHUB_TOKEN"]
        return keyring.get_password("github-api-token", "read-public-repos")

    def get_gemini_api_key(self) -> str:
        """Retrieves the Gemini API key from the environment or keyring."""
        if "GEMINI_API_KEY" in os.environ:
            return os.environ["GEMINI_API_KEY"]
        return keyring.get_password("gemini", "api-key")
