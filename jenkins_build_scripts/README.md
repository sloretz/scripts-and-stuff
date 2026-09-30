# Jenkins Build Scripts

This directory contains Python scripts that get data from Jenkins servers and analyze build results.

## Requirements

These scripts use Python 3 and third-party packages:

* `jenkinsapi`
* `keyring`
* `matplotlib`
* `requests`

To install these packages, run this command:

```bash
pip install jenkinsapi keyring matplotlib requests
```

## Scripts

### `dangitjenkins.py`

This script connects to a Jenkins server and prints Markdown reports of test failures. When you run the script, it asks for a Jenkins username and password.

The script contains three report functions:

* `verb_compare`: This function compares test failures in one pull request build against the last 15 builds of a continuous integration job.
* `verb_tally_failures`: This function counts test failures across the last seven builds of a list of jobs. It also calculates the failure percentage for each test.
* `print_latest_failures`: This function finds all tests that failed in the most recent build of each job in a list.

By default, the `__main__` block runs `verb_tally_failures` for the `ignition_gui-ci-default-zesty-amd64` job.

#### Usage

1. Edit the `__main__` block in `dangitjenkins.py` to select a report function and target jobs.
2. Run the script with the URL of the Jenkins server:

```bash
./dangitjenkins.py https://build.osrfoundation.org
```

### `fetch_job_logs.py`

This script downloads console logs from recent builds of a Jenkins job. It gets the latest build number from the Jenkins JSON API. Then it writes the console text for each selected build to `<job_name>_<build_number>.txt` in the current directory.

The script accepts three command-line arguments:

* `--url`: The URL of the Jenkins job.
* `--number`: The number of build logs to download.
* `--step`: The interval between build numbers. The default value is `1`.

#### Usage

Run the script with the job URL and the number of builds:

```bash
./fetch_job_logs.py --url https://ci.ros2.org/view/nightly/job/nightly_win_deb/ --number 50 --step 1
```

### `gazeboci_report.py`

This script connects to `https://build.osrfoundation.org` and prints a Markdown report for a predefined list of Gazebo and Ignition jobs. When you run the script, it asks for a Jenkins username and password.

The report contains three sections:

* A summary table that shows the number and percentage of builds in each status (`SUCCESS`, `FAILURE`, `UNSTABLE`, and `ABORTED`).
* A list of failed jobs. The script separates failed jobs that succeeded in the past from failed jobs that never succeeded.
* A list of unstable builds. The script groups unstable builds by `cppcheck` violations, compiler warnings, single test failures, and unrecognized failures.

#### Usage

Run the script from the command line:

```bash
./gazeboci_report.py
```

### `plot_build_test_times.py`

This script reads console log files from a directory and shows six plots of package durations in `matplotlib`. All log files in the directory must match the `<job_name>_<number>.txt` name format and come from the same job. You can use `fetch_job_logs.py` to download these log files.

The script reads the `build` and `test` subsections in each log file and shows these six plots:

* Build durations for individual packages across build numbers.
* Test durations for individual packages across build numbers.
* Total build duration for each build number.
* Total test duration for each build number.
* The 10 packages with the highest average build duration.
* The 10 packages with the highest average test duration.

#### Usage

Run the script and specify the directory that contains the log files:

```bash
./plot_build_test_times.py --directory /path/to/logs
```

### `plot_build_times.py`

This script connects to a Jenkins server and gets build durations for a job over a specified number of days. It shows a `matplotlib` plot of build durations in seconds by date. If `matplotlib` is not available, the script prints the timestamp and duration of each build to the terminal.

The script accepts four command-line arguments:

* `--jenkins-url`: The URL of the Jenkins server. The default value is `https://ci.ros2.org/`.
* `--job-name`: The name of the Jenkins job. The default value is `ci_linux`.
* `--username`: The Jenkins username for authentication. This argument is optional.
* `--days-to-fetch`: The number of past days to include. The default value is `30`.

#### Usage

1. If you use `--username`, store your Jenkins API token in the system keyring first:

```bash
keyring set jenkins-api-token job-statistics
```

2. Run the script with your target job and date range:

```bash
./plot_build_times.py --jenkins-url https://ci.ros2.org/ --job-name ci_linux --days-to-fetch 30
```

---

### `ros2ci_report.py`

This script connects to `https://ci.ros2.org` and prints a Markdown report of failed tests from the latest ROS 2 nightly builds. It reads credentials from the `JENKINS_GITHUB_USER` and `JENKINS_GITHUB_TOKEN` environment variables.

The script examines the latest build for a predefined list of nightly jobs. It groups failed tests by the exact combination of jobs in which the tests failed. The script also contains a `print_flaky_tests` helper function that counts test failures across the last seven builds.

#### Usage

1. Set the environment variables for authentication:

```bash
export JENKINS_GITHUB_USER="your_username"
export JENKINS_GITHUB_TOKEN="your_token"
```

2. Run the script:

```bash
./ros2ci_report.py
```

---

### `time_windows_jobs.py`

This file is empty and contains no code.
