#!/usr/bin/env python

import argparse
from github import Github
from github.InputFileContent import InputFileContent
import keyring
import re
import requests
import yaml


def get_gist_key():
    key = keyring.get_password("github-api-token", "may-create-gist")
    if key is None:
        raise RuntimeError('Failed to get github api key')
    return key


def create_gist(github_handle, content, description):
    content = InputFileContent(content=content, new_name='ros2.repos')
    gist = github_handle.get_user().create_gist(
        True, {'ros2.repos': content}, description)
    return gist.files['ros2.repos'].raw_url


def download_ros2_repos(branch):
    url = 'https://raw.githubusercontent.com/ros2/ros2/{branch}/ros2.repos'
    r = requests.get(url.format(branch=branch))
    if r.status_code != 200:
        raise RuntimeError('Failed to download ros2.repos file' + repr(r))
    return r.text


class RepoPatch:

    def __init__(self, name, url, ref):
        # Name of the repo (ex: ros2/system_tests)
        self.name = name
        # URL to use for repo (ex: https://github.com/alice/system_tests.git)
        self.url = url
        # The branch, tag or commit on the repo to use (ex: master)
        self.ref = ref


def patch_repo_file(repo_content, patches):
    repos = yaml.load(repo_content)
    for patch in patches:
        for repo in repos['repositories']:
            if repo == patch.name:
                repos['repositories'][repo]['url'] = patch.url
                repos['repositories'][repo]['version'] = patch.ref
    return yaml.dump(repos)


def repo_patches_from_args(github_handle, args):
    regex = [
        # ex: https://github.com/ros2/rmw_fastrtps/pull/247
        r'https://github.com/(?P<name>.*)/pull/(?P<number>[0-9]+)',
        # ex: ros2/rmw_fastrtps#247
        r'(?P<name>[-a-zA-Z_0-9.]+/[-a-zA-Z_0-9.]+)#(?P<number>[0-9]+)',
    ]
    regex = [re.compile(r) for r in regex]

    patches = []
    for pull_request in args.pull_requests:
        name = None
        number = None
        for r in regex:
            match = re.match(r, pull_request)
            if match is not None:
                name = match.group('name')
                number = match.group('number')
                break

        if name is None or number is None:
            raise RuntimeError('Invalid argument ' + repr(pull_request))

        repo = github_handle.get_repo(name)
        if repo is None:
            raise RuntimeError('Failed to get repo ' + repr(pull_request))

        pr = repo.get_pull(int(number))
        if pr is None:
            raise RuntimeError('Failed to get PR ' + repr(pull_request))

        patches.append(RepoPatch(name, pr.head.repo.clone_url, pr.head.ref))
    return patches


def parse_args(args):
    parser = argparse.ArgumentParser(
        description='Create a repos file with one or more pull requests.')
    parser.add_argument('pull_requests', metavar='PR', type=str, nargs='+',
                        help='pull request to include in the repos file')
    parser.add_argument('--branch', type=str, default='master',
                        help='branch on ros2/ros2 to get ros2.repos from')
    return parser.parse_args(args)


def main(args=None):
    args = parse_args(args)

    repo_content = download_ros2_repos(args.branch)

    github_handle = Github(get_gist_key())

    patches = repo_patches_from_args(github_handle, args)

    repo_content = patch_repo_file(repo_content, patches)

    description = 'Generated repos file for'
    for pr in args.pull_requests:
        description += ' ' + pr

    url = create_gist(github_handle, repo_content, description)
    print(url)


if __name__ == '__main__':
    import sys
    main(sys.argv)
