from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterator, List

from app.config import NPM_CMD


def _popen(cmd: List[str], cwd: Path) -> subprocess.Popen:
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    try:
        return subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            creationflags=creationflags,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Failed to start build command: {cmd[0]} not found. "
            "Install Node.js/npm and/or set NPM_CMD in backend/orchestrator/.env. "
            f"Tried to run: {cmd!r}"
        ) from exc


def stream_npm_install(workspace: Path) -> Iterator[str]:
    yield 'Starting npm install...\n'
    # Some production environments set NODE_ENV=production / npm_config_production=true,
    # which causes `npm install` to omit devDependencies. Our generated Vite+TS projects
    # need devDependencies (notably `vite`) for `tsc -b` to resolve `vite/client`.
    process = _popen([NPM_CMD, 'install', '--include=dev'], workspace)
    assert process.stdout is not None
    tail: list[str] = []
    for line in process.stdout:
        yield line
        tail.append(line)
        if len(tail) > 60:
            tail.pop(0)
    rc = process.wait()
    if rc != 0:
        snippet = ''.join(tail)[-2000:]
        raise RuntimeError(f'npm install failed (exit code {rc})\n--- tail ---\n{snippet}')


def stream_npm_build(workspace: Path) -> Iterator[str]:
    yield 'Starting npm run build...\n'
    process = _popen([NPM_CMD, 'run', 'build'], workspace)
    assert process.stdout is not None
    tail: list[str] = []
    for line in process.stdout:
        yield line
        tail.append(line)
        if len(tail) > 80:
            tail.pop(0)
    rc = process.wait()
    if rc != 0:
        snippet = ''.join(tail)[-2500:]
        raise RuntimeError(f'npm run build failed (exit code {rc})\n--- tail ---\n{snippet}')


def node_modules_exists(workspace: Path) -> bool:
    return (workspace / 'node_modules').exists()


def has_vite_client_types(workspace: Path) -> bool:
    # TypeScript resolves `vite/client` from node_modules/vite/client.d.ts.
    return (workspace / 'node_modules' / 'vite' / 'client.d.ts').exists()


def node_modules_ready_for_build(workspace: Path) -> bool:
    return node_modules_exists(workspace) and has_vite_client_types(workspace)
