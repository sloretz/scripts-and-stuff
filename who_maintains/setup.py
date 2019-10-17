from setuptools import setup, find_packages
setup(
    name='who_maintains',
    version='0.1.0',
    packages=['who_maintains'],
    install_requires=[
        'catkin-pkg',
        'gitpython',
    ],
    author='Shane Loretz',
    author_email='shane.loretz@gmail.com',
    description='Tool to list maintainers in a workspace.',
    license='Apache 2.0',
    entry_points={
        'console_scripts': [
            'who-maintains = who_maintains.main:main',
        ],
    }
)
