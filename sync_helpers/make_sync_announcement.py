#!/usr/bin/env python3

from datetime import date, timedelta
import re
from string import Template
import sys

import requests


title_template = "New Packages for Noetic ${sync_date}"


body_template = """We’re happy to announce **${num_added}** new packages and **${num_updated}** updates are now available in ROS Noetic. This sync was tagged as [`noetic/${sync_date}`](https://github.com/ros/rosdistro/blob/noetic/${sync_date}/noetic/distribution.yaml).

Thank you to every maintainer and contributor who made these updates available!

## Package Updates for ROS Noetic

### Added Packages [${num_added}]:

${added_packages}

### Updated Packages [${num_updated}]:

${updated_packages}

### Removed Packages [${num_removed}]:

${removed_packages}
Thanks to all ROS maintainers who make packages available to the ROS community. The above list of packages was made possible by the work of the following maintainers:

${maintainers}
"""


slack_template = "(@ @ FYI) Noetic packages have been synced: https://discourse.ros.org/t/new-packages-for-noetic-${sync_date}/ - no need to hold Noetic ros/rosdistro PRs anymore."


reply_template = "The [sync is out](https://discourse.ros.org/t/new-packages-for-noetic-${sync_date}/) :tada: . Now is a great time to make releases for the next sync"


def non_dbgsym_pkgs(content):
    """Return all lines that are non dbgsym packages"""
    for line in content.split('\n'):
        pkg_line = re.match('^ \* \[?(ros-noetic-[-a-z0-9]*)\]?\(?.*\)?:.+$', line)
        if not pkg_line:
            # print('skipping', repr(line))
            continue
        if pkg_line and pkg_line.group(1).endswith('-dbgsym'):
            # print('skipping', pkg_line.group(1))
            continue
        else:
            yield line


def main():
    r = requests.get('https://build.ros.org/job/Nrel_sync-packages-to-main/lastSuccessfulBuild/consoleText')
    if r.status_code != 200:
        sys.exit("Failed to fetch page :(", r)

    content = r.text
    sync_date = re.search('computed at ([0-9]{4}-[0-9]{2}-[0-9]{2})', content).group(1)

    start_pattern = "Difference between 'file:///var/repos/ubuntu/main/dists/focal/main/binary-amd64/Packages' and 'file:///var/repos/ubuntu/testing/dists/focal/main/binary-amd64/Packages'"
    end_pattern = "Difference between 'file:///var/repos/ubuntu/main/dists/focal/main/binary-arm64/Packages' and 'file:///var/repos/ubuntu/testing/dists/focal/main/binary-arm64/Packages'"

    start_text = re.search(start_pattern, content).start()
    end_text = re.search(end_pattern, content).start()
    content = content[start_text:end_text]
    
    added_match = re.search('### Added Packages \[[0-9]+\]', content)
    updated_match = re.search('### Updated Packages \[[0-9]+\]', content)
    removed_match = re.search('### Removed Packages \[[0-9]+\]', content)
    maintainers_match = re.search('Thanks to all ROS maintainers', content)

    added_packages = []
    for line in non_dbgsym_pkgs(content[added_match.end():updated_match.start()]):
        added_packages.append(line)

    updated_packages = []
    for line in non_dbgsym_pkgs(content[updated_match.end():removed_match.start()]):
        updated_packages.append(line)

    removed_packages = []
    for line in non_dbgsym_pkgs(content[removed_match.end():maintainers_match.start()]):
        removed_packages.append(line)

    maintainers = []
    for line in content[maintainers_match.start():].split('\n'):
        if line.startswith(' * '):
            maintainers.append(line)

    mapping = {
        'sync_date': sync_date,
        'num_added': len(added_packages),
        'num_updated': len(updated_packages),
        'num_removed': len(removed_packages),
        'added_packages': '\n'.join(added_packages),
        'updated_packages': '\n'.join(updated_packages),
        'removed_packages': '\n'.join(removed_packages),
        'maintainers': '\n'.join(maintainers),
    }
    print("https://discourse.ros.org/c/general/8          release        noetic")
    print('----------')
    print(Template(title_template).substitute(mapping))
    print('----------')
    print(Template(body_template).substitute(mapping))
    print('----------')
    print(Template(slack_template).substitute(mapping))
    print('----------')
    print(Template(reply_template).substitute(mapping))


if __name__ == '__main__':
    main()

