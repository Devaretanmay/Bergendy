"""boundary._exec_shim - entry point called by workspace shim scripts.

Usage (from a .boundary/bin/<agent> shim):
    python3 -m boundary._exec_shim <agent_name> <workspace_root> [argv...]
"""

import argparse
import sys
from bergendy.cli.main import cmd_exec_shim


if __name__ == "__main__":
    cmd_exec_shim(argparse.Namespace(shim_args=sys.argv[1:]))
