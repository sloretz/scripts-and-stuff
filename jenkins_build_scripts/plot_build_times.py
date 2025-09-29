#!/usr/bin/env python3
"""
Fetches and plots Jenkins build duration statistics over a specified period.

This script connects to a Jenkins server, retrieves build history for a
given job, and plots the build durations over time using matplotlib.
"""

import argparse
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import List, Optional
import time

import keyring
from jenkinsapi.jenkins import Jenkins


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        An object containing the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Fetch and plot Jenkins job build times."
    )
    parser.add_argument(
        "--jenkins-url",
        default="https://ci.ros2.org/",
        help="The URL of the Jenkins server."
    )
    parser.add_argument(
        "--job-name",
        default="ci_linux",
        help="The name of the Jenkins job to analyze."
    )
    parser.add_argument(
        "--username",
        default=None,
        help="A jenkins username to log in as (requires a jenkins token in keyring)"
    )
    parser.add_argument(
        "--days-to-fetch",
        type=int,
        default=30,
        help="The number of past days to fetch build data for."
    )
    return parser.parse_args()


def get_jenkins_token() -> Optional[str]:
    """Retrieve the Jenkins API token from the system's keyring.

    To set the token, use a tool like `keyring` from the command line:
    `keyring set jenkins-api-token job-statistics`

    Returns:
        The API token string, or None if not found.
    """
    return keyring.get_password("jenkins-api-token", "job-statistics")


@dataclass
class BuildDuration:
    """A simple data class to hold build information."""
    date: datetime
    duration_seconds: float


def plot_build_times(builds: List[BuildDuration], job_name: str, days: int) -> None:
    """Plot build durations over time using matplotlib.

    Args:
        builds: A list of BuildDuration objects.
        job_name: The name of the Jenkins job.
        days: The number of days the data was fetched for.
    """
    if not builds:
        print("No build data found in the specified date range to plot.")
        return

    # This can raise an ImportError if matplotlib is not installed.
    import matplotlib.pyplot as plt

    builds.sort(key=lambda b: b.date)
    timestamps = [b.date for b in builds]
    durations = [b.duration_seconds for b in builds]

    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, durations, marker='o', linestyle='-')
    plt.title(f"Build Times for '{job_name}' (Last {days} Days)")
    plt.xlabel("Date")
    plt.ylabel("Build Duration (seconds)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def get_build_data(
    jenkins_url: str,
    job_name: str,
    days_to_fetch: int,
    username: Optional[str],
    api_token: Optional[str]
) -> List[BuildDuration]:
    """Fetch build data from a Jenkins job.

    Args:
        jenkins_url: The URL of the Jenkins server.
        job_name: The name of the job to fetch builds from.
        days_to_fetch: The number of past days of builds to retrieve.
        api_token: The API token for Jenkins authentication.

    Returns:
        A list of BuildDuration objects.
    """
    print(f"Connecting to Jenkins at {jenkins_url}...")
    # This can raise various network-related exceptions.
    jenkins = Jenkins(jenkins_url, username=username, password=api_token)

    print(f"Fetching job '{job_name}'...")
    # This can raise a KeyError if the job is not found.
    job = jenkins[job_name]

    build_data = []
    start_date = datetime.now(timezone.utc) - timedelta(days=days_to_fetch)

    print(f"Fetching builds for '{job_name}' from the last {days_to_fetch} days...")

    # This can raise various jenkinsapi or network exceptions.
    for build_id in job.get_build_ids():
        # Rate limiting
        time.sleep(0.5)
        build = job.get_build(build_id)
        build_timestamp = build.get_timestamp()

        if build_timestamp > start_date:
            duration_seconds = build.get_duration().total_seconds()
            build_data.append(
                BuildDuration(
                    date=build_timestamp,
                    duration_seconds=duration_seconds
                )
            )
            print(f"  - Build #{build.get_number()}: {duration_seconds:.2f} seconds")
        else:
            # Builds are ordered newest to oldest, so we can stop early.
            break
    return build_data


def main() -> None:
    """Main execution function."""
    args = parse_arguments()

    token=None
    if args.username:
        token = get_jenkins_token()

    try:
        builds = get_build_data(
            jenkins_url=args.jenkins_url,
            job_name=args.job_name,
            days_to_fetch=args.days_to_fetch,
            username=args.username,
            api_token=token
        )

        try:
            plot_build_times(builds, args.job_name, args.days_to_fetch)
        except ImportError:
            print("\nMatplotlib not found. Cannot generate plot.")
            print("To install: pip install matplotlib")
            print("\nBuild data (timestamp, duration in seconds):")
            for build in sorted(builds, key=lambda b: b.date):
                print(
                    f"{build.date.strftime('%Y-%m-%d %H:%M:%S')}, "
                    f"{build.duration_seconds:.2f}"
                )

    except Exception as e:
        print(f"\nAn error occurred: {e}")


if __name__ == '__main__':
    main()
