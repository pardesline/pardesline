"""Start the pardesline MCP server for the Claude Code plugin.

The directory wants plugins to start a file they ship, so this file is what the
plugin manifest runs. It hands stdin and stdout, the MCP protocol channel, to
`pardesline mcp` when the package is installed, or to `python -m
pardesline.mcp_server` from the interpreter that runs this file. Everything it
prints goes to stderr, which the client shows as log output.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

HINT = (
    "pardesline is not installed for this Python. Install it with\n"
    '    pip install "pardesline[all]"\n'
    "or point the plugin at an environment that has it. Documentation:\n"
    "    https://pardesline.github.io/pardesline/latest/mcp/"
)


def main() -> int:
    args = sys.argv[1:]
    try:
        import pardesline.mcp_server  # noqa: F401  (the interpreter running this file has the package)
    except ImportError:
        exe = shutil.which("pardesline")
        if exe is None:
            print(HINT, file=sys.stderr)
            return 1
        cmd = [exe, "mcp", *args]
    else:
        cmd = [sys.executable, "-m", "pardesline.mcp_server", *args]
    completed = subprocess.run(cmd, env=os.environ, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
