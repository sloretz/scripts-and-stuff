#!/usr/bin/env python3

# Moddified from a script I got from Adissu

import csv
import keyring
from github import Github
import re
from collections import namedtuple
import argparse
import sys
import io


def get_api_key():
    key = keyring.get_password("github-api-token", "may-search-github")
    if key is None:
        raise RuntimeError('Failed to get github api key')
    return key

AUTHORS = [
    "hidmic",
    "sloretz",
    "cottsay",
    "aaronchongth",
    "gbiggs",
]

GithubUrl = namedtuple("GithubUrl", ["org", "repo", "url_type",  "number"])


def parse_url(url):
    m = re.match(r".*github.com/(.*)/(.*)/(.*)/(.*)", url)
    return GithubUrl(*m.groups())


def to_csv(issues):
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    for issue in issues:
        gh_url = parse_url(issue.html_url)
        csv_writer.writerow((
            "FALSE",  # For a checkbox
            issue.title,
            issue.html_url,
            f"{gh_url.org}/{gh_url.repo}#{gh_url.number}",
            str(issue.state),
            gh_url.url_type,
            issue.updated_at,
            issue.created_at,
            str(issue.closed_at),
            issue.user.login))

    return csv_buffer.getvalue()


IGNORE_REPOS = [
    "open-rmf/.*",
    "osrf/ovc.",
    "ros-infrastructure/.*",
    "ros/rosdistro/.*",
    "ChrisScianna/.*",
]


def filter_issue(issue):
    """Return true if issue is to be included in report"""

    repo = re.match(r".*github.com/(.*)", issue.html_url)[1]
    for pattern in IGNORE_REPOS:
        if re.match(pattern, repo):
            return False

    return True


def query_by_author(author, start_date):
    query_str = f'author:{author} updated:>{start_date}'

    g = Github(get_api_key())
    issues = g.search_issues(query_str, sort="created", order="asc")

    filtered_issues = [issue for issue in issues if filter_issue(issue)]
    yield from sorted(
        filtered_issues, key=lambda issue: parse_url(issue.html_url).repo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('start_date')
    args = parser.parse_args();

    # Output a CSV file to stdout
    for author in AUTHORS:
        print(to_csv(query_by_author(author, args.start_date)))

if __name__ == "__main__":
    main()
