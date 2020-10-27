#!/usr/bin/env python3

import re
import requests
import yaml


req = requests.get("https://raw.githubusercontent.com/ros/rosdistro/master/noetic/distribution.yaml")
if req.status_code != 200:
    print("Failed to fetch", url)
else:
    distro = yaml.safe_load(req.text)
    count = 0
    for name, repo in distro['repositories'].items():
        if 'release' in repo:
            if 'packages' in repo['release']:
                count += len(repo['release']['packages'])
            else:
                count += 1
    print(f'released packages: {count}')


built_packages = {
    "focal-amd64": "http://repositories.ros.org/ubuntu/building/dists/focal/main/binary-amd64/Packages",
    "focal-arm64": "http://repositories.ros.org/ubuntu/building/dists/focal/main/binary-arm64/Packages",
    "focal-armhf": "http://repositories.ros.org/ubuntu/building/dists/focal/main/binary-armhf/Packages",
    "buster-amd64": "http://repositories.ros.org/ubuntu/building/dists/buster/main/binary-amd64/Packages",
    "buster-arm64": "http://repositories.ros.org/ubuntu/building/dists/buster/main/binary-arm64/Packages",
}

for name, url in built_packages.items():
    req = requests.get(url)
    if req.status_code != 200:
        print("Failed to fetch", url)
        continue

    count = 0
    for line in req.text.split("\n"):
        if line.startswith("Package: ros-noetic-"):
            if not line.endswith("-dbgsym"):
                count += 1

    print(f'{name}: {count} packages built')
