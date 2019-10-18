from setuptools import setup, find_packages
setup(
    name='ros1_repo_graph',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'graphviz',
        'git+https://github.com/ros-infrastructure/ros_buildfarm.git',
    ],
    author='Shane Loretz',
    author_email='shane.loretz@gmail.com',
    description='Tool to visualize repos in a rosdistro.',
    license='Apache 2.0',
    entry_points={
        'console_scripts': [
            'ros1-repo-graph = ros1_repo_graph.main:main',
        ],
    }
)
