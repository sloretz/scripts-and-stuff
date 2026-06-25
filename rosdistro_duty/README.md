# ROSDistro Duty: PR Review Tool

A modularized Python package designed to automate and streamline the review of new or modified ROS package additions in `rosdistro` pull requests. It evaluates compliance with **REP-144 (ROS Package Naming)** and checks for OSI-approved licensing using the Gemini API.

---

## 1. Development Installation

To install this package for development inside your local virtual environment (`env3`), run the following command from the root of the repository:

```bash
./env3/bin/pip install -e "./rosdistro_duty[test]"
```

This installs:
- The `rosdistro-duty` package in **editable mode** (any changes you make to the code in `src/` will take effect immediately).
- The development/test dependencies, including `pytest`.
- The `review-new-packages` command-line executable in your virtual environment's bin folder.

---

## 2. Usage

Once installed, you can run the tool in two ways:

### Option A: Using the wrapper script
```bash
./rosdistro_duty/review_new_packages.py https://github.com/ros/rosdistro/pull/51902
```

### Option B: Using the installed CLI executable
```bash
./env3/bin/review-new-packages https://github.com/ros/rosdistro/pull/51902
```

### Requirements
Ensure that your credentials are set up:
- **GitHub Token**: Stored in the keyring as `github-api-token` for username `read-public-repos`, or set as the `GITHUB_TOKEN` environment variable.
- **Gemini API Key**: Stored in the keyring as `gemini` for username `api-key`, or set as the `GEMINI_API_KEY` environment variable.

---

## 3. Running Unit Tests

We have written comprehensive unit tests using `pytest` to verify the package XML parsing, license file detection, and distribution diff logic. Since these tests use mock folders and inputs, they run in milliseconds and do not require internet access or API credentials.

To run the unit tests, execute:

```bash
./env3/bin/pytest rosdistro_duty/tests
```

Or to run them with verbose output:

```bash
./env3/bin/pytest -v rosdistro_duty/tests
```
