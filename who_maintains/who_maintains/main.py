import argparse
from collections import defaultdict
import pathlib

import catkin_pkg.package

from .find import packages_in_folder
from .find import repositories_in_folder


def main():
    parser = argparse.ArgumentParser(description='Determine package maintainers')
    parser.add_argument('folder_with_packages', metavar='PATH',
                        help='A folder (maybe a workspace) that has ROS packages')

    args = parser.parse_args()

    start_path = pathlib.Path(args.folder_with_packages)
    repo_paths = [pathlib.Path(path) for path in repositories_in_folder(args.folder_with_packages)]
    pkg_paths = [pathlib.Path(path) for path in packages_in_folder(args.folder_with_packages)]

    # Each key is a repo name
    repo_report = defaultdict(set)
    # Each key is a package name that's not in a repo
    pkg_report = defaultdict(set)

    for pkg_path in pkg_paths:
        try:
            pkg = catkin_pkg.package.parse_package(pkg_path)
        except catkin_pkg.package.InvalidPackage:
            # TODO(sloretz) warn?
            pass
        report = None
        for repo_path in repo_paths:
            if repo_path == pkg_path or repo_path in pkg_path.parents:
                # Consolidate this report by repository
                repo_name = str(repo_path.relative_to(start_path))
                report = repo_report[repo_name]
                break
        if report is None:
            report = pkg_report[pkg.name]

        for m in pkg.maintainers:
            report.add(m.name)

    for name, report in repo_report.items():
        print(name + ':', ', '.join(report).replace('\n', ''))

    for name, report in pkg_report.items():
        print(name + ':', ', '.join(report).replace('\n', ''))


if __name__ == '__main__':
    main()
