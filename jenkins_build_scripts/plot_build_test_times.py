#!/usr/bin/env python3


# Given a directory full of job locks in the format <job_name>_<number>.txt
# Create plots of trends of build time and test times over time

import os
import re
import argparse
from pathlib import Path
import matplotlib.pyplot as plt


SUBSECTION_REGEX = re.compile('^# BEGIN SUBSECTION: (.+)$')
START_REGEX = re.compile('^Starting >>> (.+)$')
STOP_REGEX = re.compile('^Finished <<< (.+) \[([^]]+)\]$')
JOB_REGEX = re.compile('^(.+)_([0-9]+)\.txt')

TIME_REGEX = re.compile('^(?:(?P<minutes>[0-9]+)min )?(?P<seconds>[0-9.]+)s$')


def pkg_time_to_float(time_str):
    time_match = TIME_REGEX.match(time_str)
    minutes = 0
    if not time_match:
        raise RuntimeError(time_str)
    if time_match.group('minutes'):
        minutes = int(time_match.group('minutes'))
    seconds = float(time_match.group('seconds'))
    return 60 * minutes + seconds


def get_subsection_info(text):
    subsection = None
    info = {'build': {}, 'test': {}}
    for line in text.split('\n'):
        subsection_match = SUBSECTION_REGEX.match(line)
        if subsection_match:
            # print('In subsection', subsection_match.group(1))
            subsection = subsection_match.group(1)

        if subsection in ('build', 'test'):
            stop_match = STOP_REGEX.match(line)
            if stop_match:
                pkg_name = stop_match.group(1)
                pkg_time = stop_match.group(2)
                
                info[subsection][pkg_name] = pkg_time_to_float(pkg_time)
    return info


def plot_mega_info(mega_info):
    fig = plt.figure()
    plot_partial_info(fig.add_subplot(4, 2, 1), 'build', mega_info)
    plot_partial_info(fig.add_subplot(4, 2, 2), 'test', mega_info)

    plot_total_time(fig.add_subplot(4, 2, 3), 'build', mega_info)
    plot_total_time(fig.add_subplot(4, 2, 4), 'test', mega_info)

    plot_top_10(fig.add_subplot(4, 2, 5), 'build', mega_info)
    plot_top_10(fig.add_subplot(4, 2, 6), 'test', mega_info)

    plt.show()


def plot_partial_info(ax, subsection, mega_info):
    x_axis_data = []
    y_axis_data = []
    for job_number, subsection_info in mega_info:
        time_info = subsection_info[subsection]
        for pkg_name, pkg_time in time_info.items():
            x_axis_data.append(job_number)
            y_axis_data.append(pkg_time)

    ax.scatter(x_axis_data, y_axis_data, s=2)
    ax.title.set_text(f'{subsection} times')



def plot_total_time(ax, subsection, mega_info):
    x_axis_data = []
    y_axis_data = []
    for job_number, subsection_info in mega_info:
        time_info = subsection_info[subsection]
        total_time = 0
        for pkg_name, pkg_time in time_info.items():
            total_time += pkg_time

        x_axis_data.append(job_number)
        y_axis_data.append(total_time)

    ax.scatter(x_axis_data, y_axis_data)
    ax.title.set_text(f'{subsection} total times')


def plot_top_10(ax, subsection, mega_info):
    # {pkg_name: [time1, time2, ...]}
    pkg_times = {}
    for job_number, subsection_info in mega_info:
        time_info = subsection_info[subsection]
        for pkg_name, pkg_time in time_info.items():
            if pkg_name not in pkg_times:
                pkg_times[pkg_name] = []
            pkg_times[pkg_name].append(pkg_time)

    # [(name, avg_time), ...]
    averages = []
    for name, times in pkg_times.items():
        averages.append((name, sum(times) / len(times)))

    sorted_averages = [a for a in sorted(averages, key=lambda i: i[1])]
    top_10_names = [a[0] for a in sorted_averages[-10:]]
    top_10_times = [a[1] for a in sorted_averages[-10:]]

    hbars = ax.barh(top_10_names, top_10_times)
    # ax.set_yticks(range(len(top_10_names)), labels=top_10_names)
    ax.set_xlabel(f'{subsection} avg time')
    ax.set_title(f'Top 10 {subsection} times')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', help='Directory to get job logs from', required=True)
    args = parser.parse_args()

    # [(job number, subsection_info)]
    mega_info = []

    job_name = None
    for filename in sorted(os.listdir(args.directory)):
        job_name_match = JOB_REGEX.match(filename)
        if job_name is None:
            job_name = job_name_match.group(1)
        else:
            if job_name_match.group(1) != job_name:
                raise RuntimeError('All logs in the directory must be from the same job type, found: {job_name_match.group(1)} and {job_name}')

        job_number = job_name_match.group(2)
        # print(job_number)
        textfile = Path(args.directory) / Path(filename)
        subsection_info = get_subsection_info(textfile.read_text())

        mega_info.append((job_number, subsection_info))
    plot_mega_info(mega_info)
