#!/usr/bin/env python3

from datetime import date, timedelta
from string import Template

import requests


title_template = "Preparing for Noetic Sync ${sync_target_date}"


body_template = """Hello Noetic maintainers!

Starting now, I will be holding new Noetic [ros/rosdistro](https://github.com/ros/rosdistro/) release PRs with a plan to sync ROS Noetic packages to the main apt repo on ${sync_target_date}. Please comment here if there are any issues I should know about before performing the sync.

There are currently [${num_packages} packages](http://repositories.ros.org/status_page/ros_noetic_default.html?q=SYNC) waiting to sync and [${num_regressions} regressions](http://repositories.ros.org/status_page/ros_noetic_default.html?q=REGRESSION).
"""


slack_template = """(@ @ FYI) Noetic is in a sync hold. If you happen to review a ros/rosdistro PR then please leave a comment like

```
[Holding for Noetic sync](https://discourse.ros.org/t/preparing-for-noetic-sync-${sync_target_date}/)
```
"""

def main():

    mapping = {
        'num_packages': '???',
        'num_regressions': '???',
        'sync_target_date': '???'
    }

    r = requests.get('http://repositories.ros.org/status_page/ros_noetic_default.html')
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

    sync_date = date.today() + timedelta(days=2)
    while sync_date.weekday() > 4:
        sync_date += timedelta(days=1)
    mapping['sync_target_date'] = sync_date.strftime("%Y-%m-%d")

    print("https://discourse.ros.org/c/release/noetic/66")
    print('----------')
    print(Template(title_template).substitute(mapping))
    print('----------')
    print(Template(body_template).substitute(mapping))
    print('----------')
    print(Template(slack_template).substitute(mapping))


if __name__ == '__main__':
    main()
