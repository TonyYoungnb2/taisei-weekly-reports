#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_search.py — Build the client-side full-text search index (Pagefind).

No backend, no CDN. Uses Pagefind's EXTENDED binary (includes Chinese/Japanese/
Korean word segmentation) to index all static HTML in this repo and emit a
self-contained `pagefind/` folder that is committed into the repo and served as
static assets by EdgeOne Pages.

The binary is downloaded ON DEMAND into `vendor/pagefind/<os>/` (git-ignored)
instead of being committed — the extended binary is ~56 MB and would bloat the
repo / stall EdgeOne deploys. The generated `pagefind/` bundle (~700 KB) is what
is actually served, so the repo stays light.

Pagefind release (pinned): v1.5.2 extended
  Linux:   pagefind_extended-v1.5.2-x86_64-unknown-linux-musl.tar.gz
  Windows: pagefind_extended-v1.5.2-x86_64-pc-windows-msvc.tar.gz

Usage:
  python build_search.py            # index the whole site ( --site . )

Pagefind indexing scope:
  Once ANY page contains a `data-pagefind-body` element, Pagefind ONLY indexes
  pages that have that marker. The agent marks report/index/projects/map, so all
  four are indexed. Adding the marker to a new page automatically includes it.
"""
import os
import sys
import platform
import subprocess
import tarfile
import io
import urllib.request

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

PAGEFIND_VERSION = "v1.5.2"
RELEASE_BASE = "https://github.com/Pagefind/pagefind/releases/download/%s" % PAGEFIND_VERSION

# Cache dir for the downloaded binary (git-ignored).
BIN_DIR = os.path.join(REPO_ROOT, "vendor", "pagefind")
WIN_BIN = os.path.join(BIN_DIR, "pagefind-win", "pagefind.exe")
LINUX_BIN = os.path.join(BIN_DIR, "pagefind-linux", "pagefind")


def pick_asset():
    system = platform.system()
    if system == "Windows":
        return "pagefind_extended-%s-x86_64-pc-windows-msvc.tar.gz" % PAGEFIND_VERSION, WIN_BIN
    return "pagefind_extended-%s-x86_64-unknown-linux-musl.tar.gz" % PAGEFIND_VERSION, LINUX_BIN


def download_binary():
    asset, dest = pick_asset()
    url = "%s/%s" % (RELEASE_BASE, asset)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print("Downloading Pagefind %s -> %s" % (asset, dest))
    print("  %s" % url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "build_search/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
    except Exception as exc:  # noqa: BLE001
        print("ERROR: download failed: %s" % exc, file=sys.stderr)
        return None
    print("  downloaded %d bytes" % len(data))
    # Tar contains a single `pagefind` binary at the archive root.
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            member = None
            for m in tf.getmembers():
                if m.name.endswith("pagefind") or m.name.endswith("pagefind.exe"):
                    member = m
                    break
            if member is None:
                print("ERROR: pagefind binary not found in archive", file=sys.stderr)
                return None
            f = tf.extractfile(member)
            if f is None:
                print("ERROR: cannot extract pagefind binary", file=sys.stderr)
                return None
            with open(dest, "wb") as out:
                out.write(f.read())
    except Exception as exc:  # noqa: BLE001
        print("ERROR: extract failed: %s" % exc, file=sys.stderr)
        return None
    if not dest.endswith(".exe"):
        try:
            os.chmod(dest, 0o755)
        except OSError:
            pass
    print("  saved to %s" % dest)
    return dest


def pick_binary():
    system = platform.system()
    binary = WIN_BIN if system == "Windows" else LINUX_BIN
    if not os.path.isfile(binary):
        binary = download_binary()
    return binary


def main():
    binary = pick_binary()
    if not binary or not os.path.isfile(binary):
        print("ERROR: pagefind binary unavailable", file=sys.stderr)
        return 1

    cmd = [binary, "--site", "."]
    print("Running: %s" % " ".join(cmd))
    print("Working dir: %s" % REPO_ROOT)
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT)
    except OSError as exc:
        print("ERROR: failed to launch pagefind: %s" % exc, file=sys.stderr)
        return 1

    if proc.returncode == 0:
        out_dir = os.path.join(REPO_ROOT, "pagefind")
        print("")
        print("Done. Search bundle written to: %s" % out_dir)
        print("Remember to COMMIT the pagefind/ folder (static deploy has no build step).")
    else:
        print("pagefind exited with code %d" % proc.returncode, file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
