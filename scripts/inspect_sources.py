#!/usr/bin/env python3
"""Show what is in the files a business dropped in, so the agent can tell which is the schedule, which the
product facts, which the QC rules, which past scripts — and how to map them into a config.

    python3 scripts/inspect_sources.py <file or folder> [...]

For every file (.xlsx / .csv / .tsv / .md / .txt / .json / .html, or a Feishu / http link): its tables, each
table's header row and a few sample rows, how each column would be read as a schedule (date / product /
direction / selling point / audience / quantity, or kept as an extra column), the dates found, and the
first lines of any plain text. Read-only; writes nothing.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import fetch_doc, parse_table
from parse_schedule import FIELD_WORDS, header_row, parse_date, sections

TEXT = {".xlsx", ".csv", ".tsv", ".md", ".markdown", ".txt", ".json", ".html", ".htm"}
NO_CFG = {"schedule": {}, "brief_size": 10}


def field_of(h):
    h = re.sub(r"\s", "", h)
    return next((f for f, words in FIELD_WORDS if any(w in h for w in words)), None)


def show(label, text):
    print(f"\n==================== {label}  （{len(text)} 字）")
    n = 0
    for heading, notes, table in sections(text):
        grid = parse_table(table)
        if not grid:
            continue
        n += 1
        h = header_row(grid, NO_CFG)
        head = grid[h] if h is not None else grid[0]
        body = grid[(h if h is not None else 0) + 1:]
        print(f"\n-- 表 {n}「{heading}」 {len(body)} 行 × {len(head)} 列" + ("" if h is not None else "（没认出表头，按第一行算）"))
        if h:
            print(f"   表头在第 {h + 1} 行，上面是：{' / '.join(c for r in grid[:h] for c in r if c)[:80]}")
        cols = []
        for i, c in enumerate(head):
            f = field_of(c)
            sample = next((r[i] for r in body if i < len(r) and r[i].strip()), "")
            cols.append(f"{c or '(空)'}→{f or '其它'}「{sample[:16]}」")
        print("   列：" + "  ".join(cols))
        dcol = next((i for i, c in enumerate(head) if field_of(c) == "date"), None)
        if dcol is not None:
            days = sorted({d for r in body if dcol < len(r) for d in parse_date(r[dcol], 2026)})
            if days:
                print(f"   日期：{days[0]} ~ {days[-1]}，共 {len(days)} 天")
        for r in body[:3]:
            print("   · " + " | ".join(x[:24] for x in r))
        if notes:
            print(f"   表外文字：{notes[:200]}")
    if not n:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        print(f"（没有表格，{len(lines)} 行文字）")
        for l in lines[:12]:
            print("   " + l[:120])


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for arg in sys.argv[1:]:
        p = Path(arg).expanduser()
        if p.is_dir():
            files = sorted(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in TEXT)
            skipped = sorted(f.name for f in p.rglob("*") if f.is_file() and f.suffix.lower() not in TEXT)
            if skipped:
                print(f"（读不了，要转成 xlsx / csv / md 或贴文字：{'、'.join(skipped[:10])}）")
        else:
            files = [arg]
        for f in files:
            try:
                show(str(f), fetch_doc(str(f)))
            except Exception as e:
                print(f"\n==================== {f}\n读不了：{e}")


if __name__ == "__main__":
    main()
