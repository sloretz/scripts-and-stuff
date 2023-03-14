#!/usr/bin/env python3

# Given a CSV file where the leftmost column are checkboxes indicating if the
# issues and PRs should be in a report, output markdown.

import argparse
import csv

def row_to_md(
        include_in_report,
        title,
        url,
        short_link,
        state,
        type_,
        updated_at,
        created_at,
        closed_at,
        user
    ):
    if state == "open":
        if type_ == "issues":
            status = "in progress"
        elif type_ == "pull":
            status = "in review"
        else:
            raise ValueError(f"Unknown type: ${type}")
    elif state == "closed":
        if type_ == "issues":
            status = "closed"
        elif type_ == "pull":
            status = "merged"
        else:
            raise ValueError(f"Unknown type: ${type}")
    else:
        raise ValueError(f"Unknown state: ${state}")
    return [
        f'* [{short_link}]({url})',
        f'   * {title} ({status})',
    ]


def get_repo(csv_row):
    """Given a csv row, return the repo it's part of."""
    short_link = csv_row[3]
    return short_link.split('#')[0]


def to_md(filename):
    repo_rows = {}
    with open(filename) as csvfile:
        for row in csv.reader(csvfile):
            if 'TRUE' == row[0]:
                repo = get_repo(row)
                if repo not in repo_rows:
                    repo_rows[repo] = []
                repo_rows[repo].append(row)

    report = []
    for repo in sorted(repo_rows.keys()):
        report.append(f"* {repo}")
        for row in repo_rows[repo]:
            for md_row in row_to_md(*row):
                report.append("   " + md_row)
    return '\n'.join(report)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')
    args = parser.parse_args();

    # Output a markdown file to stdout
    print(to_md(args.filename))

if __name__ == "__main__":
    main()
