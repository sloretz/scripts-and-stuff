#!/usr/bin/env python3
"""
review_new_packages.py
A wrapper script that invokes the review-new-packages CLI tool.

Usage:
  ./rosdistro_duty/review_new_packages.py <PR_URL>
"""

import sys
from rosdistro_duty.cli import main

if __name__ == "__main__":
    sys.exit(main())
