from ros_buildfarm.status_page import _get_blocked_source_entries_info


def filter_repos(repos_info, depth):
    """Limit how deep tree is, since super deep repos aren't that useful to me."""
    # if depth is 0, just root repo
    # if depth is 1, root repo plus all repos_blocking

    filtered_info = {}
    while depth >= 0:
        depth -= 1
        repos_at_depth = []
        for name, repo in repos_info.items():
            if name in filtered_info:
                # already added this one
                continue
            if 0 == len(set(repo['repos_blocked_by']).difference(filtered_info.keys())):
                # Found repo at this depth
                repos_at_depth.append(name)
        for name in repos_at_depth:
            filtered_info[name] = repos_info[name]
    return filtered_info



def source_entries_repo_info(config_url, ros_distro_name, depth=None):
    repos_info = _get_blocked_source_entries_info(config_url, ros_distro_name)

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


def who_is_next_info(repos_info):
    next_repos = {}

    for name, repo in repos_info.items():
        if repo['released']:
            continue
        if repo['repos_blocked_by']:
            continue
        next_repos[name] = repo

    report = []
    for name, repo in sorted(next_repos.items(), key=lambda t: len(t[1]['repos_blocking']), reverse=True):
        report.append({
                'name': name,
                'blocking': len(repo['repos_blocking']),
                'url': repo['url']
            })
    return report


def who_is_next(repos_info):
    report_info = who_is_next_info(repos_info)

    report = []
    for info in report_info:
        report.append("{name} (blocking {amt})".format(name=info['name'], amt=info['blocking']))
        report.append("\t{url}".format(url=info['url']))
    return "\n".join(report)


def who_is_next_vcstool(repos_info):
    next_repos = {}

    for name, repo in repos_info.items():
        if repo['released']:
            continue
        if repo['repos_blocked_by']:
            continue
        next_repos[name] = repo

    repos_file = ['repositories:']
    for name, repo in sorted(next_repos.items(), key=lambda t: len(t[1]['repos_blocking']), reverse=True):
        if repo['url']:
            repos_file.append("""  {name}:
    type: git
    url: {url}""".format(name=name, url=repo['url']))
    return "\n".join(repos_file)
