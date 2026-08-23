"""Validate that the built SPA keeps deep links working.

Checks performed:
1. dist/index.html exists after a frontend build.
2. nginx.conf serves index.html as the SPA fallback (try_files ... /index.html).
3. Every static asset referenced from dist/index.html exists on disk.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "datathon" / "dist"
NGINX = ROOT / "nginx.conf"


def fail(messages: list[str]) -> int:
    print("SPA ROUTING CHECK FAILED:")
    for message in messages:
        print(f"  - {message}")
    return 1


def main() -> int:
    problems: list[str] = []

    index_html = DIST / "index.html"
    if not index_html.is_file():
        problems.append(f"{index_html.relative_to(ROOT)} not found - run `npm run build` first.")
        return fail(problems)

    html = index_html.read_text(encoding="utf-8")

    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
    for asset in assets:
        if not (DIST / asset.lstrip("/")).is_file():
            problems.append(f"asset referenced by index.html is missing: {asset}")

    nginx_conf = NGINX.read_text(encoding="utf-8") if NGINX.is_file() else ""
    fallback_pattern = re.compile(r"try_files\s+\S+\s+/index\.html")
    if not fallback_pattern.search(nginx_conf):
        problems.append(
            "nginx.conf has no SPA fallback rule (`try_files $uri /index.html;`) - "
            "deep links such as /dashboard would 404 after a page refresh."
        )
    if 'location /' not in nginx_conf:
        problems.append("nginx.conf is missing a `location /` block.")

    if problems:
        return fail(problems)

    print(f"SPA routing check passed ({len(assets)} hashed assets verified, nginx fallback present).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
