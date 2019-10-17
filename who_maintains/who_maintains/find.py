import os

import catkin_pkg.package
import catkin_pkg.packages
import git


def repo(path):
    try:
        return git.Repo(path)
    except git.exc.InvalidGitRepositoryError:
        return None


def repositories_in_folder(path):
    """Given a path to a workspace, return paths to repositories in it."""
    for thing in os.listdir(path):
        thing = os.path.join(path, thing)
        if os.path.isdir(thing):
            # Is it a repository?
            if repo(thing):
                yield thing
            else:
                yield from repositories_in_folder(thing)
        elif repo(thing):
            yield thing


def packages_in_folder(path):
    """Given a path to a workspace, return paths to packages in it."""
    for pkg_path in catkin_pkg.packages.find_package_paths(path):
        yield os.path.join(path, pkg_path)


def maintainers(path):
    """Return maintainers of a package at the given path."""
    pkg = catkin_pkg.package.parse_package(path)
    for m in pkg.maintainers:
        yield m.name, m.email


