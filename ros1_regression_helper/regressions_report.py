#!/usr/bin/env python

import re
import requests
import json


TABLE_ROW_EXPR = re.compile('<tr>.+?</tr>')
DIV_EXPR = re.compile('<div>(?P<content>.+?)</div>')
LINK_EXPR  = re.compile('<a href="(?P<link>.+?)">(?P<text>.+?)</a>')


def rows_with_regression(text):
    for match in TABLE_ROW_EXPR.finditer(text):
        line = match.group()
        if 'REGRESSION' in line:
            yield line


def package_in_row(text):
    div_match = DIV_EXPR.search(text)
    # print(div_match.group('content'))
    link_match = LINK_EXPR.search(div_match.group('content'))
    if link_match:
        return link_match.group('text')
    return div_match.group('content')


def report_status_page(jenkins_json_url, status_url):
    resp = requests.get(status_url)
    # print(resp, dir(resp), resp.text)
    for row in rows_with_regression(resp.text):
        this_package = package_in_row(row)
        resp = requests.get(jenkins_json_url.format(package=this_package))
        results = json.loads(resp.text)
        this_color = results['color']
        colors = {'red': [], 'aborted': []}
        for project in results['upstreamProjects']:
            name = project['name'].split('__')[1]
            if 'blue' != project['color']:
                colors[project['color']].append(name)

        red_markdown = map(lambda c: '`{}`'.format(c), colors['red'])
        aborted_markdown = map(lambda c: '`{}`'.format(c), colors['aborted'])

        print(f'* [{this_package}]({results["url"]})')
        if 'aborted' == this_color:
            if colors['red']:
                print(f'  * :warning: Upstream packages that failed to build: {", ".join(red_markdown)}')
            if colors['aborted']:
                print(f'  * Upstream packages blocking this: {", ".join(aborted_markdown)}')
        elif 'red' == this_color:
            print('  * :warning: Failed to build :warning:')
        else:
            print('  * Script bug? Nothing seems wrong with this one')


def main():
    print("## Ubuntu Focal amd64")
    jenkins_json_url = 'http://build.ros.org/view/Nbin_uF64/job/Nbin_uF64__{package}__ubuntu_focal_amd64__binary/api/json?pretty=true'
    status_url = 'http://repositories.ros.org/status_page/ros_noetic_default.html'
    report_status_page(jenkins_json_url, status_url)
    print('')

    print("## Ubuntu Focal arm64")
    jenkins_json_url = 'http://build.ros.org/view/Nbin_ufv8_uFv8/job/Nbin_ufv8_uFv8__{package}__ubuntu_focal_arm64__binary/api/json?pretty=true'
    status_url = 'http://repositories.ros.org/status_page/ros_noetic_ufv8.html'
    report_status_page(jenkins_json_url, status_url)
    print('')

    print("## Ubuntu Focal armhf")
    jenkins_json_url = 'http://build.ros.org/view/Nbin_ufhf_uFhf/job/Nbin_ufhf_uFhf__{package}__ubuntu_focal_armhf__binary/api/json?pretty=true'
    status_url = 'http://repositories.ros.org/status_page/ros_noetic_ufhf.html'
    report_status_page(jenkins_json_url, status_url)
    print('')

    print("## Debian Buster amd64")
    jenkins_json_url = 'http://build.ros.org/view/Nbin_db_dB64/job/Nbin_db_dB64__{package}__debian_buster_amd64__binary/api/json?pretty=true'
    status_url = 'http://repositories.ros.org/status_page/ros_noetic_db.html'
    report_status_page(jenkins_json_url, status_url)
    print('')

    print("## Debian Buster arm64")
    jenkins_json_url = 'http://build.ros.org/view/Nbin_dbv8_dBv8/job/Nbin_dbv8_dBv8__{package}__debian_buster_arm64__binary/api/json?pretty=true'
    status_url = 'http://repositories.ros.org/status_page/ros_noetic_dbv8.html'
    report_status_page(jenkins_json_url, status_url)


if __name__ == '__main__':
    main()
