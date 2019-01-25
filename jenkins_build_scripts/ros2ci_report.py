#!/usr/bin/env python3

from jenkinsapi import jenkins
import jenkinsapi.custom_exceptions
import os


def test_results(build):
    """Return a generator to iterate through test results."""
    if build.has_resultset():
        rs = build.get_resultset()
        for test_name, result in rs.items():
            yield result


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


def print_flaky_tests(args, job_names):
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
                    # TODO(sloretz) why does a build name sometimes come up twice here?
                    if build.name not in test_failures[result.identifier()]['builds']:
                        test_failures[result.identifier()]['builds'].append(build.name)

    # Order failures from most to least
    test_failures = list(test_failures.items())
    test_failures.sort(key=lambda t: len(t[1]['builds']), reverse=True)

    # combine failures by the combination of platforms they failed on
    platform_tuples = {}
    for test_name, info in test_failures:
        info['builds'].sort()
        build_tuple = tuple(info['builds'])
        if build_tuple not in platform_tuples:
            platform_tuples[build_tuple] = list()
        platform_tuples[build_tuple].append(test_name)

    # Sort tests alphabetically
    for builds, test_names in platform_tuples.items():
        test_names.sort()

    print('---------------Markdown---------------')
    for build_tuple, test_names in platform_tuples.items():
        build_links = []
        for build_name in build_tuple:
            build_links.append(
                '[{name}]({url})'.format(name=build_name, url=build_urls[build_name]))
        print('Failures in {build_links}'.format(build_links=', '.join(build_links)))
        print('```')
        for test_name in test_names:
            print(test_name)
        print('```')
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


if __name__ == '__main__':
    server = jenkins.Jenkins(
            'https://ci.ros2.org', username=os.getenv('JENKINS_GITHUB_USER'), password=os.getenv('JENKINS_GITHUB_TOKEN'))

    # The very latest failures
    print_latest_failures(server, [
        'nightly_linux-aarch64_debug',
        'nightly_linux-aarch64_release',
        'nightly_linux-aarch64_extra_rmw_release',
        'nightly_linux_debug',
        'nightly_linux_release',
        'nightly_linux_extra_rmw_release',
        'nightly_osx_debug',
        'nightly_osx_release',
        'nightly_osx_extra_rmw_release',
        'nightly_win_deb',
        'nightly_win_rel',
        'nightly_win_extra_rmw_rel',
        'nightly_xenial_linux-aarch64_release',
        'nightly_xenial_linux_release'])

    # Confirmed vs new failures
    # TODO

    # Flaky tests
    # TODO
