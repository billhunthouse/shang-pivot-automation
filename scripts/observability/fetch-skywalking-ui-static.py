#!/usr/bin/env python3
"""Copy SkyWalking UI static assets and patch the SPA router base.

SkyWalking UI's Vite build hardcodes `createWebHistory("/")`. When the UI is
mounted under a subpath such as /skywalking/, the SPA renders its 404 page.
This script downloads the UI's static assets and rewrites the router base.

Example on the server:

    python3 scripts/observability/fetch-skywalking-ui-static.py \
      --ui-url http://127.0.0.1:60086 \
      --out /opt/skywalking/ui-static \
      --base /skywalking/
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import urllib.parse
import urllib.request

STATIC_RE = re.compile(r"(?:/static|static)/[A-Za-z0-9_./@-]+\.(?:js|css|woff2?|ttf|png|svg|ico)")


def fetch(url: str) -> tuple[bytes, str]:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read(), response.headers.get("Content-Type", "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui-url", default="http://127.0.0.1:60086")
    parser.add_argument("--out", default="/opt/skywalking/ui-static")
    parser.add_argument("--base", default="/skywalking/")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    base = args.base if args.base.endswith("/") else args.base + "/"
    if args.clean:
        shutil.rmtree(args.out, ignore_errors=True)
    os.makedirs(args.out, exist_ok=True)

    seen: set[str] = set()
    queue = ["/"]
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        url = args.ui_url.rstrip("/") + path
        try:
            data, content_type = fetch(url)
        except Exception as exc:  # noqa: BLE001 - report and continue crawling
            print(f"skip {path}: {exc}")
            continue

        if path.startswith("/static/"):
            target = os.path.join(args.out, path.lstrip("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(data)

        if any(kind in content_type for kind in ("javascript", "css", "html")):
            text = data.decode("utf-8", errors="ignore")
            for match in STATIC_RE.findall(text):
                candidate = match if match.startswith("/") else "/" + match
                if candidate not in seen:
                    queue.append(candidate)

    patched = 0
    old = 'history:X$("/")'
    new = f'history:X$("{base}")'
    for root, _, files in os.walk(args.out):
        for name in files:
            if not name.endswith(".js"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="ignore") as handle:
                text = handle.read()
            if old in text:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text.replace(old, new))
                patched += 1
                print(f"patched {path}")

    print(f"assets={len([p for p in seen if p.startswith('/static/')])} patched={patched} base={base}")
    return 0 if patched else 1


if __name__ == "__main__":
    raise SystemExit(main())
