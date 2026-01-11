from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape


_SITEMAP_XMLNS = "http://www.sitemaps.org/schemas/sitemap/0.9"


def _lastmod_date(path: Path) -> str:
    dt = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return dt.date().isoformat()


def generate_sitemap_xml(*, workspace_root: Path, origin: str) -> str:
    """Generate a sitemap.xml from the built static site under workspace_root/app.

    - Includes / and /app/ plus every *.html file under app/ (excluding assets/).
    - Uses file mtimes for <lastmod> (date only).
    """

    origin = (origin or "").strip().rstrip("/")
    if not origin:
        origin = "http://localhost:7080"

    app_dir = workspace_root / "app"

    urls: list[tuple[str, str]] = []

    # Home + /app/ are both canonical entry points.
    app_index = app_dir / "index.html"
    if app_index.exists():
        lm = _lastmod_date(app_index)
        urls.append(("/", lm))
        urls.append(("/app/", lm))
    else:
        # Fall back to a fixed date if the build output isn't present.
        today = datetime.now(timezone.utc).date().isoformat()
        urls.append(("/", today))
        urls.append(("/app/", today))

    if app_dir.exists():
        for html_path in sorted(app_dir.rglob("*.html")):
            rel = html_path.relative_to(app_dir).as_posix()

            if rel == "index.html":
                continue
            if rel.startswith("assets/"):
                continue

            urls.append((f"/app/{rel}", _lastmod_date(html_path)))

    # De-dup while preserving order.
    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for url_path, lastmod in urls:
        if url_path in seen:
            continue
        seen.add(url_path)
        deduped.append((url_path, lastmod))

    parts: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{_SITEMAP_XMLNS}">',
    ]

    for url_path, lastmod in deduped:
        loc = escape(f"{origin}{url_path}")
        parts.append("  <url>")
        parts.append(f"    <loc>{loc}</loc>")
        parts.append(f"    <lastmod>{escape(lastmod)}</lastmod>")
        parts.append("  </url>")

    parts.append("</urlset>")
    parts.append("")
    return "\n".join(parts)


def generate_robots_txt(*, origin: str) -> str:
    origin = (origin or "").strip().rstrip("/")
    if not origin:
        origin = "http://localhost:7080"

    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {origin}/sitemap.xml",
            "",
        ]
    )
