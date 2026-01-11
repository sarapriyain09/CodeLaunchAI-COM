import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

function escapeXml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function getOrigin() {
  const configured = (process.env.PUBLIC_APP_ORIGIN || '').trim().replace(/\/+$/, '');
  if (configured) return configured;

  const vercelEnv = (process.env.VERCEL_ENV || '').toLowerCase();
  const vercelUrl = (process.env.VERCEL_URL || '').trim();

  // Vercel preview deployments: use the preview domain by default.
  if (vercelEnv && vercelEnv !== 'production' && vercelUrl) {
    return `https://${vercelUrl.replace(/^https?:\/\//, '')}`;
  }

  // Default canonical domain (local + production).
  return 'https://www.codlearn.com';
}

function urlPathFromRel(relPosix) {
  if (relPosix === 'index.html') return '/';
  if (relPosix.endsWith('/index.html')) {
    return `/${relPosix.slice(0, -'index.html'.length)}`;
  }
  return `/${relPosix}`;
}

async function listHtmlPages(frontendRoot) {
  const files = [];

  // Top-level pages.
  const top = await fs.readdir(frontendRoot, { withFileTypes: true });
  for (const entry of top) {
    if (entry.isFile() && entry.name.toLowerCase().endsWith('.html')) {
      files.push(path.join(frontendRoot, entry.name));
    }
  }

  // Blog pages.
  const blogDir = path.join(frontendRoot, 'blog');
  try {
    const blogEntries = await fs.readdir(blogDir, { withFileTypes: true });
    for (const entry of blogEntries) {
      if (entry.isFile() && entry.name.toLowerCase().endsWith('.html')) {
        files.push(path.join(blogDir, entry.name));
      }
    }
  } catch {
    // No blog dir.
  }

  return files.sort();
}

async function main() {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const frontendRoot = path.resolve(scriptDir, '..');
  const publicDir = path.join(frontendRoot, 'public');

  await fs.mkdir(publicDir, { recursive: true });

  const origin = getOrigin();
  const htmlFiles = await listHtmlPages(frontendRoot);

  const entries = [];
  for (const filePath of htmlFiles) {
    const rel = path.relative(frontendRoot, filePath).split(path.sep).join('/');
    const stat = await fs.stat(filePath);
    const lastmod = new Date(stat.mtimeMs).toISOString().slice(0, 10);

    const urlPath = urlPathFromRel(rel);
    entries.push({ urlPath, lastmod });
  }

  // Ensure / is present even if index.html is missing.
  if (!entries.some((e) => e.urlPath === '/')) {
    entries.unshift({ urlPath: '/', lastmod: new Date().toISOString().slice(0, 10) });
  }

  // De-dupe.
  const seen = new Set();
  const unique = [];
  for (const e of entries) {
    if (seen.has(e.urlPath)) continue;
    seen.add(e.urlPath);
    unique.push(e);
  }

  const sitemapLines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ];

  for (const e of unique) {
    const loc = escapeXml(`${origin}${e.urlPath}`);
    sitemapLines.push('  <url>');
    sitemapLines.push(`    <loc>${loc}</loc>`);
    sitemapLines.push(`    <lastmod>${escapeXml(e.lastmod)}</lastmod>`);
    sitemapLines.push('  </url>');
  }

  sitemapLines.push('</urlset>');
  sitemapLines.push('');

  const sitemapXml = sitemapLines.join('\n');
  const robotsTxt = [
    'User-agent: *',
    'Allow: /',
    `Sitemap: ${origin}/sitemap.xml`,
    '',
  ].join('\n');

  await fs.writeFile(path.join(publicDir, 'sitemap.xml'), sitemapXml, 'utf8');
  await fs.writeFile(path.join(publicDir, 'site.xml'), sitemapXml, 'utf8');
  await fs.writeFile(path.join(publicDir, 'robots.txt'), robotsTxt, 'utf8');

  console.log(`Generated sitemap.xml (${unique.length} URLs) for ${origin}`);
}

await main();
