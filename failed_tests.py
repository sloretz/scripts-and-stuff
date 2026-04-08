#!/usr/bin/env python3

import sys
import re
import argparse

def extract_package_logs(lines):
    """
    Parses the log to isolate the output block for each package.
    Matches from '--- output: <package>' to 'Finished <<< <package>'
    """
    package_logs = {}
    current_pkg = None
    
    # Regex to match the start and end of a package's output block
    start_re = re.compile(r'---\s*output:\s+([^\s]+)')
    end_re = re.compile(r'Finished <<<\s+([^\s]+)')
    
    for line in lines:
        start_match = start_re.search(line)
        if start_match:
            current_pkg = start_match.group(1).strip()
            package_logs[current_pkg] = []
            
        if current_pkg:
            package_logs[current_pkg].append(line)
            
        end_match = end_re.search(line)
        if end_match and current_pkg == end_match.group(1).strip():
            current_pkg = None
            
    return package_logs

def find_failed_tests(log_lines):
    """
    Scans the lines of a package log to identify the names of tests that failed.
    """
    failed_tests = set()
    
    # Matches GTest failures: e.g. "[  FAILED  ] TestName"
    gtest_re = re.compile(r'\[\s*FAILED\s*\]\s+([^\s]+)')
    
    # Matches PyTest / Python Unittest failures: e.g. "FAIL: test_name" or "ERROR: test_name"
    unittest_re = re.compile(r'(?:FAIL|ERROR):\s+([^\s]+)')
    
    # Matches raw PyTest summary failures: e.g. "FAILED path/to/file.py::test_name"
    pytest_summary_re = re.compile(r'FAILED\s+.*::([^\s]+)')
    
    for line in log_lines:
        if "tests, listed below" in line:
            continue
        m1 = gtest_re.search(line)
        if m1 and "ms)" not in m1.group(1):
            failed_tests.add(m1.group(1))
            
        m2 = unittest_re.search(line)
        if m2:
            failed_tests.add(m2.group(1))
            
        m3 = pytest_summary_re.search(line)
        if m3:
            failed_tests.add(m3.group(1))
            
    return sorted(list(failed_tests))

def extract_failed_test_output(log_lines, test_name):
    """
    Attempts to extract the specific block of log output related to a failed test.
    """
    output = []
    capturing = False
    
    # Markers for GTest and Unittest output blocks
    gtest_start = f"[ RUN      ] {test_name}"
    gtest_end = f"[  FAILED  ] {test_name}"
    
    unit_start = f"FAIL: {test_name}"
    unit_error_start = f"ERROR: {test_name}"
    pytest_start = f"_{test_name}_"  # Pytest usually underlines the test name
    
    unit_end = "----------------------------------------------------------------------"
    
    dashed_line_count = 0
    
    for line in log_lines:
        if gtest_start in line or unit_start in line or unit_error_start in line or pytest_start in line:
            capturing = True
            dashed_line_count = 0
            
        if capturing:
            output.append(line)
            
        if capturing:
            if gtest_end in line:
                capturing = False
            elif unit_end in line:
                dashed_line_count += 1
                # Unittest tracebacks usually end with a second dashed line
                if dashed_line_count >= 2:
                    capturing = False
                    
    return "".join(output)

def main():
    parser = argparse.ArgumentParser(description="Extract failed tests from CI log files")
    parser.add_argument('--names-only', action='store_true', help="Show just failed test names")
    parser.add_argument('--packages', nargs='+', help="Show just failed tests from given packages")
    args = parser.parse_args()

    # 1. Read all input from stdin
    lines = sys.stdin.readlines()
    
    # 2. Isolate the logs by package using the specified regex boundaries
    pkg_logs = extract_package_logs(lines)
    
    # 3. Filter to the specified packages if requested
    packages_to_check = args.packages if args.packages else pkg_logs.keys()
    
    for pkg in packages_to_check:
        if pkg not in pkg_logs:
            continue
            
        log = pkg_logs[pkg]
        failed_tests = find_failed_tests(log)
        
        if not failed_tests:
            continue
            
        if args.names_only:
            for t in failed_tests:
                print(f"{pkg}: {t}")
        else:
            for t in failed_tests:
                print(f"=== Failed Test: {t} (Package: {pkg}) ===")
                ext_log = extract_failed_test_output(log, t)
                
                if ext_log:
                    print(ext_log.strip())
                else:
                    # Fallback to showing context around the failure if exact parsing fails
                    print(f"Could not isolate exact test log block. Here is the failure context:")
                    for i, line in enumerate(log):
                        if t in line and ("FAIL" in line or "ERROR" in line):
                            start = max(0, i - 5)
                            end = min(len(log), i + 15)
                            print("".join(log[start:end]).strip())
                            break
                print("\n" + "=" * 80 + "\n")

if __name__ == '__main__':
    main()