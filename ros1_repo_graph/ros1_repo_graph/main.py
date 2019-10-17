from .repo_info import source_entries_repo_info
from .repo_info import who_is_next
from .repo_info import who_is_next_vcstool
from .repo_info import dot_graph


def main():
    print('Hello world')
    repo_info = source_entries_repo_info(
        'https://raw.githubusercontent.com/ros-infrastructure/ros_buildfarm_config/master/index.yaml',
        'noetic', depth=3)

    print(dot_graph(repo_info))
    print(who_is_next(repo_info))
    print(who_is_next_vcstool(repo_info))
