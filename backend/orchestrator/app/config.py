from __future__ import annotations

import os
import shutil
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACES_DIR = Path(os.getenv('WORKSPACES_DIR', BASE_DIR / 'generated_workspaces'))


def _resolve_npm_cmd() -> str:
	# On Windows, npm is commonly a .cmd shim and subprocess(shell=False) may fail
	# if we try to execute just "npm".
	env = os.getenv('NPM_CMD')
	if env and env.strip():
		return env.strip()

	if os.name == 'nt':
		preferred = ['npm.cmd', 'npm.exe', 'npm']
	else:
		preferred = ['npm']

	for candidate in preferred:
		resolved = shutil.which(candidate)
		if resolved:
			return resolved

	# Fallback to a sensible default name; callers will surface a friendly error.
	return 'npm.cmd' if os.name == 'nt' else 'npm'


NPM_CMD = _resolve_npm_cmd()