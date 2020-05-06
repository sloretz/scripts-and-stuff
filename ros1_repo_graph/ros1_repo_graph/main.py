from .repo_info import releases_repo_info
from .repo_info import source_entries_repo_info
from .repo_info import who_is_next
from .repo_info import who_is_next_vcstool
from .repo_info import dot_graph
from .repo_info import filter_repos
from .repo_info import vcstool


def main():
    # repo_info = source_entries_repo_info(
    #     'https://raw.githubusercontent.com/ros-infrastructure/ros_buildfarm_config/master/index.yaml',
    #     'noetic')  # , depth=3)
    repo_info = releases_repo_info(
        'https://raw.githubusercontent.com/ros-infrastructure/ros_buildfarm_config/master/index.yaml',
        'noetic')  # , depth=3)


    # Print graph of repos being blocked, ignore repos who aren't blocked or blocking any others
    print(who_is_next(repo_info))
    # print(who_is_next_vcstool(repo_info))

    # Only care about dot graph to ros-desktop-full for the moment because there's too much other stuff
    # print(metapackages_info.keys())

    mvp = [
        'ackermann_msgs',
        'actionlib',
        'angles',
        'bond_core',
        'catkin',
        'class_loader',
        'cmake_modules',
        'common_msgs',
        'common_tutorials',
        'control_msgs',
        'control_toolbox',
        'diagnostics',
        'dynamic_reconfigure',
        'eigen_stl_containers',
        'executive_smach',
        'filters',
        'gazebo_ros_pkgs',
        'gencpp',
        'genlisp',
        'genmsg',
        'genpy',
        'geometric_shapes',
        'geometry',
        'geometry_tutorials',
        'image_common',
        'image_pipeline',
        'image_transport_plugins',
        'interactive_markers',
        'laser_assembler',
        'laser_filters',
        'laser_geometry',
        'laser_pipeline',
        'libg2o',
        'media_export',
        'message_generation',
        'message_runtime',
        'metapackages',
        'nodelet_core',
        'object_recognition_msgs',
        'octomap',
        'octomap_msgs',
        'pcl_msgs',
        'perception_pcl',
        'pluginlib',
        'python_qt_binding',
        'qt_gui_core',
        'random_numbers',
        'realtime_tools',
        'resource_retriever',
        'robot_state_publisher',
        'ros',
        'ros_comm',
        'ros_comm_msgs',
        'ros_tutorials',
        'rosbag_migration_rule',
        'rosconsole_bridge',
        'roscpp_core',
        'roslint',
        'roslisp',
        'rospack',
        'rqt',
        'rqt_common_plugins',
        'rqt_robot_plugins',
        'rviz',
        'stage',
        'stage_ros',
        'std_msgs',
        'unique_identifier',
        'urdf_tutorial',
        'urdfdom_py',
        'vision_opencv',
        'visualization_tutorials',
        'xacro',
    ]

    print(repr(repo_info['kdl_parser']))

    mvp_info = filter_repos(repo_info, target_repos=mvp)

    unreleased_mvp_info = {}
    for name, repo in mvp_info.items():
        if not repo['released']:
            unreleased_mvp_info[name] = repo

    print(vcstool(unreleased_mvp_info))

    print(dot_graph(unreleased_mvp_info))
