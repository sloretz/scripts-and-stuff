#!/usr/bin/env python3
"""
time-to-first-touch
This script returns statistics about the time it took for maintainers to review or reply to a PR.

Example:

$ ./time-to-first-touch --repo ros2/rclpy --begin-date 2025-09-01
Date range: 2025-09-01 to 2025-09-29
Issues opened: 16
Pull requests opened: 5
Average time to first touch: 1 day, 5 hours, and 30 minutes
Maximum time to first touch: 30 days 4 hours and 6 seconds

Example --raw-data:

$ ./time-to-first-touch --repo ros2/rclpy --begin-date 2025-09-01 --raw-data
Date opened, identifier, time_to_first_touch_seconds
2025-09-04,ros2/rclpy#42,43221
2025-09-07,ros2/rclpy#43,883272
2025-09-19,ros2/rclpy#44,113
"""

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, date, timezone, timedelta
from typing import List, Tuple

import keyring
from github import Github
from github.GithubException import UnknownObjectException


@dataclass
class Data:
  """A container for a single data point."""
  identifier: str
  time_to_first_touch_seconds: int
  date_opened: datetime


def get_github_key() -> str:
    """
    Retrieves the GitHub API key from the environment or keyring.
    
    Raises:
        RuntimeError: If the key cannot be found.
        
    Returns:
        The GitHub API key.
    """
    if 'GITHUB_TOKEN' in os.environ:
        return os.environ['GITHUB_TOKEN']
    key = keyring.get_password("github-api-token", "list-collaborators")
    if key is None:
        raise RuntimeError(
            'Failed to get github api key. Please set GITHUB_TOKEN environment variable '
            'or set the key with: `keyring set github-api-token read-public-repos`'
        )
    return key


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.
    
    Raises:
        RuntimeError: If date arguments are invalid.
        
    Returns:
        The parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description='Get statistics about time to first touch on GitHub issues and PRs.'
    )
    parser.add_argument(
        '--begin-date', required=True,
        help='Starting date UTC YYYY-MM-DD (inclusive)'
    )
    parser.add_argument(
        '--end-date',
        help="Ending date UTC YYYY-MM-DD (inclusive), defaults to Today's date"
    )
    parser.add_argument(
        '--repo', required=True, action='append',
        help='One or more GitHub repos (e.g., ros2/rclpy)'
    )
    parser.add_argument(
        '--raw-data', action='store_true',
        help='Return the data as a CSV file instead of statistics'
    )
    parser.add_argument(
        '--issues', action='store_true', help='Look at data from issues'
    )
    parser.add_argument(
        '--prs', action='store_true', help='Look at data from pull requests'
    )
    parser.add_argument(
        '--exclude-maintainers', action='store_true', help='Exclude issues and PRs from people with write acces to the repository'
    )
    args = parser.parse_args()

    # Process and validate dates
    try:
        args.begin_date = datetime.strptime(args.begin_date, '%Y-%m-%d').date()
    except ValueError:
        raise RuntimeError("Invalid --begin-date format. Please use YYYY-MM-DD.")

    today = date.today()
    if args.end_date:
        try:
            args.end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            raise RuntimeError("Invalid --end-date format. Please use YYYY-MM-DD.")
    else:
        args.end_date = today

    if args.begin_date > args.end_date:
        raise RuntimeError('begin-date cannot be newer than end-date')
    if args.end_date > today:
        raise RuntimeError('end-date cannot be in the future')

    # Default to both issues and PRs if neither is specified
    if not args.issues and not args.prs:
        args.issues = True
        args.prs = True

    return args


def format_seconds(seconds: int) -> str:
    """Converts seconds into a human-readable string."""
    if seconds < 0:
        return "N/A"
    if seconds == 0:
        return "0 seconds"

    parts = []
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    if days > 0:
        parts.append(f"{int(days)} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{int(hours)} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{int(minutes)} minute{'s' if minutes != 1 else ''}")
    if secs > 0:
        parts.append(f"{int(secs)} second{'s' if secs != 1 else ''}")
    
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    return parts[0]


def fetch_data_for_repo(
    g: Github, repo_name: str, begin_date: date, end_date: date, do_issues: bool, do_prs: bool, exclude_maintainers: bool
) -> Tuple[List[Data], int, int]:
    """
    Fetches time-to-first-touch data for a given repository.

    Returns:
        A tuple containing: (list of Data objects, issue count, PR count).
    """
    try:
        repo = g.get_repo(repo_name)
    except UnknownObjectException:
        print(f"Error: Repository '{repo_name}' not found or access denied.", file=sys.stderr)
        return [], 0, 0

    maintainers = {c.login for c in repo.get_collaborators(permission='push')}
    
    results = []
    issue_count = 0
    pr_count = 0

    date_query = f"created:{begin_date.isoformat()}..{end_date.isoformat()}"
    base_query = f"repo:{repo_name} {date_query}"

    queries = []
    if do_issues:
        queries.append("type:issue")
    if do_prs:
        queries.append("type:pr")

    for type_qualifier in queries:
        query = f"{base_query} {type_qualifier}"
        items = g.search_issues(query=query, sort='created', order='asc')
        
        if type_qualifier == "type:issue":
            issue_count += items.totalCount
        else:
            pr_count += items.totalCount
        
        for item in items:
            if exclude_maintainers and item.user.login in maintainers:
                continue

            # If no one has touched it yet, pretend it was "touched" right now
            # to get some data on untouched items.
            first_touch_time = datetime.now(timezone.utc)
            
            # Find first comment by a maintainer
            for comment in item.get_comments(since=item.created_at):
                if comment.user.login in maintainers:
                    first_touch_time = comment.created_at
                    break # Comments are chronological

            # For PRs, also check reviews
            if item.pull_request:
                pr = item.as_pull_request()
                for review in pr.get_reviews():
                    if review.user and review.user.login in maintainers:
                        if review.submitted_at < first_touch_time:
                            first_touch_time = review.submitted_at
            
            time_delta = (first_touch_time - item.created_at).total_seconds()
            results.append(Data(
                identifier=f"{repo_name}#{item.number}",
                time_to_first_touch_seconds=int(time_delta),
                date_opened=item.created_at
            ))
    
    return results, issue_count, pr_count


def output_csv(raw_data: List[Data]) -> None:
    """Prints the collected data in CSV format."""
    print('Date opened,identifier,time_to_first_touch_seconds')
    for d in sorted(raw_data, key=lambda x: x.date_opened):
        date_str = d.date_opened.strftime('%Y-%m-%d')
        print(f"{date_str},{d.identifier},{d.time_to_first_touch_seconds}")


def output_statistics(
    raw_data: List[Data], begin_date: date, end_date: date, issue_count: int, pr_count: int
) -> None:
    """Calculates and prints summary statistics."""
    print(f"Date range: {begin_date.isoformat()} to {end_date.isoformat()}")
    if issue_count > 0:
        print(f"Issues opened: {issue_count}")
    if pr_count > 0:
        print(f"Pull requests opened: {pr_count}")
    
    if not raw_data:
        print("No community issues or PRs with maintainer responses found in this period.")
        return

    total_seconds = sum(d.time_to_first_touch_seconds for d in raw_data)
    max_seconds = max(d.time_to_first_touch_seconds for d in raw_data)
    avg_seconds = total_seconds / len(raw_data)

    print(f"Average time to first touch: {format_seconds(avg_seconds)}")
    print(f"Maximum time to first touch: {format_seconds(max_seconds)}")


def main():
  """Main script execution."""
  try:
      args = parse_arguments()
      github_api = Github(get_github_key())
  except RuntimeError as e:
      print(f"Error: {e}", file=sys.stderr)
      sys.exit(1)
  
  all_data = []
  total_issues = 0
  total_prs = 0
  
  for repo in args.repo:
    print(f"Fetching data for {repo}...", file=sys.stderr)
    repo_data, issue_count, pr_count = fetch_data_for_repo(
        github_api, repo, args.begin_date, args.end_date, args.issues, args.prs, args.exclude_maintainers
    )
    all_data.extend(repo_data)
    total_issues += issue_count
    total_prs += pr_count
                    
  if args.raw_data:
    output_csv(all_data)
  else:
    output_statistics(all_data, args.begin_date, args.end_date, total_issues, total_prs)
    

if __name__ == '__main__':
  main()
