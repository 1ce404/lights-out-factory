#!/usr/bin/env python3
"""Pull today's sources into a run directory: every key under config `sources` that has a value.

    python3 scripts/fetch_sources.py --config example --run runs/20261030

A source is a Feishu link (lark-cli), any http(s) URL, or a local file path (see common.fetch_doc).
Writes sources/<key>.txt. Keys starting with history_ are only fetched with --history (they tend to be big).
"""
import argparse
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch_doc, load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--history", action="store_true", help="also fetch the historical script collection")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out = Path(args.run) / "sources"
    out.mkdir(parents=True, exist_ok=True)
    keys = [k for k, v in cfg["sources"].items() if not k.startswith("_") and isinstance(v, str)
            and (args.history or not k.startswith("history_"))]
    if "schedule" not in keys:
        print("schedule: 没有排期文档（用 config.daily_quota 固定条数）")
    for key in keys:
        if not cfg["sources"].get(key):
            print(f"{key}: 没配，跳过")
            continue
        text = fetch_doc(cfg["sources"][key])
        dest = out / f"{key}.txt"
        if dest.exists() and dest.read_text() != text and key != "schedule":
            dest = out / f"{key}-{cfg['brand_key']}.txt"  # two brands on the same day can point at different docs
        dest.write_text(text)
        print(f"{key}: {len(text)} chars -> {dest}")


if __name__ == "__main__":
    main()
