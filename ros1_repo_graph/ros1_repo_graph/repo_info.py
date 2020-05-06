import copy

from ros_buildfarm.status_page import _get_blocked_source_entries_info
from ros_buildfarm.status_page import _get_blocked_releases_info


def filter_repos(repos_info, *, depth=None, target_repos=None):
    """Limit how deep tree is, since super deep repos aren't that useful to me."""
    # if depth is 0, just root repo
    # if depth is 1, root repo plus all repos_blocking

    ret_info = copy.copy(repos_info)

    if depth is not None:
        filtered_info = {}
        while depth >= 0:
            depth -= 1
            repos_at_depth = []
            for name, repo in ret_info.items():
                if name in filtered_info:
                    # already added this one
                    continue
                if 0 == len(set(repo['repos_blocked_by']).difference(filtered_info.keys())):
                    # Found repo at this depth
                    repos_at_depth.append(name)
            for name in repos_at_depth:
                filtered_info[name] = ret_info[name]
        ret_info = filtered_info
    if target_repos is not None:
        filtered_info = {}
        for name, repo in ret_info.items():
            include = False
            if 'recursive_repos_blocking' in repo:
                for r in repo['recursive_repos_blocking']:
                    if r in target_repos:
                        include = True
                        break
            if name in target_repos:
                include = True
            if include:
                filtered_info[name] = repo
        ret_info = filtered_info

    return ret_info


def source_entries_repo_info(config_url, ros_distro_name, depth=None):
    repos_info = _get_blocked_source_entries_info(config_url, ros_distro_name)

    if depth:
        repos_info = filter_repos(repos_info, depth)
    return repos_info


def releases_repo_info(config_url, ros_distro_name, depth=None):
    repos_info = _get_blocked_releases_info(config_url, ros_distro_name)

    if depth:
        repos_info = filter_repos(repos_info, depth)
    return repos_info


def dot_graph(repos_info):
    nodes = set()
    edges = set()

    for name, repo in repos_info.items():
        style = '[label="{}"]'.format(name)
        if repo['released']:
            continue
        if repo['repos_blocked_by']:
            style += '[color=red]'
        else:
            style += '[color=yellow]'
        nodes.add((name, style))

        for blocked_by in repo['repos_blocked_by']:
            if blocked_by in repos_info:
                edges.add((name, blocked_by))
        if 'repos_blocking' in repo:
            for blocking in repo['repos_blocking']:
                if blocking in repos_info:
                    edges.add((blocking, name))

    edges_dot = []
    nodes_dot = []
    for name, style in nodes:
        nodes_dot.append('  "{name}"{style};'.format(name=name, style=style))
    for from_repo, to_repo in edges:
        edges_dot.append('  "{from_repo}" -> "{to_repo}";'.format(
            from_repo=from_repo, to_repo=to_repo))

    return 'digraph G {{\n{edges}\n{nodes}\n}}'.format(
        edges='\n'.join(edges_dot),
        nodes='\n'.join(nodes_dot))


def num_repos_blocking(repo):
    if 'recursive_repos_blocking' in repo:
        return len(repo['recursive_repos_blocking'])
    elif 'repos_blocking' in repo:
        return len(repo['repos_blocking'])
    return 0


def who_is_next_info(repos_info, ignore_repos=('orocos_kinematics_dynamics', 'bfl')):
    next_repos = {}

    for name, repo in repos_info.items():
        if name in ignore_repos:
            continue
        if repo['released']:
            continue
        if repo['repos_blocked_by']:
            do_continue = False
            for br in repo['repos_blocked_by'].keys():
                if br not in ignore_repos:
                    do_continue = True
                    break
            if do_continue:
                continue
        next_repos[name] = repo

    report = []

    for name, repo in sorted(next_repos.items(), key=lambda t: num_repos_blocking(t[1]), reverse=True):
        report.append({
                'name': name,
                'blocking': num_repos_blocking(repo),
                'url': repo['url'] if 'url' in repo else None
            })
    return report


def who_is_next(repos_info):
    report_info = who_is_next_info(repos_info)

    report = []
    for info in report_info:
        report.append("{name} (blocking {amt})".format(name=info['name'], amt=info['blocking']))
    return "\n".join(report)


def who_is_next_vcstool(repos_info):
    return vcstool(who_is_next_info(repos_info))


def vcstool(repos_info):
    repos_file = ['repositories:']

    for name, repo in repos_info.items():
        if 'url' in repo and repo['url']:
            repos_file.append("""  {name}:
    type: git
    url: {url}""".format(name=name, url=repo['url']))
        else:
            repos_file.append("""#  {name}:
#    type: git
#    url: {url}""".format(name=name, url=None))
    return "\n".join(repos_file)
