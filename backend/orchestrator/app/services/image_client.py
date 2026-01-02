from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

import httpx


PICSUM_SEED_RE = re.compile(r"https://picsum\.photos/seed/(?P<seed>[a-zA-Z0-9_-]+)/(?P<w>\d+)/(?P<h>\d+)")


@dataclass(frozen=True)
class ImageGenConfig:
    enabled: bool
    max_images: int
    model: str
    size: str
    base_url: str
    api_key: str | None


def load_image_gen_config() -> ImageGenConfig:
    enabled = os.getenv('GENERATE_IMAGES', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}
    max_images = int(os.getenv('MAX_IMAGES_PER_PROJECT', '6'))
    model = os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-1')
    size = os.getenv('OPENAI_IMAGE_SIZE', '1024x1024')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    api_key = os.getenv('OPENAI_API_KEY')

    return ImageGenConfig(
        enabled=enabled,
        max_images=max(0, max_images),
        model=model,
        size=size,
        base_url=base_url,
        api_key=api_key,
    )


def extract_picsum_seeds(files: Dict[str, str]) -> List[str]:
    seeds: Set[str] = set()
    for path, content in files.items():
        if not path.endswith(('.tsx', '.ts', '.jsx', '.js')):
            continue
        for match in PICSUM_SEED_RE.finditer(content):
            seed = match.group('seed')
            if seed:
                seeds.add(seed)
    return sorted(seeds)


def rewrite_picsum_urls_to_local(files: Dict[str, str], available_seeds: Iterable[str]) -> Dict[str, str]:
    seeds_set = set(available_seeds)

    def replace(match: re.Match) -> str:
        seed = match.group('seed')
        if seed in seeds_set:
            return f"/assets/{seed}.png"
        return match.group(0)

    out: Dict[str, str] = {}
    for path, content in files.items():
        if path.endswith(('.tsx', '.ts', '.jsx', '.js')):
            out[path] = PICSUM_SEED_RE.sub(replace, content)
        else:
            out[path] = content
    return out


async def generate_png_for_seed(
    *,
    seed: str,
    product_name: str,
    theme_style: str,
    timeout_s: float = 90.0,
) -> bytes:
    cfg = load_image_gen_config()
    if not (cfg.api_key and cfg.api_key.strip()):
        raise RuntimeError('OPENAI_API_KEY is not set')

    url = f"{cfg.base_url}/images/generations"
    headers = {
        'Authorization': f"Bearer {cfg.api_key}",
        'Content-Type': 'application/json',
    }

    # Keep prompt tight + safe: no people, no logos, no text.
    prompt = (
        f"Create a high-quality website image for '{product_name}'. "
        f"Subject: {seed.replace('-', ' ')}. "
        f"Style: {theme_style}. "
        "No text, no logos, no watermarks. Crisp, modern, web-hero friendly."
    )

    payload = {
        'model': cfg.model,
        'prompt': prompt,
        'size': cfg.size,
        'n': 1,
        'response_format': 'b64_json',
    }

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    try:
        b64 = (data.get('data') or [None])[0].get('b64_json')  # type: ignore[union-attr]
    except Exception:
        b64 = None

    if not isinstance(b64, str) or not b64.strip():
        raise RuntimeError('OpenAI Images API returned no image data')

    return base64.b64decode(b64)


async def maybe_generate_images_and_rewrite_files(
    *,
    files: Dict[str, str],
    workspace: Path,
    product_name: str,
    theme_style: str,
) -> Tuple[Dict[str, str], List[str]]:
    cfg = load_image_gen_config()
    if not cfg.enabled:
        return files, []

    if not (cfg.api_key and cfg.api_key.strip()):
        # Best-effort: if not configured, keep remote placeholder images.
        return files, []

    seeds = extract_picsum_seeds(files)
    if not seeds or cfg.max_images <= 0:
        return files, []

    seeds = seeds[: cfg.max_images]

    assets_dir = (workspace / 'public' / 'assets')
    assets_dir.mkdir(parents=True, exist_ok=True)

    generated: List[str] = []
    for seed in seeds:
        out_path = assets_dir / f"{seed}.png"
        if out_path.exists():
            generated.append(seed)
            continue

        try:
            png = await generate_png_for_seed(
                seed=seed,
                product_name=product_name,
                theme_style=theme_style,
            )
            out_path.write_bytes(png)
            generated.append(seed)
        except Exception:
            # Best-effort: keep placeholder URL for this seed.
            continue

    rewritten = rewrite_picsum_urls_to_local(files, generated)
    return rewritten, generated
