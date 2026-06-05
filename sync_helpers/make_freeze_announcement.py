#!/usr/bin/env python3

import argparse
from datetime import date, timedelta
from string import Template

import requests


title_template = "Preparing for ${distro_title} Sync ${sync_target_date}"


body_template = """Hello ${distro_title} maintainers!

Starting now, I will be holding new ${distro_title} [ros/rosdistro](https://github.com/ros/rosdistro/) release PRs with a plan to sync ROS ${distro_title} packages to the main apt repo on ${sync_target_date}. Please comment here if there are any issues I should know about before performing the sync.

There are currently [${num_packages} packages](https://repo.ros2.org/status_page/ros_${distro_lower}_default.html?q=SYNC) waiting to sync and [${num_regressions} regressions](https://repo.ros2.org/status_page/ros_${distro_lower}_default.html?q=REGRESSION).
"""


slack_template = """(@ @ FYI) ${distro_title} is in a sync hold. If you happen to review a ros/rosdistro PR then please leave a comment like

```
[Holding for ${distro_title} sync](https://discourse.ros.org/t/preparing-for-${distro_lower}-sync-${sync_target_date}/)
```
"""

def parse_arguments():
    parser = argparse.ArgumentParser(description='Prepare freeze announcement.')
    parser.add_argument('--rosdistro', required=True, help='The name of the ROS distribution (e.g., humble, rolling).')
    return parser.parse_args()


def main():
    args = parse_arguments()
    rosdistro = args.rosdistro
    distro_lower = rosdistro.lower()
    distro_title = rosdistro.capitalize()

    mapping = {
        'distro_lower': distro_lower,
        'distro_title': distro_title,
        'num_packages': '???',
        'num_regressions': '???',
        'sync_target_date': '???'
    }

    try:
        r = requests.get(f'https://repo.ros2.org/status_page/ros_{distro_lower}_default.html')
        if r.status_code == 200:
            content = r.text
            sync = 0
            regression = 0
            for line in content.split('\n'):
                if line.startswith('<tr><td><div>'):
                    if 'SYNC' in line:
                        sync += 1
                    if 'REGRESSION' in line:
                        regression += 1
            mapping['num_packages'] = sync
            mapping['num_regressions'] = regression
        else:
            print("Failed to fetch page :(", r)
    except requests.RequestException as e:
        print(f"Failed to fetch page due to connection error: {e}")

    sync_date = date.today() + timedelta(days=2)
    while sync_date.weekday() > 4:
        sync_date += timedelta(days=1)
    mapping['sync_target_date'] = sync_date.strftime("%Y-%m-%d")

    print('----------')
    print(Template(title_template).substitute(mapping))
    print('----------')
    print(Template(body_template).substitute(mapping))
    print('----------')
    print(Template(slack_template).substitute(mapping))


if __name__ == '__main__':
    main()
