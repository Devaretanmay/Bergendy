"""Minimal output recording interface for box isolation.

Legacy 12,000-line compression engine was pruned. This provides
the recording and accounting interface used by Box compartments.
"""

from typing import Any


class OutputCompressor:
    """Lightweight compartment output recorder."""

    def __init__(self):
        self.compressed_outputs: dict[str, str] = {}

    def record(self, compartment_name: str, result: Any) -> None:
        """Record the output of a compartment."""
        if isinstance(result, str):
            self.compressed_outputs[compartment_name] = result
        else:
            self.compressed_outputs[compartment_name] = str(result)

    def log_totals(self) -> None:
        """No-op log handler for compartment termination."""
        pass
