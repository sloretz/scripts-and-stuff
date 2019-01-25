#!/usr/bin/env python3

import datetime
from jenkinsapi import jenkins
import jenkinsapi.custom_exceptions
import os
import time
import getpass


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


def get_credentials():
    """Prompt for username/password via CLI."""
    username = input('Jenkins username: ')
    password = getpass.getpass()
    return username, password


def num_cppcheck_violations(build):
    """Return the number of reported CPPcheck violations."""
    url = build.python_api_url(build.baseurl + '/cppcheckResult')
    try:
        # may print 'ERROR:root:failed request' for some jobs (ones that don't run cppcheck?)
        return build.get_data(url)['numberTotal']
    except Exception:
        pass
    return 0


def num_compiler_warnings(build):
    """Return the number of reported compiler warnings."""
    url = build.python_api_url(build.baseurl + '/warningsResult')
    warnings = 0
    try:
        warnings += build.get_data(url)['numberOfWarnings']
    except:
        pass
    return warnings


def num_failed_tests(build):
    """Return the number of tests that failed."""
    num = 0
    for result in test_results(build):
        if result.status not in ['PASSED', 'FIXED', 'SKIPPED']:
            num += 1
    return num


if __name__ == '__main__':
    username, password = get_credentials()
    server = jenkins.Jenkins(
            'https://build.osrfoundation.org', username=username, password=password)

    # TODO get jobs using regex
    job_names = [
        u'gazebo-ci-default-artful-amd64-gpu-none',
        u'gazebo-ci-default-bionic-amd64-gpu-none',
        u'gazebo-ci-default-homebrew-amd64',
        u'gazebo-ci-default-windows7-amd64',
        u'gazebo-ci-default-xenial-amd64-gpu-none',
        u'gazebo-ci-default-xenial-amd64-gpu-nvidia',
        u'gazebo-ci-default-xenial-i386-gpu-none',
        u'gazebo-ci-gazebo7-homebrew-amd64',
        u'gazebo-ci-gazebo7-xenial-amd64-gpu-nvidia',
        u'gazebo-ci-gazebo8-homebrew-amd64',
        u'gazebo-ci-gazebo8-windows7-amd64',
        u'gazebo-ci-gazebo8-xenial-amd64-gpu-nvidia',
        u'gazebo-ci-gazebo9-homebrew-amd64',
        u'gazebo-ci-gazebo9-windows7-amd64',
        u'gazebo-ci-gazebo9-xenial-amd64-gpu-nvidia',
        u'gazebo-ci_BTCoverage-default-xenial-amd64-gpu-none',
        u'gazebo-ci_BTDebug-default-xenial-amd64-gpu-none',
        u'gazebo-ci_BTRelease-default-xenial-amd64-gpu-none',
        u'gazebo-install-gazebo7_pkg-artful-amd64',
        u'gazebo-install-gazebo7_pkg-xenial-amd64',
        u'gazebo-install-gazebo8_pkg-xenial-amd64',
        u'gazebo-install-gazebo9_pkg-xenial-amd64',
        u'gazebo-install-one_liner-homebrew-amd64',
        u'gazebo-install-one_liner-xenial-amd64',
        u'gazebo-performance-default-xenial-amd64',
        u'ignition_cmake-ci-default-artful-amd64',
        u'ignition_cmake-ci-default-bionic-amd64',
        u'ignition_cmake-ci-default-homebrew-amd64',
        u'ignition_cmake-ci-default-windows7-amd64',
        u'ignition_cmake-ci-default-xenial-amd64',
        u'ignition_cmake-install-pkg-bionic-amd64',
        u'ignition_cmake-install-pkg-xenial-amd64',
        u'ignition_common-ci-default-bionic-amd64',
        u'ignition_common-ci-ign-common1-artful-amd64',
        u'ignition_common-ci-ign-common1-bionic-amd64',
        u'ignition_common-ci-ign-common1-homebrew-amd64',
        u'ignition_common-ci-ign-common1-windows7-amd64',
        u'ignition_common-ci-ign-common1-xenial-amd64',
        u'ignition_common-install-pkg-bionic-amd64',
        u'ignition_common-install-pkg-xenial-amd64',
        u'ignition_fuel-tools-ci-default-bionic-amd64',
        u'ignition_fuel-tools-ci-default-xenial-amd64',
        u'ignition_fuel-tools-ci-ign-fuel-tools1-artful-amd64',
        u'ignition_fuel-tools-ci-ign-fuel-tools1-bionic-amd64',
        u'ignition_fuel-tools-ci-ign-fuel-tools1-homebrew-amd64',
        u'ignition_fuel-tools-ci-ign-fuel-tools1-windows7-amd64',
        u'ignition_fuel-tools-ci-ign-fuel-tools1-xenial-amd64',
        u'ignition_fuel-tools-install-pkg-bionic-amd64',
        u'ignition_fuel-tools-install-pkg-xenial-amd64',
        u'ignition_gui-ci-default-bionic-amd64',
        u'ignition_math-ci-default-artful-amd64',
        u'ignition_math-ci-default-bionic-amd64',
        u'ignition_math-ci-default-homebrew-amd64',
        u'ignition_math-ci-default-windows7-amd64',
        u'ignition_math-ci-default-xenial-amd64',
        u'ignition_math2-install-pkg-artful-amd64',
        u'ignition_math2-install-pkg-trusty-amd64',
        u'ignition_math2-install-pkg-xenial-amd64',
        u'ignition_math3-install-pkg-artful-amd64',
        u'ignition_math3-install-pkg-trusty-amd64',
        u'ignition_math3-install-pkg-xenial-amd64',
        u'ignition_math4-install-pkg-artful-amd64',
        u'ignition_math4-install-pkg-bionic-amd64',
        u'ignition_math4-install-pkg-xenial-amd64',
        u'ignition_msgs-ci-default-artful-amd64',
        u'ignition_msgs-ci-default-bionic-amd64',
        u'ignition_msgs-ci-default-homebrew-amd64',
        u'ignition_msgs-ci-default-windows7-amd64',
        u'ignition_msgs-ci-default-xenial-amd64',
        u'ignition_physics-ci-default-artful-amd64',
        u'ignition_rendering-ci-default-artful-amd64',
        u'ignition_rendering-ci-default-bionic-amd64',
        u'ignition_rendering-ci-default-homebrew-amd64',
        u'ignition_rendering-ci-default-windows7-amd64',
        u'ignition_rendering-ci-default-xenial-amd64',
        u'ignition_rndf-install-pkg-artful-amd64',
        u'ignition_rndf-install-pkg-xenial-amd64',
        u'ignition_sensors-ci-default-artful-amd64',
        u'ignition_sensors-ci-default-bionic-amd64',
        u'ignition_sensors-ci-default-homebrew-amd64',
        u'ignition_sensors-ci-default-windows7-amd64',
        u'ignition_sensors-ci-default-xenial-amd64',
        u'ignition_transport-ci-default-artful-amd64',
        u'ignition_transport-ci-default-bionic-amd64',
        u'ignition_transport-ci-default-homebrew-amd64',
        u'ignition_transport-ci-default-windows7-amd64',
        u'ignition_transport-ci-default-xenial-amd64',
        u'ignition_transport-ci-ign-transport3-artful-amd64',
        u'ignition_transport-ci-ign-transport3-homebrew-amd64',
        u'ignition_transport-ci-ign-transport3-windows7-amd64',
        u'ignition_transport-ci-ign-transport3-xenial-amd64',
        u'ignition_transport-ci-ign-transport4-artful-amd64',
        u'ignition_transport-ci-ign-transport4-bionic-amd64',
        u'ignition_transport-ci-ign-transport4-homebrew-amd64',
        u'ignition_transport-ci-ign-transport4-windows7-amd64',
        u'ignition_transport-ci-ign-transport4-xenial-amd64',
        u'ignition_transport3-install-pkg-artful-amd64',
        u'ignition_transport3-install-pkg-xenial-amd64',
        u'ignition_transport4-install-pkg-artful-amd64',
        u'ignition_transport4-install-pkg-bionic-amd64',
        u'ignition_transport4-install-pkg-xenial-amd64',
        u'sdformat-ci-default-artful-amd64',
        u'sdformat-ci-default-bionic-amd64',
        u'sdformat-ci-default-homebrew-amd64',
        u'sdformat-ci-default-trusty-amd64',
        u'sdformat-ci-default-windows7-amd64',
        u'sdformat-ci-default-xenial-amd64',
        u'sdformat-ci-default-xenial-armhf',
        u'sdformat-ci-default-xenial-i386',
        u'sdformat-ci-sdformat5-xenial-amd64',
        u'sdformat-ci-sdformat6-homebrew-amd64',
        u'sdformat-ci-sdformat6-windows7-amd64',
        u'sdformat-ci-sdformat6-xenial-amd64',
        u'sdformat-install-sdformat4_pkg-xenial-amd64',
        u'sdformat-install-sdformat5_pkg-xenial-amd64',
        u'sdformat-install-sdformat6_pkg-xenial-amd64',
        u'servicesim-ci-xenial-amd64',
        u'subt-ci-default-bionic-amd64',
    ]

    # Cache jobs and builds because build.osrfoundation.org is really slow to respond to API calls
    jobs = {}
    job_builds = {}

    def get_job(job_name):
        """Get a job either from the server or a cache of jobs."""
        global jobs, server
        if job_name not in jobs:
            count = 0
            while True:
                count += 1
                print('downloading', job_name)
                try:
                    job = server.get_job(job_name)
                except Exception:
                    time.sleep(2 * count)
                else:
                    break
            assert job_name == job.name
            jobs[job_name] = job
        else:
            print("dbg job cache hit")
        return jobs[job_name]

    def get_build(job_name, build_num, elsedo=None):
        """Get a build either from the server or a cache of builds."""
        global job_builds, server
        job = get_job(job_name)

        if job_name not in job_builds:
            job_builds[job_name] = {}

        builds = job_builds[job_name]
        if build_num not in builds:
            build = elsedo()
            if build_num is None:
                build_num = build.buildno
            builds[build_num] = build
        else:
            print("dbg build cache hit")

        return builds[build_num]

    # aggregate results
    blue = 0
    yellow = 0
    red = 0
    aborted = 0

    for job_name in job_names:
        job = get_job(job_name)
        last_build = get_build(job_name, job.get_last_buildnumber(), lambda: job.get_last_build())

        status = last_build.get_status()
        if status == 'SUCCESS':
            blue += 1
        elif status == 'FAILURE':
            red += 1
        elif status == 'UNSTABLE':
            yellow += 1
        elif status == 'ABORTED':
            aborted += 1
        else:
            # raise ValueError('Unexpected status %r' % (status,))
            print('Unexpected status %r on job %s' % (status, job_name))

    # Builds that succeeded in the past but are failing now
    succeeded_in_past = []
    # Builds that have never succeeded
    never_succeeded = []

    # {'build': <build>, 'cppcheck': <num>, 'warnings': <num>, 'test_failures': <num>}
    unstable_builds = []

    for job_name in job_names:
        job = get_job(job_name)
        last_build = get_build(job_name, job.get_last_buildnumber(), lambda: job.get_last_build())

        status = last_build.get_status()
        if status == 'FAILURE':
            try:
                get_build(job_name, job.get_last_good_buildnumber(), lambda: job.get_last_good_build())
            except Exception:
                never_succeeded.append(job)
            else:
                succeeded_in_past.append(job)
        elif status == 'UNSTABLE':
            data = {'build': last_build}
            data['cppcheck'] = num_cppcheck_violations(last_build)
            data['test_failures'] = num_failed_tests(last_build)
            data['warnings'] = num_compiler_warnings(last_build)
            unstable_builds.append(data)

    unstable_builds.sort(key=lambda i: i['build'].name)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    num_jobs = len(job_names)
    blue_per = 100.0 * blue / num_jobs
    yellow_per = 100.0 * yellow / num_jobs
    red_per = 100.0 * red / num_jobs
    aborted_per = 100.0 * aborted / num_jobs

    for info in unstable_builds:
        print(info)

    # Output a formatted report
    markdown = []
    markdown.append('# Build Cop Report {today}'.format(**locals()))
    markdown.append('')
    markdown.append('## Aggregate Results')
    markdown.append('| Type | Count | Percent | Change |')
    markdown.append('|--|--|--|--|')
    markdown.append('| total | {num_jobs} | |  |'.format(**locals()))
    markdown.append('| blue | {blue}/{num_jobs} | {blue_per:.1f}% |  |'.format(**locals()))
    markdown.append('| yellow | {yellow}/{num_jobs} | {yellow_per:.1f}% |  |'.format(**locals()))
    markdown.append('| red | {red}/{num_jobs} | {red_per:.1f}% |  |'.format(**locals()))
    markdown.append('| aborted | {aborted}/{num_jobs} | {aborted_per:.1f}% |  |'.format(**locals()))
    markdown.append('')
    markdown.append('## [Failing Builds](https://build.osrfoundation.org/view/main/view/BuildCopFail/)')
    markdown.append('')
    markdown.append('## Builds that have succeeded in the past, but are failing now')
    markdown.append('')
    for build in succeeded_in_past:
        build_name = build.name
        build_url = build.baseurl
        markdown.append('* [{build_name}]({build_url})'.format(**locals()))
    markdown.append('')
    markdown.append('## Builds with no record of passing')
    for build in never_succeeded:
        build_name = build.name
        build_url = build.baseurl
        markdown.append('* [{build_name}]({build_url})'.format(**locals()))
    markdown.append('')
    markdown.append('## [Unstable Builds](https://build.osrfoundation.org/view/main/view/BuildCopFail/)')
    markdown.append('')
    markdown.append('### Only cppcheck errors')
    markdown.append('')
    for info in [i for i in unstable_builds if 0 == i['warnings'] and 0 == i['test_failures'] and i['cppcheck'] > 0]:
        build = info['build']
        build_name = build.name
        build_url = build.baseurl
        num = info['cppcheck']
        markdown.append('* [{build_name}]({build_url}) {num} violations'.format(**locals()))
    markdown.append('')
    markdown.append('### Only compiler warnings')
    markdown.append('')
    for info in [i for i in unstable_builds if 0 == i['cppcheck'] and 0 == i['test_failures'] and i['warnings'] > 0]:
        build = info['build']
        build_name = build.name
        build_url = build.baseurl
        num = info['warnings']
        markdown.append('* [{build_name}]({build_url}) {num} warnings'.format(**locals()))
    markdown.append('### One test failure')
    markdown.append('')
    for info in [i for i in unstable_builds if 0 == i['cppcheck'] and 0 == i['warnings'] and i['test_failures'] == 1]:
        build = info['build']
        build_name = build.name
        build_url = build.baseurl
        num = info['test_failures']
        markdown.append('* [{build_name}]({build_url}) {num} test failures'.format(**locals()))
    markdown.append('')
    markdown.append('### Unrecognized failure')
    markdown.append('')
    for info in [i for i in unstable_builds if 0 == i['cppcheck'] and 0 == i['warnings'] and 0 == i['test_failures']]:
        build = info['build']
        build_name = build.name
        build_url = build.baseurl
        markdown.append('* [{build_name}]({build_url})'.format(**locals()))

    print('-------------------Markdown----------------------')
    print('\n'.join(markdown))
