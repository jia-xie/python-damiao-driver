#!/usr/bin/env bash
set -e

# Build docs for Cloudflare Pages (damiao-motor.jia-xie.com). Run from repo root.
# Requires: mkdocs, mkdocs-material, mkdocstrings[python], and the package (pip install -e .)

mkdocs build -f mkdocs.cloudflare.yml
