#!/usr/bin/env python3
from __future__ import annotations

import sys

from agent_baseline.meta_agent_tooling import run_meta_agent_baseline_integration_check_cli


if __name__ == "__main__":
    raise SystemExit(run_meta_agent_baseline_integration_check_cli(sys.argv[1:]))
