#!/usr/bin/env python3

import getpass
from jenkinsapi import jenkins
import jenkinsapi.custom_exceptions
import argparse


_username = None
_password = None


def get_credentials():
    """Prompt for username/password via CLI."""
    global _username
    global _password
    if _username is None:
        _username = input('Jenkins username: ')
        _password = getpass.getpass()
    return _username, _password


def get_arguments():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("jenkins_uri")
    return parser.parse_args()


def test_results(build):
    """Return a generator to iterate through test results."""
    if build.has_resultset():
        rs = build.get_resultset()
        for test_name, result in rs.items():
            yield result


def verb_compare(args, pr_job_name, pr_build_num, ci_job_name):
    """Compare test failures in a PR job to the history in a CI job."""
    print('Comparing', pr_job_name, '#', pr_build_num, 'to', ci_job_name)
    username, password = get_credentials()
    server = jenkins.Jenkins(
        args.jenkins_uri, username=username, password=password)
    pr_job = server.get_job(pr_job_name)
    ci_job = server.get_job(ci_job_name)

    # Get failures from the PR job
    pr_build = pr_job.get_build(pr_build_num)
    pr_failures = {}
    for result in test_results(pr_build):
        if result.status not in ['PASSED', 'FIXED']:
            print('PR', result.identifier(), result.status)
            pr_failures[result.identifier()] = []
    if not pr_failures:
        print("No failures found in {name}".format(name=pr_build.name))

    # Get failures from recent CI jobs
    for build in recent_builds(ci_job):
        print("Checking", build.name)
        for result in test_results(build):
            if result.status not in ['PASSED', 'FIXED']:
                if result.identifier() in pr_failures:
                    pr_failures[result.identifier()].append((build, result))

    print('---------------Markdown---------------')
    print('**Build [{name}]({url})**\n'.format(
        name=pr_build.name, url=pr_build.baseurl))
    for test_name, others in pr_failures.items():
        print('* Test `{test_name}`'.format(test_name=test_name))
        if not others:
            print('    * **Did not fail in other recent builds**')
        else:
            for ci_build, result in others:
                print('    * Also failed in [{name}]({url})'.format(
                    name=ci_build.name, url=ci_build.baseurl))
    print('---------------Markdown---------------')


def recent_builds(job, num=15):
    """Return a generator to iterate through recent builds."""
    current_number = job.get_last_buildnumber()
    while num > 0 and current_number > 0:
        try:
            yield job.get_build(current_number)
        except jenkinsapi.custom_exceptions.NotFound:
            continue
        num -= 1
        current_number -= 1


def verb_tally_failures(args, job_names):
    print('Tallying recent flaky tests for ', job_names)
    username, password = get_credentials()
    server = jenkins.Jenkins(
        args.jenkins_uri, username=username, password=password)

    # Get failures from recent jobs
    build_urls = {}
    test_failures = {}
    for job_name in job_names:
        job = server.get_job(job_name)
        for build in recent_builds(job, num=7):
            build_urls[build.name] = build.baseurl
            print("Checking", build.name)
            for result in test_results(build):
                if result.status not in ['PASSED', 'FIXED']:
                    if result.identifier() not in test_failures:
                        test_failures[result.identifier()] = 0
                    test_failures[result.identifier()] += 1

    # Order failures from most to least
    test_failures = list(test_failures.items())
    test_failures.sort(key=lambda t: t[1], reverse=True)

    print('---------------Markdown---------------')
    print('**In these %d builds**\n' % len(build_urls))
    for build_name, build_url in build_urls.items():
        print('* [{name}]({url})'.format(name=build_name, url=build_url))
    print('\n**These were the test failures**\n')
    for test_name, count in test_failures:
        print('* *{per}%* **{count}** failures of `{test_name}`'.format(
        test_name=test_name, count=count, per=int(float(count)/len(build_urls) * 100.0)))
    print('---------------Markdown---------------')


# TODO Run this for non-repeated jobs, and repeated jobs separately

def print_latest_failures(server, job_names):
    """Get a list of all tests that failed on the most recent build of the given jobs."""
    build_urls = {}
    test_failures = {}

    for job_name in job_names:
        job = server.get_job(job_name)
        for build in recent_builds(job, num=1):
            build_urls[build.name] = build.baseurl
            for result in test_results(build):
                if result.status not in ['PASSED', 'FIXED', 'SKIPPED']:
                    if result.identifier() not in test_failures:
                        test_failures[result.identifier()] = {'builds':[]}
                    test_failures[result.identifier()]['builds'].append(build.name)

    # Order failures from most to least
    test_failures = list(test_failures.items())
    test_failures.sort(key=lambda t: len(t[1]['builds']), reverse=True)

    print('---------------Markdown---------------')
    for test_name, info in test_failures:
        print('* `{test_name}`'.format(test_name=test_name))
        build_links = []
        for build_name in info['builds']:
            build_links.append(
                '[{name}]({url})'.format(name=build_name, url=build_urls[build_name]))
        print('    * ' + ', '.join(build_links))
    print('---------------Markdown---------------')


# def get_failing_tests(server, job_names):
#     """Get markdown formatted with failing tests.
#     Confirmed failure:
#         failed on the most recent build job and one of
#             - the previous build of the same job
#             - another most recent build of a different job
#     Lone Failure:
#         failed on most recent build of only one job
#     """
#     # Get all the data outright
#     jobs = []
#     for job_name in job_names:
#         job = server.get_job(job_name)
#         job.builds = list(recent_builds(job, num=2))
#         for build in job.builds:
#             build.failed_tests = []
#             for result in test_results(build)
#                 if result.status not in ['PASSED', 'FIXED', 'SKIPPED']:
#                     failed_tests.append(result
#         jobs.append(job)
# 
#     # Figure out what's confirmed, new, or flaky
#     confirmed_failures = {}
#     new_failures = {}
# 
#     # All failures are possibly new
#     for job in jobs:
#         if len(job.builds) == 0:
#             continue
#         first_build = job.builds[0]
#         confirmed_by_build = []
#         new_in_build = {}
# 
#         # Look at most recent build first
#         print("Looking at " + first_build.name)
#         for result in first_build.failed_tests:
#             if result.identifier() in new_failures:
#                 # Confirmed for being in multiple jobs of the most recent build
#                 del new_failures[result.identifier()]
#                 confirmed_failures.append(result)
#             else:
#                 # Possibly new
#                 new_failures[result.identifier()] = result
# 
#         # Now look at second job to confirm failures that way
#         if len(job.builds) == 1:
#             continue
#         second_build = job.builds[1]



def gz_build_cop_report(args, view_name):
    # TODO Generage gazebo build cop report given a link to the view
    # ex:  https://build.osrfoundation.org/view/main/view/BuildCopFail/api/json
    pass


if __name__ == '__main__':
    args = get_arguments()

    import os
    global _username, _password
#    _username = 'sloretz'
#    _password = os.getenv('SLORETZ_GITHUB_TOKEN')
#
#    server = jenkins.Jenkins(
#        args.jenkins_uri, username='sloretz', password=os.getenv('SLORETZ_GITHUB_TOKEN'))
#
#    print_latest_failures(server, [
#        'nightly_linux-aarch64_debug',
#        'nightly_linux-aarch64_release',
#        'nightly_linux_debug',
#        'nightly_linux_release',
#        'nightly_osx_debug',
#        'nightly_osx_release',
#        'nightly_win_deb',
#        'nightly_win_rel'])

    # Broken tests
    # verb_tally_failures(args, ['nightly_linux-aarch64_debug', 'nightly_linux-aarch64_release'])
    # verb_tally_failures(args, ['nightly_linux_debug', 'nightly_linux_release'])
    # verb_tally_failures(args, ['nightly_osx_debug', 'nightly_osx_release'])
    # verb_tally_failures(args, ['nightly_win_deb', 'nightly_win_rel'])

    # # Flaky tests
    # verb_tally_failures(args, ['nightly_linux-aarch64_repeated'])
    # verb_tally_failures(args, ['nightly_linux_repeated'])
    # verb_tally_failures(args, ['nightly_osx_repeated'])
    # verb_tally_failures(args, ['nightly_win_rep'])

    # verb_compare(
    #     args, 'gazebo-ci-pr_any-homebrew-amd64', 1255,
    #     'gazebo-ci-default-homebrew-amd64')

    # verb_compare(
    #     args, 'gazebo-ci-pr_any-xenial-amd64-gpu-nvidia', 339,
    #     'gazebo-ci-default-xenial-amd64-gpu-nvidia')

    # verb_compare(
    #     args, 'gazebo-ci-pr_any-xenial-amd64-gpu-none', 670,
    #     'gazebo-ci-default-xenial-amd64-gpu-none')

#    verb_compare(
#        args, 'ignition_transport-ci-pr_any-homebrew-amd64', 283,
#        'ignition_transport-ci-default-homebrew-amd64')

#    verb_tally_failures(args, [
#        'gazebo-ci-default-homebrew-amd64',
#        'gazebo-ci-default-windows7-amd64',
#        'gazebo-ci-default-xenial-amd64-gpu-none',
#        'gazebo-ci-default-xenial-amd64-gpu-nvidia',
#        'gazebo-ci-default-xenial-i386-gpu-none',
#        'gazebo-ci-default-zesty-amd64-gpu-none',
#        ])
#
#    verb_tally_failures(args, [
#        'gazebo-ci-gazebo7-homebrew-amd64',
#        'gazebo-ci-gazebo7-xenial-amd64-gpu-nvidia'
#        ])
#
#    verb_tally_failures(args, [
#        'gazebo-ci-gazebo8-homebrew-amd64',
#        'gazebo-ci-gazebo8-windows7-amd64',
#        'gazebo-ci-gazebo8-xenial-amd64-gpu-nvidia',
#        ])
#
#    verb_tally_failures(args, [
#        'ignition_common-ci-default-zesty-amd64',
#        ])
#
    verb_tally_failures(args, [
        'ignition_gui-ci-default-zesty-amd64',
        ])

#    verb_tally_failures(args, [
#        'ignition_msgs-ci-default-zesty-amd64',
#        'ignition_msgs-ci-ign-msgs1-zesty-amd64',
#        ])
#
#    verb_tally_failures(args, [
#        'sdformat-ci-default-trusty-amd64'
#        ])
