"""
Milestone 1 Iteration 2 Adversarial Stress Verification Runner.
Executes all adversarial, tier-5, and challenger stress test suites.
"""

import sys
import pytest

if __name__ == "__main__":
    test_files = [
        "tests/test_adversarial_m1.py",
        "tests/test_tier5_adversarial.py",
        "tests/test_challenger_stress_harness.py",
    ]
    print(f"Running adversarial verification on: {test_files}")
    exit_code = pytest.main(["-v", *test_files])
    sys.exit(exit_code)
