# scripts-and-stuff
Miscellaneous scripts that make my life easier

## `make_repos_gist`

Pass a list of pull request URLs to this tool and it will create a ros2.repos file gist for you.

### Examples
Single PR
```
make-repos-gist https://github.com/ros2/rmw_fastrtps/pull/248
```

Single PR with shorthand PR identifier instead of full URL.
```
make-repos-gist ros2/rmw_fastrtps#248
```

Use crystal branch of ros2/ros2 for initial ros2.repos file
```
make-repos-gist --branch crystal https://github.com/ros2/rmw_fastrtps/pull/248
```

Multiple PRs (must be different repos)
```
make-repos-gist https://github.com/ros2/rmw_fastrtps/pull/248 https://github.com/ros2/rcl/pull/365
```

### Installation

```
python3 ./make_repos_gist/setup.py install
```

After installing, put a github API key in the system keyring that is capable of creating gists.

```
# This will prompt for a 'password'. Paste the github api token.
keyring set github-api-token may-create-gist
```
