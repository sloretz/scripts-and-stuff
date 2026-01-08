#!/usr/bin/env python3

import requests
import json
import time
import keyring
import os
import argparse
from dataclasses import dataclass
from functools import lru_cache

@dataclass
class Repository:
    owner: str
    name: str

@lru_cache(maxsize=1)
def get_api_key():
    """
    Retrieves the GitHub token from the system keyring.
    Cached so the keyring is only accessed once.
    """
    key = keyring.get_password("github-api-token", "may-search-github")
    if key is None:
        raise RuntimeError('Failed to get github api key. Ensure it is set in keyring.')
    return key

def make_graphql_request(query, variables):
    """Handles authentication, URL management, and rate limiting internally."""
    url = "https://api.github.com/graphql"
    # This call now hits the cache after the first execution
    token = get_api_key()
    headers = {"Authorization": f"Bearer {token}"}

    while True:
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        
        if response.status_code in [403, 429]:
            retry_after = response.headers.get("retry-after")
            wait_time = int(retry_after) if retry_after else max(int(response.headers.get("x-ratelimit-reset", time.time() + 60)) - int(time.time()), 60)
            print(f"Rate limit hit. Sleeping for {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        remaining = int(response.headers.get("x-ratelimit-remaining", 1))
        if remaining == 0:
            reset_at = int(response.headers.get("x-ratelimit-reset", 0))
            wait_time = max(reset_at - int(time.time()), 1)
            print(f"Primary rate limit exhausted. Sleeping until reset ({wait_time}s)...")
            time.sleep(wait_time)
            continue

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Query failed with status {response.status_code}: {response.text}")

def get_all_repo_issues(repo: Repository):
    """Fetches all open issues and comments for a specific Repository dataclass."""
    query = """
    query($owner: String!, $name: String!, $issueCursor: String) {
      repository(owner: $owner, name: $name) {
        issues(states: OPEN, first: 50, after: $issueCursor) {
          pageInfo { hasNextPage, endCursor }
          nodes {
            title
            body
            author { login }
            comments(first: 50) {
              nodes {
                body
                author { login }
              }
            }
          }
        }
      }
    }
    """
    repo_issues = []
    cursor = None
    
    while True:
        variables = {"owner": repo.owner, "name": repo.name, "issueCursor": cursor}
        result = make_graphql_request(query, variables)
        
        data = result.get('data', {}).get('repository')
        if not data:
            break

        issue_data = data['issues']
        for node in issue_data['nodes']:
            repo_issues.append({
                "title": node['title'],
                "author": node['author']['login'] if node['author'] else "Ghost",
                "body": node['body'],
                "comments": [
                    {
                        "author": c['author']['login'] if c['author'] else "Ghost",
                        "body": c['body']
                    } for c in node['comments']['nodes']
                ]
            })

        if not issue_data['pageInfo']['hasNextPage']:
            break
        cursor = issue_data['pageInfo']['endCursor']
        
    return repo_issues

def write_issues_to_file(issues, repo: Repository, output_dir):
    """Saves the issue list to a JSON file."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    filename = f"{repo.owner}__{repo.name}.json"
    file_path = os.path.join(output_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(issues, f, indent=4, ensure_ascii=False)
    
    return file_path

def parse_arguments():
    """Parses command line arguments and converts repo strings into Repository dataclasses."""
    parser = argparse.ArgumentParser(description="Download GitHub issues via GraphQL API")
    parser.add_argument(
        "--output", 
        default="github_exports", 
        help="Directory to save the JSON results (default: github_exports)"
    )
    parser.add_argument(
        "repos", 
        nargs="+", 
        help="One or more repository names in 'org/repo' format"
    )
    
    args = parser.parse_args()
    
    processed_repos = []
    for r in args.repos:
        if "/" not in r:
            parser.error(f"Repository '{r}' must be in 'owner/name' format.")
        owner, name = r.split("/", 1)
        processed_repos.append(Repository(owner=owner, name=name))
    
    args.repos = processed_repos
    return args

def main():
    """Main execution flow."""
    args = parse_arguments()

    for repo in args.repos:
        try:
            print(f"Processing: {repo.owner}/{repo.name}...")
            
            issues = get_all_repo_issues(repo)
            saved_path = write_issues_to_file(issues, repo, args.output)
            
            print(f"Successfully wrote {len(issues)} issues to {saved_path}")
            
        except Exception as e:
            print(f"Failed to process {repo.owner}/{repo.name}: {e}")

if __name__ == "__main__":
    main()
