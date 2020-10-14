from setuptools import setup

setup(
    name='update-maintainers',
    version='0.1.0',
    packages=['update_maintainers'],
    install_requires=[
        'defusedxml',
    ],
    author='Shane Loretz',
    author_email='shane.loretz@gmail.com',
    description='Tool to update maintainers in a package.xml.',
    license='Apache 2.0',
    entry_points={
        'console_scripts': [
            'update-maintainers = update_maintainers.main:main',
        ],
    }
)
