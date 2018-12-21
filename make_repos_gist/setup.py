from setuptools import setup, find_packages
setup(
    name="make_repos_gist",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'PyGithub>=1.43.3',
        'keyring>=17.0.0',
        'requests>=2.21.0',
        'PyYAML>=3.13',
    ],
    author="Shane Loretz",
    author_email="shane.loretz@gmail.com",
    description="Tool to create a ros2.repos gist for testing ros2 PRs.",
    license="Apache 2.0",
    entry_points={
        'console_scripts': [
            'make-repos-gist = make_repos_gist:main',
        ],
    }
)
