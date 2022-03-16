#!/usr/bin/env python3


# Staring from:
# https://gist.github.com/m-x-k/7c7e02de0abfb47b07d8e62aed93d00d

import re
import argparse
import requests

VIEW_URL_REGEX = re.compile('^(.*)/(?:view/[^/]+/)?job/([^/]+)[/]?$')

def get_response(url):
    response = requests.get(url)
    if not response.ok:
        raise RuntimeError(f'{response.status_code}: {response.reason} when accessing {url}')

    return response

def get_job_name(view_url):
    match = VIEW_URL_REGEX.match(view_url)
    if match is None:
        raise ValueError(f'Could not get job name from "{view_url}"')

    return match.group(2)

def last_build_json_api_url(view_url) -> str:
    """
    Given a job view URL, make a url to the api of the last build
    """
    # from: https://ci.ros2.org/view/nightly/job/nightly_win_deb/
    # to: https://ci.ros2.org/job/nightly_win_deb/lastBuild/api/json
    match = VIEW_URL_REGEX.match(view_url)
    if match is None:
        raise ValueError(f'Could not make API url from "{view_url}"')

    url_base = match.group(1)
    job_name = match.group(2)

    return f'{url_base}/job/{job_name}/lastBuild/api/json'

def last_build_number(view_url) -> int:
    api_url = last_build_json_api_url(view_url)
    return get_response(api_url).json()['number']

def console_text_url(view_url, build_number):
    # from: https://ci.ros2.org/view/nightly/job/nightly_win_deb/
    # to: https://ci.ros2.org/job/nightly_win_deb/2227/consoleText
    match = VIEW_URL_REGEX.match(view_url)
    if match is None:
        raise ValueError(f'Could not make consle url from "{view_url}"')

    url_base = match.group(1)
    job_name = match.group(2)

    return f'{url_base}/job/{job_name}/{build_number}/consoleText'


def console_text(view_url, build_number):
    url = console_text_url(view_url, build_number)
    response = get_response(url)
    return response.text


if __name__ == '__main__':
    # Example: python jenkinsJobConsoleOutput.py -j https://ci.ros2.org/view/nightly/job/nightly_win_deb/ -n 50 --stride
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', help="URL of job to get logs from")
    parser.add_argument('--number', help="Number of jobs to fetch")
    parser.add_argument('--step', help="Collect every N jobs (default: 1)", default="1")
    args = parser.parse_args()

    job_name = get_job_name(args.url)
    num = last_build_number(args.url)

    start = num
    stop = num - (int(args.number) * int(args.step))
    step = -1 * int(args.step)

    for num in range(start, stop, step):
        filename = f'{job_name}_{num}.txt'
        print(f'Getting data for {filename}')
        text = console_text(args.url, num)
        with open(filename, 'w') as fout:
            fout.write(text)
