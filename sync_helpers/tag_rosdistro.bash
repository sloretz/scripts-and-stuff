#!/bin/bash

cd /tmp
git clone git@github.com:ros/rosdistro.git
cd rosdistro/
git log -n 1 -- noetic/distribution.yaml
git checkout `git log -n 1 --format=format:%H -- noetic/distribution.yaml`
git tag "noetic/`date +%Y-%m-%d`"

echo "-----------------------------"
echo "If this looks good, then run"
echo "-----------------------------"
echo "cd /tmp/rosdistro"
echo "git push --tags"

