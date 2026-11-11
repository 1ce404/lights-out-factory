"""Shared helpers: config loading, fetching sources (Feishu via lark-cli, web URL or local file), table parsing, clause splitting."""
import html
import json
import re
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def load_config(path_or_key):
    """Brand file config/<brand>.json (sources, store mapping, shared rules) merged with one file per
    product under config/<brand>/<product_key>.json. Scripts see cfg["products"][key] as before."""
    p = Path(path_or_key)
    if not p.exists():
        p = SKILL_DIR / "config" / f"{path_or_key}.json"
    cfg = json.loads(p.read_text())
    cfg.setdefault("products", {})
    for f in sorted((p.parent / p.stem).glob("*.json")):
        cfg["products"][f.stem] = json.loads(f.read_text())
    return with_defaults(cfg, p.stem)


# Everything a config may leave out. A business only has to write what differs (config/minimal.json is the
# smallest working one: a brand name and a product name). Scripts can then read cfg["x"] without checks.
BRAND_DEFAULTS = {
    "brand_tag": None,             # → brand
    "sources": {},
    "schedule": {},                # columns / date_formats, see parse_schedule.py
    "daily_quota": None,
    "store_to_product": {},
    "brief_prefix": "B",
    "brief_size": 10,
    "generate_factor": 2,
    "generate_chunk": 15,
    "writing": {},
    "banned_words": {"error": [], "warn": [], "regex_error": [], "regex_warn": [], "scene_warn": [], "allow_exceptions": []},
    "copy_limits": {"clause_hard_max": 20, "clause_warn_max": 12, "clause_warn_min": 1, "combo_chars_min": 60,
                    "combo_chars_max": 200, "chars_per_second": 5.5, "history_days": 7, "name_not_before": 0,
                    "opening_similar_max": 0.5},
    "campaign": None,
    "clipo": {"base_url": "https://clipo-remix.tezign.com"},
    "watermark": {"add": True, "position": "bottom_right", "mode": "global"},
    "tts": {},
    "banned_footage_words": [],
    "naming": "{date}-{brief_no}-V{n:02d}-{product}-{selling_point}",
    "delivery_naming": None,       # None → same as naming without -V
    "delivery_group_naming": "{date}-{brand_tag}",
    "direction_tags": {},
    "direction_notes": {},
    "review": {},
    "open_questions": [],
}
PRODUCT_DEFAULTS = {
    "name_aliases": None,          # → [full_name]
    "short_name": None,            # → full_name
    "collection_labels": None,     # → [full_name]
    "clipo_product_id": None,
    "default_selling_point": "",
    "selling_points": {},
    "mechanism": {"spoken": [], "allowed_numbers": []},
    "cta_required": [],            # empty = no required ending word
    "banned_words": [], "warn_words": [], "allow_words": [], "foreign_claims": [], "keep_terms": [],
    "speaker_warn": [], "rules": [], "footage": {}, "footage_tags": [],
    "ingredient_terms": [], "ingredient_footage": [],
}


def with_defaults(cfg, key):
    for k, v in BRAND_DEFAULTS.items():
        if isinstance(v, dict) and isinstance(cfg.get(k), dict):
            cfg[k] = {**v, **cfg[k]}
        else:
            cfg.setdefault(k, json.loads(json.dumps(v)))
    cfg.setdefault("brand_key", key)
    cfg.setdefault("brand", cfg["brand_key"])
    cfg["brand_tag"] = cfg["brand_tag"] or cfg["brand"]
    for pk, prod in cfg["products"].items():
        prod.setdefault("full_name", pk)
        for k, v in PRODUCT_DEFAULTS.items():
            if isinstance(v, dict) and isinstance(prod.get(k), dict):
                prod[k] = {**v, **prod[k]}
            else:
                prod.setdefault(k, json.loads(json.dumps(v)))
        prod["name_aliases"] = prod["name_aliases"] or [prod["full_name"]]
        prod["short_name"] = prod["short_name"] or prod["full_name"]
        prod["collection_labels"] = prod["collection_labels"] or [prod["full_name"]]
    if not cfg["store_to_product"]:  # schedule rows name the product: match on product names
        cfg["store_to_product"] = {n: pk for pk, prod in cfg["products"].items()
                                   for n in [pk, prod["full_name"], prod["short_name"]] + prod["name_aliases"]}
    return cfg


def fetch_doc(src):
    """Text of one source: a Feishu/Lark wiki or docx link (needs lark-cli), any other http(s) URL, or a local
    file path (relative to the current directory, else to the skill folder). Add your own kind here (Notion, Google Docs…)."""
    if re.match(r"https?://[^/]*(feishu|larksuite)\.", src):
        return lark_fetch(src)
    if re.match(r"https?://", src):
        import urllib.request
        with urllib.request.urlopen(src, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    p = Path(src).expanduser()
    if not p.is_absolute() and not p.exists() and (SKILL_DIR / p).exists():
        p = SKILL_DIR / p  # files kept inside the skill (sources/…, examples/…)
    return read_file(p)


def read_file(path):
    """A local file as text the other scripts read: .xlsx / .csv / .tsv become one markdown pipe table per sheet
    (under a ### sheet-name heading); anything else (.md / .txt / .json / .html) is read as is."""
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        return "\n\n".join(f"### {name}\n\n" + to_markdown(rows) for name, rows in xlsx_sheets(path) if rows)
    if suffix in (".csv", ".tsv"):
        import csv
        raw = path.read_bytes()
        text = next(raw.decode(e) for e in ("utf-8-sig", "gb18030", "latin-1") if _decodes(raw, e))
        return to_markdown(list(csv.reader(text.splitlines(), delimiter="\t" if suffix == ".tsv" else ",")))
    return path.read_text()


def _decodes(raw, enc):
    try:
        raw.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def to_markdown(rows):
    rows = [[str(c).replace("|", "／").replace("\n", "<br/>").strip() for c in r] for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        return ""
    w = max(len(r) for r in rows)
    rows = [r + [""] * (w - len(r)) for r in rows]
    return "\n".join(["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w] + ["| " + " | ".join(r) + " |" for r in rows[1:]])


def xlsx_sheets(path):
    """[(sheet name, rows)] from an .xlsx with the standard library only (no openpyxl). Merged cells are
    filled with their top-left value; dates stay Excel serial numbers (parse_schedule reads them)."""
    import zipfile
    import xml.etree.ElementTree as ET
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    z = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    col = lambda ref: sum((ord(ch) - 64) * 26 ** i for i, ch in enumerate(reversed(re.match(r"[A-Z]+", ref)[0]))) - 1
    out = []
    for sh in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", ns):
        target = rels[sh.get(f"{{{ns['r']}}}id")].lstrip("/")
        root = ET.fromstring(z.read(target if target.startswith("xl/") else "xl/" + target))
        cells = {}
        for row in root.iter(f"{{{ns['m']}}}row"):
            for c in row.findall("m:c", ns):
                v = c.find("m:v", ns)
                t = c.get("t")
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(f"{{{ns['m']}}}t"))
                elif v is None:
                    continue
                elif t == "s":
                    val = shared[int(v.text)]
                else:
                    val = v.text or ""
                    if re.fullmatch(r"-?\d+\.0+", val):
                        val = val.split(".")[0]
                cells[(int(row.get("r")) - 1, col(c.get("r")))] = val
        for m in root.iter(f"{{{ns['m']}}}mergeCell"):
            a, b = m.get("ref").split(":")
            (r0, c0), (r1, c1) = [(int(re.search(r"\d+", x)[0]) - 1, col(x)) for x in (a, b)]
            for r in range(r0, r1 + 1):
                for cc in range(c0, c1 + 1):
                    cells.setdefault((r, cc), cells.get((r0, c0), ""))
        if not cells:
            out.append((sh.get("name"), []))
            continue
        nr, nc = max(r for r, _ in cells) + 1, max(c for _, c in cells) + 1
        out.append((sh.get("name"), [[cells.get((r, c), "") for c in range(nc)] for r in range(nr)]))
    return out


def lark_fetch(doc_url):
    """Return the document body (Lark XML-ish markdown) of a wiki/docx URL."""
    out = subprocess.run(
        ["lark-cli", "docs", "+fetch", "--doc", doc_url, "--doc-format", "markdown"],
        capture_output=True, text=True, timeout=180,
    )
    if out.returncode != 0:
        raise RuntimeError(f"lark-cli fetch failed for {doc_url}: {out.stderr[-800:]}")
    data = json.loads(out.stdout)
    if not data.get("ok"):
        raise RuntimeError(f"lark-cli fetch error for {doc_url}: {json.dumps(data, ensure_ascii=False)[:800]}")
    return data["data"]["document"]["content"]


def cell_text(raw):
    """Lark cell HTML → plain text, keeping <br/> as newlines."""
    t = re.sub(r"<br\s*/?>", "\n", raw)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).strip()


def parse_table(table_html):
    """Expand a Lark <table> (with rowspan/colspan) into a rectangular grid of plain-text cells."""
    rows = re.findall(r"<tr>(.*?)</tr>", table_html, re.S)
    grid, carry = [], {}  # carry[col] = [remaining_rows, text]
    for row in rows:
        cells = re.findall(r"<t([dh])([^>]*)>(.*?)</t[dh]>", row, re.S)
        out, col = [], 0
        pending = list(cells)
        while pending or col in carry:
            if col in carry:
                left, text = carry[col]
                out.append(text)
                if left <= 1:
                    del carry[col]
                else:
                    carry[col] = [left - 1, text]
                col += 1
                continue
            _, attrs, raw = pending.pop(0)
            text = cell_text(raw)
            rs = int((re.search(r'rowspan="(\d+)"', attrs) or [0, 1])[1])
            cs = int((re.search(r'colspan="(\d+)"', attrs) or [0, 1])[1])
            for _ in range(cs):
                out.append(text)
                if rs > 1:
                    carry[col] = [rs - 1, text]
                col += 1
        grid.append(out)
    return grid


def split_clauses(text):
    """Split copy into short clauses on reading punctuation; decimal points (89.9) don't split."""
    text = re.sub(r"\[#[^\]]*\]", "", text)
    parts = re.split(r"[，。！？；：、…!?;:,]|(?<!\d)\.|\.(?!\d)", text)
    return [p.strip(" 　“”\"'（）()【】") for p in parts if p.strip(" 　“”\"'（）()【】")]


def visible_len(s):
    return len(re.sub(r"\s", "", s))


def display_len(s):
    """Subtitle width: a CJK character is 1, a half-width letter or digit is 0.5 (HONOR X7e = 4)."""
    s = re.sub(r"\s", "", s)
    return sum(0.5 if ord(ch) < 128 else 1 for ch in s)


def normalize_copy(text):
    """For exact-match comparison: drop voice instructions, punctuation and whitespace."""
    t = re.sub(r"\[#[^\]]*\]", "", text)
    t = re.sub(r"[\s，。！？；：、…,.!?;:“”\"'（）()【】~～]", "", t)
    return t.lower()


def seg_alts(seg):
    """Other ways to say this line (team scripts give 2~3 per line). Stored as a list; a string is one alternative."""
    a = seg.get("alt") or []
    return [a] if isinstance(a, str) else [x for x in a if x]


def copy_hash(brief):
    """Fingerprint of the copy a reviewer saw. Approval is only valid while this still matches."""
    import hashlib
    body = "\n".join(f"{x.get('id')}|{x.get('role')}|{x.get('text', '')}" + "".join(f"|{a}" for a in seg_alts(x))
                     for x in brief.get("segments") or [])
    return hashlib.sha1(body.encode()).hexdigest()[:12]


def approval_problem(brief):
    """Why this brief may not go to Clipo, or None. Only a recorded human review counts as approved."""
    if brief.get("status") != "approved":
        return f"status={brief.get('status')}（未审核通过）"
    a = brief.get("approval") or {}
    if not a.get("by"):
        return "没有审核记录：status 是手改的，要走 review_doc.py sync 或 approve"
    if a.get("copy_hash") != copy_hash(brief):
        return f"{a['by']} 审过之后文案又改了，要重新给人看"
    return None


def load_gold(cfg, product_key=None):
    """Gold scripts for the brand; with product_key, only that product's (each script carries `product`)."""
    p = SKILL_DIR / "gold" / f"{cfg['brand_key']}.json"
    scripts = json.loads(p.read_text())["scripts"] if p.exists() else []
    return [g for g in scripts if not product_key or g.get("product") == product_key]


def day_briefs(run, cfg):
    """All briefs of this brand in a day folder (several brands share runs/<day>/briefs/)."""
    out = []
    for p in sorted((Path(run) / "briefs").glob("*.json")):
        b = json.loads(p.read_text())
        if b.get("brand", cfg["brand_key"]) == cfg["brand_key"]:
            out.append(b)
    return out


def out_name(cfg, name):
    """Per-brand file name inside a day folder (several brands can share one runs/<day>/): lint-<brand>.json."""
    stem, dot, ext = name.partition(".")
    return f"{stem}-{cfg['brand_key']}{dot}{ext}"


WRITING_DEFAULTS = {
    # What the opening talks about: the viewer's problem, in the words of this category (头发 / 皮肤 / 厨房油污…)
    "subject": "使用者的问题",
    # Opening types to rotate between briefs of the same product on one day (writing.md §3)
    "opening_types": ["反问", "判断", "金句", "场景引子", "对话", "热梗", "直戳问题状态"],
    # The first line may not open with price / deal / pack / ingredient list
    "opening_banned_regex": r"拍[一二三四五六七八九十\d]+发|到手|\d+(?:\.\d+)?\s*元|套组|瓶背|背面|成分表|配方表",
    # Directions allowed to open with the deal (they copy viral videos that do); bottle back / ingredient list still out
    "opening_deal_ok_directions": ["爆款复刻"],
    "opening_never": ["瓶背", "背面", "成分表", "配方表"],
    # After the product is named, the copy must not say the problem comes back (reads as "it doesn't work")
    "after_use_bad_regex": r"(下班|下午|晚上|回家|一天下来|过了一会|没多久|又)[^。！？]{0,8}(干|油|乱|塌|脏|痛|痒|坏)",
    # Two or more of these in one script = a timeline, which reads as "it got bad again later"
    "timeline_regex": r"早上|下午|下班|出门前|晚上",
    # Pointing at the product instead of naming it
    "product_pronoun_regex": r"(这|那)(瓶|款|支|个产品)",
    # Rules written into every script's AI-rewrite prompt (vo_rewrite_prompt)
    "rewrite_rules": [
        "不要加任何 [#…] 语音指令，每段都直接写正文，整条用同一种自然的语气",
        "段落顺序和每段的意思不变：先讲问题，再讲产品；产品出现以后只讲用完的好结果，不写用了以后问题又回来",
        "不加早上、下午、下班、出门前这类时间线，不编使用场景和前后对比",
    ],
}


def writing(cfg, key):
    """A writing rule from config `writing` (see config/example.json), falling back to WRITING_DEFAULTS."""
    return (cfg.get("writing") or {}).get(key, WRITING_DEFAULTS[key])
