# Copyright 2026 Bergendy Authors
# SPDX-License-Identifier: Apache-2.0

"""Proof Engine for Bergendy Buddy.

Enforces the Finish Instinct: 'NO EVIDENCE ≠ PASS'.
Executes verification suites, inspects exit codes, and extracts test evidence.
"""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass


@dataclass
class TestExecution:
    command: str
    exit_code: int
    passed_count: int
    failed_count: int
    duration_ms: int
    stdout: str
    stderr: str

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and self.failed_count == 0 and self.passed_count > 0


class ProofEngine:
    """Executes and records verifiable evidence for completion checks."""

    @staticmethod
    def parse_test_counts(output: str) -> tuple[int, int]:
        """Extract passed and failed test counts from common test runners."""
        passed = 0
        failed = 0

        # Pytest: "12 passed, 2 failed in 0.45s"
        m_passed = re.search(r"(\d+)\s+passed", output)
        if m_passed:
            passed = int(m_passed.group(1))
        m_failed = re.search(r"(\d+)\s+failed", output)
        if m_failed:
            failed = int(m_failed.group(1))

        # Cargo test: "test result: ok. 134 passed; 0 failed"
        m_cargo = re.search(r"test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed", output)
        if m_cargo:
            passed = int(m_cargo.group(1))
            failed = int(m_cargo.group(2))

        # Jest / Vitest: "Tests: 2 failed, 12 passed, 14 total"
        m_jest_pass = re.search(r"(\d+)\s+passed,\s+\d+\s+total", output)
        if m_jest_pass and passed == 0:
            passed = int(m_jest_pass.group(1))
        m_jest_fail = re.search(r"(\d+)\s+failed,\s+\d+\s+passed", output)
        if m_jest_fail and failed == 0:
            failed = int(m_jest_fail.group(1))

        # Go test: "PASS" or "FAIL"
        if passed == 0 and failed == 0:
            if "PASS" in output and "FAIL" not in output:
                passed = 1
            elif "FAIL" in output:
                failed = 1

        return passed, failed

    def run(self, command: str, cwd: str = ".") -> TestExecution:
        start_ns = time.perf_counter_ns()
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            passed, failed = self.parse_test_counts(res.stdout + "\n" + res.stderr)
            return TestExecution(
                command=command,
                exit_code=res.returncode,
                passed_count=passed,
                failed_count=failed,
                duration_ms=duration_ms,
                stdout=res.stdout,
                stderr=res.stderr,
            )
        except subprocess.TimeoutExpired as te:
            duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            return TestExecution(
                command=command,
                exit_code=124,
                passed_count=0,
                failed_count=1,
                duration_ms=duration_ms,
                stdout=te.stdout or "",
                stderr="Timed out after 120 seconds",
            )
        except Exception as ex:
            duration_ms = (time.perf_counter_ns() - start_ns) // 1_000_000
            return TestExecution(
                command=command,
                exit_code=1,
                passed_count=0,
                failed_count=1,
                duration_ms=duration_ms,
                stdout="",
                stderr=str(ex),
            )
