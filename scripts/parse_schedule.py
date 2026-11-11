#!/usr/bin/env python3
"""Turn one day of the schedule doc into brief stubs (one brief per `brief_size` videos).

    python3 scripts/parse_schedule.py --config example --run runs/20261030 --date 2026-10-30

Reads  runs/<day>/sources/schedule.txt, or config.daily_quota for brands without a schedule doc
Writes runs/<day>/schedule-<brand>.json every row for that date (incl. 新增 tables) + section notes
       runs/<day>/briefs/<id>.json      one stub per brief; the agent fills segments (brief_card.py shows what to write)
"""
import argparse
import json
import math
import re
from datetime import date
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_config, parse_table

# Which field a column is, by words in its header (first match wins). config schedule.columns maps exact
# headers when a table uses words not listed here. Any other column is kept as-is and shown on the brief card.
FIELD_WORDS = [
    ("date", ["日期", "时间", "投放日", "上线日", "发布日", "date"]),
    ("quantity", ["总交付", "数量", "条数", "产量", "需求量", "个数", "qty", "quantity"]),
    ("store", ["店铺", "产品", "商品", "sku", "SKU", "品名", "品项", "账号"]),
    ("selling_point", ["卖点", "利益点", "功效"]),
    ("audience", ["人群", "受众", "对象", "TA"]),
    ("direction", ["方向", "类型", "主题", "题材", "形式", "脚本类型"]),
]


def field_of(header, cfg):
    h = re.sub(r"\s", "", header)
    exact = (cfg.get("schedule") or {}).get("columns") or {}
    if h in exact:
        return exact[h]
    for field, words in FIELD_WORDS:
        if any(w in h for w in words):
            return field
    return None


def parse_date(cell, year):
    """A schedule date cell → date, or None. Reads 11.20 / 11/20 / 11-20 / 11月20日 / 2026-11-20 / 2026/11/20 /
    20261120 / Excel serial (46345). Ranges like 11.20-11.22 count for every day in them."""
    t = re.sub(r"\s", "", str(cell or ""))
    if not t:
        return []
    if re.fullmatch(r"\d{5}(\.0+)?", t):  # Excel serial day number
        from datetime import timedelta
        return [date(1899, 12, 30) + timedelta(days=int(float(t)))]
    found = []
    for y, m, d in re.findall(r"(?:(20\d\d)[年./-])?(\d{1,2})[月./-](\d{1,2})日?", t) + \
            [(a[:4], a[4:6], a[6:]) for a in re.findall(r"20\d{6}", t)]:
        try:
            found.append(date(int(y or year), int(m), int(d)))
        except ValueError:
            pass
    if len(found) == 2 and re.search(r"\d[-~～至到]\d", t) and found[0] < found[1]:
        from datetime import timedelta
        found = [found[0] + timedelta(days=i) for i in range((found[1] - found[0]).days + 1)]
    return found


def markdown_tables(body):
    """Pipe tables (| a | b |) → <table> html, so a schedule kept as plain markdown parses the same way."""
    out = []
    for block in re.findall(r"(?:^\|.*\|[ \t]*\n?)+", body, re.M):
        rows = [l.strip().strip("|").split("|") for l in block.strip().splitlines() if not re.match(r"^\|[\s:|-]+\|$", l.strip())]
        out.append("<table>" + "".join("<tr>" + "".join(f"<td>{c.strip()}</td>" for c in r) + "</tr>" for r in rows) + "</table>")
    return out


def sections(text):
    """Yield (heading, notes, table_html) for every #/##/### section that has tables (html or markdown pipe
    tables). A file with no headings counts as one section."""
    if not re.search(r"^#{1,3} ", text, re.M):
        text = "### 排期\n" + text
    parts = re.split(r"^#{1,3} (.*)$", text, flags=re.M)
    for i in range(1, len(parts), 2):
        heading, body = parts[i].strip(), parts[i + 1]
        tables = re.findall(r"<table>.*?</table>", body, re.S) + markdown_tables(body)
        notes = re.sub(r"<table>.*?</table>", "", body, flags=re.S)
        notes = " ".join(l.strip() for l in notes.splitlines() if l.strip() and not l.startswith(("<", "|")))
        for t in tables:
            yield heading, notes, t


def header_row(grid, cfg):
    """Index of the header row: the first of the top 5 rows whose cells name at least two known fields."""
    for i, r in enumerate(grid[:5]):
        if len({field_of(h, cfg) for h in r} - {None}) >= 2:
            return i
    return None


def rows_for(text, day, cfg, all_rows=False):
    """Rows of every table for `day` (or every row with all_rows / when no table has a date column).
    Known columns become fields; every other column goes to row["extra"] untouched."""
    found, dated = [], False
    for heading, notes, table in sections(text):
        grid = parse_table(table)
        h = header_row(grid, cfg) if grid else None
        if h is None:
            continue
        heads = [x.strip() for x in grid[h]]
        fields = [field_of(x, cfg) for x in heads]
        dated |= "date" in fields
        last = {}
        for r in grid[h + 1:]:
            if not any(c.strip() for c in r):
                continue
            row, extra = {}, {}
            for head, f, c in zip(heads, fields, r):
                if f and f not in row:
                    row[f] = c.strip()
                elif c.strip():
                    extra[head] = c.strip()
            if "date" in fields:  # a blank date cell continues the date above (merged-looking sheets)
                row["date"] = row.get("date") or last.get("date", "")
                last = row
                if not all_rows and day not in parse_date(row["date"], day.year):
                    continue
            qty = re.search(r"\d+(?:\+\d+)*", row.get("quantity", ""))
            row["quantity"] = sum(int(x) for x in qty[0].split("+")) if qty else cfg["brief_size"]
            row.update(extra=extra, section=heading, section_notes=notes)
            found.append(row)
    if not dated and found and not all_rows:
        print("（排期里没有日期列：表里每一行都当作今天的任务）")
    return found


def split_direction(direction, cfg):
    """「品牌背书，成分种草（某某溯源）」→ core + note. The bracket is a long-lived schedule label,
    not copy material; config.direction_notes says how the team actually wrote it."""
    m = re.match(r"(.*?)[（(](.*)[）)]\s*$", direction.strip())
    core, note = (m.group(1).strip(), m.group(2).strip()) if m else (direction.strip(), "")
    out = {"direction_core": core, "direction_note": note}
    hint = cfg.get("direction_notes", {}).get(note)
    if hint:
        out["direction_hint"] = hint
    return out


def product_key(cfg, store):
    for k, v in cfg["store_to_product"].items():
        if k in store:
            return v
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--product", help="only write briefs for this product key (numbering stays the same)")
    ap.add_argument("--all-rows", action="store_true", help="take every row of the schedule, not just this date")
    ap.add_argument("--tasks", help="a JSON list of rows the agent wrote itself (when the business has no table "
                                    "that fits): [{\"store\": \"产品\", \"direction\": \"…\", \"quantity\": 10, …}]")
    args = ap.parse_args()

    cfg = load_config(args.config)
    run = Path(args.run)
    day = date.fromisoformat(args.date)
    if args.tasks:
        known = {"store", "product_key", "direction", "selling_point", "audience", "quantity", "notes"}
        rows = [{"selling_point": "", "audience": "", "direction": "", "section": "tasks",
                 **{k: v for k, v in r.items() if k in known}, "section_notes": r.get("notes", ""),
                 "extra": {k: v for k, v in r.items() if k not in known}}
                for r in json.loads(Path(args.tasks).read_text())]
        for r in rows:
            r["quantity"] = int(r.get("quantity") or cfg["brief_size"])
    elif cfg.get("daily_quota"):
        # brands without a schedule doc: the same products and counts every day (config.daily_quota)
        rows = [{"store": q.get("store", cfg["brand"]), "product_key": q["product"], "direction": q.get("direction", "日常"),
                 "selling_point": "", "audience": q.get("audience", ""), "quantity": q["quantity"],
                 "section": "daily_quota", "section_notes": q.get("note", "")} for q in cfg["daily_quota"]]
    else:
        src = run / "sources" / "schedule.txt"
        if not src.exists():
            raise SystemExit(f"没有 {src}：先跑 fetch_sources.py（config sources.schedule），或用 --tasks 给任务清单")
        rows = rows_for(src.read_text(), day, cfg, args.all_rows)
    if not rows:
        raise SystemExit(f"排期里找不到 {day.month}.{day.day} 的行：排期可能还没更新到这一天；"
                         "表头认不出来就在 config schedule.columns 里写「表头: 字段」")

    run.mkdir(parents=True, exist_ok=True)
    (run / f"schedule-{cfg['brand_key']}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    bdir = run / "briefs"
    bdir.mkdir(exist_ok=True)
    size, n = cfg["brief_size"], 0
    for row in rows:
        pk = row.get("product_key") or product_key(cfg, row.get("store", "")) or product_key(cfg, row.get("direction", ""))
        for j in range(math.ceil(row["quantity"] / size)):
            n += 1
            bid = f"{day:%m%d}-{cfg.get('brief_prefix', 'B')}{n:02d}"
            path = bdir / f"{bid}.json"
            if path.exists() or (args.product and pk != args.product):
                continue  # never clobber a brief the agent or reviewer already worked on
            stub = {
                "brief_id": bid,
                "date": args.date,
                "brand": cfg["brand_key"],
                "store": row.get("store", "").replace("\n", " "),
                "product_key": pk,
                "direction": row.get("direction", ""),
                **split_direction(row.get("direction", ""), cfg),
                "selling_point": row.get("selling_point", "") or (cfg["products"].get(pk) or {}).get("default_selling_point", ""),
                "audience": row.get("audience", ""),
                "quantity": min(size, row["quantity"] - j * size),
                "schedule_section": row["section"],
                "schedule_notes": row["section_notes"],
                "schedule_extra": row.get("extra") or {},
                "segments": [],
                "status": "draft",
                "review_notes": "",
            }
            path.write_text(json.dumps(stub, ensure_ascii=False, indent=2))
        print(f"{row.get('store','')!r:28} {row.get('direction','')[:30]:32} {row.get('selling_point',''):14} "
              f"{row.get('audience',''):6} {row['quantity']:>3} -> product={pk} [{row['section']}]")
    print(f"\n{len(rows)} 行排期 → {n} 个 brief（每 {size} 条一个），stub 在 {bdir}")
    missing = [r for r in rows if not (r.get("product_key") or product_key(cfg, r.get('store', '')))]
    if missing:
        print("⚠️ 以下店铺没有映射到产品，需要在 config.store_to_product 补：", {r['store'] for r in missing})


if __name__ == "__main__":
    main()
