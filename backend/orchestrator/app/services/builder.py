from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import NPM_CMD
from app.services.stream_runner import node_modules_ready_for_build


class BuildError(RuntimeError):
    pass


def _run_command(cmd: list[str], cwd: Path) -> str:
    try:
        process = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, shell=False)
    except FileNotFoundError as exc:
        raise BuildError(
            f"Build dependency not found: {cmd[0]} (WinError 2). "
            "Install Node.js/npm and/or set NPM_CMD in backend/orchestrator/.env. "
            f"Tried to run: {cmd!r}"
        ) from exc
    output = (process.stdout or '') + '\n' + (process.stderr or '')
    if process.returncode != 0:
        raise BuildError(output[-2000:])
    return output[-2000:]


def npm_install_if_needed(workspace: Path) -> str:
    if node_modules_ready_for_build(workspace):
        return 'node_modules already exists; skipped install.'
    if (workspace / 'node_modules').exists():
        return _run_command([NPM_CMD, 'install', '--include=dev'], workspace)
    return _run_command([NPM_CMD, 'install', '--include=dev'], workspace)


def npm_build(workspace: Path) -> str:
    return _run_command([NPM_CMD, 'run', 'build'], workspace)


def clean_dist(workspace: Path) -> None:
    dist = workspace / 'dist'
    if dist.exists():
        shutil.rmtree(dist)