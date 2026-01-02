from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.schemas.files import FileItem


def _safe_join(base: Path, rel_path: str) -> Path:
    normalized = rel_path.replace('\\', '/').lstrip('/')
    target = (base / normalized).resolve()
    base_resolved = base.resolve()
    if not str(target).startswith(str(base_resolved)):
        raise ValueError(f'Unsafe path detected: {rel_path}')
    return target


def write_file_tree(base: Path, files: Iterable[FileItem]) -> None:
    base.mkdir(parents=True, exist_ok=True)
    for file_item in files:
        output = _safe_join(base, file_item.path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(file_item.content, encoding='utf-8')


def ensure_gitignore(base: Path) -> None:
    gitignore = base / '.gitignore'
    if gitignore.exists():
        return
    gitignore.write_text('node_modules/\ndist/\n.env\n', encoding='utf-8')