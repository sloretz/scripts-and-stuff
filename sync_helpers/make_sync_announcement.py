#!/usr/bin/env python3

import argparse
from datetime import date, timedelta
import re
from string import Template
import sys

import requests
import rosdistro


title_template = "New Packages for ${distro_title} ${sync_date}"


body_template = """We’re happy to announce **${num_added}** new packages and **${num_updated}** updates are now available in ROS ${distro_title}. This sync was tagged as [`${distro_lower}/${sync_date}`](https://github.com/ros/rosdistro/blob/${distro_lower}/${sync_date}/${distro_lower}/distribution.yaml).

Thank you to every maintainer and contributor who made these updates available!

## Package Updates for ROS ${distro_title}

${details_sections}

Thanks to all ROS maintainers who make packages available to the ROS community. The above list of packages was made possible by the work of the following maintainers:

${maintainers}
"""


zulip_template = "${distro_title} packages have been synced: https://discourse.openrobotics.org/t/new-packages-for-${distro_lower}-${sync_date}/ - no need to hold ${distro_title} ros/rosdistro PRs anymore."


reply_template = "The [sync is out](https://discourse.openrobotics.org/t/new-packages-for-${distro_lower}-${sync_date}/) :tada: . Now is a great time to make releases for the next sync"


arch_details_template = """[details=Updates to Ubuntu ${suite_title} (${arch})]

### Added Packages [${num_added}]:

${added_packages}

### Updated Packages [${num_updated}]:

${updated_packages}

### Removed Packages [${num_removed}]:

${removed_packages}
[/details]"""


def non_dbgsym_pkgs(content, distro_lower):
    """Return all lines that are non dbgsym packages"""
    for line in content.split('\n'):
        pkg_line = re.match(rf'^ \* \[?(ros-{distro_lower}-[-a-z0-9]*)\]?\(?.*\)?:.+$', line)
        if not pkg_line:
            # print('skipping', repr(line))
            continue
        if pkg_line and pkg_line.group(1).endswith('-dbgsym'):
            # print('skipping', pkg_line.group(1))
            continue
        else:
            yield line


def get_ubuntu_codename(distro_lower):
    index = rosdistro.get_index(rosdistro.get_index_url())
    try:
        cached_dist = rosdistro.get_cached_distribution(index, distro_lower)
    except RuntimeError as e:
        sys.exit(f"Failed to get distribution data: {e}")

    dist_file = cached_dist._distribution_file
    data = dist_file.get_data()
    # Override version to 1 for ReleaseFile constructor compatibility
    data['version'] = 1

    release_file = rosdistro.ReleaseFile(distro_lower, data)

    if 'ubuntu' not in release_file.platforms or not release_file.platforms['ubuntu']:
        sys.exit(f"Could not find Ubuntu release suite for {distro_lower} in rosdistro")
    return release_file.platforms['ubuntu'][0]


def parse_arguments():
    """Parse command-line arguments for the script."""
    parser = argparse.ArgumentParser(
        description='Make sync announcement.'
    )
    parser.add_argument(
        '--rosdistro',
        required=True,
        help='The name of the ROS distribution (e.g., noetic, humble, rolling).'
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    rosdistro = args.rosdistro
    distro_lower = rosdistro.lower()
    distro_title = rosdistro.capitalize()
    distro_char = distro_lower[0].upper()

    r = requests.get(f'https://build.ros2.org/job/{distro_char}rel_sync-packages-to-main/lastSuccessfulBuild/consoleText')
    if r.status_code != 200:
        sys.exit(f"Failed to fetch page :( status code {r.status_code}")

    content = r.text
    sync_date = re.search('computed at ([0-9]{4}-[0-9]{2}-[0-9]{2})', content).group(1)

    suite = get_ubuntu_codename(distro_lower)

    header_expr = re.compile(
        r"Difference between 'file:///var/repos/ubuntu/main/dists/([a-z]+)/main/binary-([a-z0-9]+)/Packages'"
    )
    matches = list(header_expr.finditer(content))

    blocks = []
    for i, m in enumerate(matches):
        m_suite = m.group(1)
        m_arch = m.group(2)
        if m_suite != suite:
            continue

        start_idx = m.start()
        if i + 1 < len(matches):
            end_idx = matches[i + 1].start()
        else:
            end_idx = len(content)

        block_content = content[start_idx:end_idx]
        blocks.append((m_arch, block_content))

    if not blocks:
        sys.exit(f"No sync architecture blocks found for suite '{suite}' in the logs.")

    all_added_pkgs = set()
    all_updated_pkgs = set()
    all_removed_pkgs = set()
    all_maintainers = set()

    details_sections = []
    suite_title = suite.capitalize()

    for arch, block_content in blocks:
        added_match = re.search(r'### Added Packages \[[0-9]+\]', block_content)
        updated_match = re.search(r'### Updated Packages \[[0-9]+\]', block_content)
        removed_match = re.search(r'### Removed Packages \[[0-9]+\]', block_content)
        maintainers_match = re.search('Thanks to all ROS maintainers', block_content)

        if not (added_match and updated_match and removed_match and maintainers_match):
            continue

        added_packages = []
        for line in non_dbgsym_pkgs(block_content[added_match.end():updated_match.start()], distro_lower):
            added_packages.append(line)
            pkg_line = re.match(rf'^ \* \[?(ros-{distro_lower}-[-a-z0-9]*)\]?\(?.*\)?:.+$', line)
            if pkg_line:
                all_added_pkgs.add(pkg_line.group(1))

        updated_packages = []
        for line in non_dbgsym_pkgs(block_content[updated_match.end():removed_match.start()], distro_lower):
            updated_packages.append(line)
            pkg_line = re.match(rf'^ \* \[?(ros-{distro_lower}-[-a-z0-9]*)\]?\(?.*\)?:.+$', line)
            if pkg_line:
                all_updated_pkgs.add(pkg_line.group(1))

        removed_packages = []
        for line in non_dbgsym_pkgs(block_content[removed_match.end():maintainers_match.start()], distro_lower):
            removed_packages.append(line)
            pkg_line = re.match(rf'^ \* \[?(ros-{distro_lower}-[-a-z0-9]*)\]?\(?.*\)?:.+$', line)
            if pkg_line:
                all_removed_pkgs.add(pkg_line.group(1))

        if not added_packages and not updated_packages and not removed_packages:
            continue

        for line in block_content[maintainers_match.start():].split('\n'):
            if line.startswith(' * '):
                name = line[3:].strip().strip('"')
                if name:
                    all_maintainers.add(name)

        arch_mapping = {
            'suite_title': suite_title,
            'arch': arch,
            'num_added': len(added_packages),
            'added_packages': '\n'.join(added_packages) if added_packages else '',
            'num_updated': len(updated_packages),
            'updated_packages': '\n'.join(updated_packages) if updated_packages else '',
            'num_removed': len(removed_packages),
            'removed_packages': '\n'.join(removed_packages) if removed_packages else '',
        }
        details_sections.append(Template(arch_details_template).substitute(arch_mapping))

    sorted_maintainers = sorted(list(all_maintainers), key=lambda x: x.lower())
    maintainers_str = '\n'.join([f" * {name}" for name in sorted_maintainers])

    mapping = {
        'distro_lower': distro_lower,
        'distro_title': distro_title,
        'sync_date': sync_date,
        'num_added': len(all_added_pkgs),
        'num_updated': len(all_updated_pkgs),
        'details_sections': '\n\n'.join(details_sections),
        'maintainers': maintainers_str,
    }
    print(f"https://discourse.openrobotics.org/c/ros/ros-announcements-news/112          release        {distro_lower}")
    print('----------')
    print(Template(title_template).substitute(mapping))
    print('----------')
    print(Template(body_template).substitute(mapping))
    print('----------')
    print(Template(zulip_template).substitute(mapping))
    print('----------')
    print(Template(reply_template).substitute(mapping))


if __name__ == '__main__':
    main()

