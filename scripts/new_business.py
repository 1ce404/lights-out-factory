#!/usr/bin/env python3
"""Create a new business's own skill from this template: a full copy with the business's name, an empty
config, its source files copied in, and no example data. The agent then fills it from what the business
handed over (references/onboarding.md).

    python3 scripts/new_business.py --key dove --brand 多芬 --agent claude \
        [--products bodywash=多芬沐浴露 shampoo=多芬洗发水] [--sources <file or folder> ...]

--agent installs it where that agent looks for skills, so the user can use it right away:
    claude → ~/.claude/skills/<key>-daily-batch/      codex → ~/.codex/skills/<key>-daily-batch/
With two agents (--agent claude codex) the skill lives in the first folder and the second gets a link to it,
so there is one copy to keep up to date. --out <folder> builds somewhere else instead (not installed).

Writes the skill folder with SKILL.md (name/description to rewrite), config/<key>.json, config/<key>/<product>.json,
gold/<key>.json (empty), sources/ (copies of the files given), and everything in scripts/ and references/.
Refuses to write into a folder that already has files.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent
KEEP = ["scripts", "references", ".gitignore"]
AGENTS = {"claude": ".claude/skills", "codex": ".codex/skills"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True, help="English key for the business, e.g. dove (file names, brief ownership)")
    ap.add_argument("--brand", required=True, help="brand name as written in copy, e.g. 多芬")
    ap.add_argument("--agent", nargs="+", choices=sorted(AGENTS), help="install into this agent's skills folder (the agent you are)")
    ap.add_argument("--out", help="build in this folder instead of installing")
    ap.add_argument("--products", nargs="*", default=[], help="key=产品全名 for each product")
    ap.add_argument("--sources", nargs="*", default=[], help="files or folders the business handed over")
    args = ap.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", args.key):
        raise SystemExit("--key 只用小写字母、数字、下划线，字母开头")
    if not args.agent and not args.out:
        raise SystemExit("要么 --agent claude / codex（装到 agent 里，推荐），要么 --out <目录>")
    name = f"{args.key}-daily-batch"
    homes = [Path.home() / AGENTS[a] / name for a in args.agent or []]
    out = Path(args.out).expanduser().resolve() if args.out else homes[0]
    links = [h for h in homes if h != out]
    for d in [out] + links:
        if d.exists() or d.is_symlink():
            if d == out and d.is_dir() and not d.is_symlink() and not any(d.iterdir()):
                continue
            raise SystemExit(f"{d} 已经有了：这个业务可能建过（换个 --key，或先看看里面是什么，不覆盖）")
    out.mkdir(parents=True, exist_ok=True)

    for name in KEEP:
        src = TEMPLATE / name
        if src.is_dir():
            shutil.copytree(src, out / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif src.exists():
            shutil.copy2(src, out / name)
    # this script and the template's onboarding belong to the template, not to a business skill
    (out / "scripts" / "new_business.py").unlink(missing_ok=True)
    (out / "references" / "onboarding.md").unlink(missing_ok=True)

    sources = {}
    if args.sources:
        sdir = out / "sources"
        sdir.mkdir()
        for s in args.sources:
            p = Path(s).expanduser()
            for f in ([p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file())):
                dest = sdir / f.name
                shutil.copy2(f, dest)
                sources.setdefault(f"_file_{len(sources) + 1}", f"sources/{f.name}")

    cfg = {
        "_readme": "本业务配置。只写和默认不一样的；每项的默认值和说明见 scripts/common.py 的 BRAND_DEFAULTS 和 references/adapt.md",
        "brand": args.brand,
        "brand_key": args.key,
        "sources": {"schedule": None, "qc": None, "recent_scripts": None, **sources,
                    "_note": "把 schedule / qc / recent_scripts 指到对应文件或链接（skill 里 sources/ 下的文件写 sources/<文件名> 就行；每天会更新的写飞书或网页链接）；_file_ 开头的是业务给的原始文件，认完归位后删掉"},
        "brief_size": 10,
        "writing": {"subject": "使用者的问题"},
        "banned_words": {"error": [], "warn": []},
        "open_questions": [],
    }
    (out / "config").mkdir()
    (out / "config" / f"{args.key}.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    pdir = out / "config" / args.key
    pdir.mkdir()
    for spec in args.products:
        k, _, name = spec.partition("=")
        prod = {"_note": "依据：哪份资料、哪天核对", "full_name": name or k, "clipo_product_id": None,
                "selling_points": {}, "mechanism": {"spoken": [], "allowed_numbers": [], "source": "", "verified_on": None},
                "cta_required": [], "rules": []}
        (pdir / f"{k}.json").write_text(json.dumps(prod, ensure_ascii=False, indent=2) + "\n")
    (out / "gold").mkdir()
    (out / "gold" / f"{args.key}.json").write_text(json.dumps(
        {"_readme": "团队交付过、客户认可的稿，每条写 product、direction、beats（role + text）", "scripts": []},
        ensure_ascii=False, indent=2) + "\n")

    skill = (TEMPLATE / "SKILL.md").read_text()
    skill = re.sub(r"^name: .*$", f"name: {args.key}-daily-batch", skill, count=1, flags=re.M)
    skill = re.sub(r"^description: .*$", f"description: {args.brand}短视频混剪每日批量生产（待改写：写清这个业务做什么、"
                   f"用户说什么话时用它，如「跑{args.brand}今天的排期」「{args.brand}今天的脚本」）", skill, count=1, flags=re.M)
    skill = re.sub(r"\n# 黑灯工厂：每日批量混剪\n\n\*\*这是模板.*?\n(?=排期上每一行)", f"\n# {args.brand}：每日批量混剪\n\n"
                   f"从黑灯工厂模板建的业务 skill。`$C` = `{args.key}`。\n\n", skill, count=1, flags=re.S)
    skill = "\n".join(l for l in skill.splitlines() if "onboarding.md" not in l) + "\n"
    skill = skill.replace("（`config/<C>.json`，示例是 `example`）", f"（这个业务是 `{args.key}`）")
    (out / "SKILL.md").write_text(skill)
    (out / "README.md").write_text(f"# {args.key}-daily-batch\n\n{args.brand}短视频混剪每日批量生产的 Agent skill，"
                                   "从 [lights-out-factory](https://github.com/1ce404/lights-out-factory) 模板建立。入口是 `SKILL.md`。\n")
    print(f"建好了 {out}")
    print(f"  config/{args.key}.json、config/{args.key}/（{len(args.products)} 个产品）、gold/{args.key}.json、"
          f"sources/（{len(sources)} 个文件）、scripts/、references/")
    for l in links:
        l.parent.mkdir(parents=True, exist_ok=True)
        l.symlink_to(out, target_is_directory=True)
        print(f"  {l} → 链接到上面这份（只有一份，改哪边都一样）")
    if args.agent:
        print(f"已装进 {'、'.join(args.agent)}：新开一个对话，说「跑{args.brand}今天的排期」就会用它")
    else:
        print(f"没有装进 agent：要用就把 {out} 放到 ~/.claude/skills/ 或 ~/.codex/skills/ 下")
    print("下一步：照模板的 references/onboarding.md 第 3 步把资料填进新 skill 的 config，改 SKILL.md 的 description 和流程")


if __name__ == "__main__":
    main()
