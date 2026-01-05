from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import NPM_CMD
from app.services.stream_runner import node_modules_ready_for_build


class BuildError(RuntimeError):
    pass


def ensure_preview_router_basename(workspace: Path) -> None:
    main_tsx = workspace / 'src' / 'main.tsx'
    if not main_tsx.exists():
        return

    try:
        text = main_tsx.read_text(encoding='utf-8')
    except Exception:
        return

    if 'BrowserRouter' not in text:
        return

    # If the file already has a helper, make sure it matches all preview mounts.
    # Older generated projects only matched /preview/{id} and would show "Page not found"
    # when hosted under /previews/{id}.
    if 'getRouterBasename' in text and '/preview/[^/]+' in text:
        text = text.replace(
            r"path.match(/^\/preview\/[^/]+/)",
            r"path.match(/^\/(?:preview|previews|p)\/[^/]+/)",
        )
        try:
            main_tsx.write_text(text, encoding='utf-8')
        except Exception:
            return
        return

    # Only patch the common template shape: BrowserRouter without basename.
    if 'basename=' in text or 'getRouterBasename' in text:
        return
    if '<BrowserRouter>' not in text:
        return

    helper = (
        "\nfunction getRouterBasename(): string {\n"
        "  const path = window.location.pathname || \"/\";\n"
        "  const match = path.match(/^\\/(?:preview|previews|p)\\/[^/]+/);\n"
        "  return match ? match[0] : \"/\";\n"
        "}\n"
    )

    if helper.strip() not in text:
        # Insert helper after the styles import if present, else after imports.
        marker = 'import "./styles.css";'
        if marker in text:
            text = text.replace(marker, marker + helper, 1)
        else:
            text = helper + text

    text = text.replace('<BrowserRouter>', '<BrowserRouter basename={getRouterBasename()}>', 1)

    try:
        main_tsx.write_text(text, encoding='utf-8')
    except Exception:
        return


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
    ensure_preview_router_basename(workspace)
    return _run_command([NPM_CMD, 'run', 'build'], workspace)


def clean_dist(workspace: Path) -> None:
    dist = workspace / 'dist'
    if dist.exists():
        shutil.rmtree(dist)