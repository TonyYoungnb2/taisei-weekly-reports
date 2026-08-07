#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_search.py — Build the client-side full-text search index (Pagefind).

No backend, no CDN. Uses a LOCALLY VENDORED Pagefind binary (the "extended"
build, which includes Chinese/Japanese/Korean word segmentation) to index all
static HTML in this repo and emit a self-contained `pagefind/` folder that is
committed into the repo and served as static assets by EdgeOne Pages.

Vendored binaries:
  Windows: vendor/pagefind/pagefind-win/pagefind.exe
  Linux:   vendor/pagefind/pagefind-linux/pagefind

Usage:
  python build_search.py            # index the whole site ( --site . )

The generated bundle (pagefind/pagefind.js, pagefind-ui.js, wasm, index/, etc.)
MUST be committed so the static deploy has search with zero build on the host.

Pagefind indexing scope:
  By default Pagefind indexes the whole <body> of every HTML page. Once ANY
  page contains a `data-pagefind-body` element, Pagefind ONLY indexes pages
  that have that marker (and only the marked region on those pages). The main
  agent adds `data-pagefind-body` to report.html's content wrapper, so after
  that change only the weekly reports are indexed. That is intentional.
"""
import os
import sys
import platform
import subprocess

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

WIN_BIN = os.path.join(REPO_ROOT, "vendor", "pagefind", "pagefind-win", "pagefind.exe")
LINUX_BIN = os.path.join(REPO_ROOT, "vendor", "pagefind", "pagefind-linux", "pagefind")


def pick_binary():
    system = platform.system()
    if system == "Windows":
        return WIN_BIN
    # Treat everything else (Linux CI on ubuntu-latest, etc.) as the linux binary.
    return LINUX_BIN


def main():
    binary = pick_binary()
    if not os.path.isfile(binary):
        print("ERROR: vendored pagefind binary not found: %s" % binary, file=sys.stderr)
        print("Expected one of:", file=sys.stderr)
        print("  %s" % WIN_BIN, file=sys.stderr)
        print("  %s" % LINUX_BIN, file=sys.stderr)
        return 1

    # Ensure the linux binary is executable (git may not preserve the bit on
    # every checkout; harmless on Windows).
    if not binary.endswith(".exe"):
        try:
            os.chmod(binary, 0o755)
        except OSError:
            pass

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
