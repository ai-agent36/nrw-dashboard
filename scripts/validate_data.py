#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, sys, urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TOP = {"meta", "lead", "signals", "ticker", "focusTopics", "stories", "newsletter"}
REQUIRED_STORY = {"id", "kind", "title", "summary", "whyItMatters", "category", "region", "publishedAt", "source", "sourceUrl"}
KINDS = {"land", "local", "niche", "federal"}

def valid_url(value: str) -> bool:
    try: return urlparse(value).scheme in {"http", "https"} and bool(urlparse(value).netloc)
    except Exception: return False

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("path", nargs="?", default=str(ROOT / "data/news.json")); p.add_argument("--check-links", action="store_true"); args = p.parse_args()
    errors=[]; warnings=[]
    try: data=json.loads(Path(args.path).read_text(encoding="utf-8"))
    except Exception as exc: print(f"ERROR: invalid JSON: {exc}"); return 1
    missing=REQUIRED_TOP-set(data); errors += [f"missing top-level key: {x}" for x in sorted(missing)]
    ids=[]; urls=[]
    items=[data.get("lead",{})]+data.get("stories",[])
    for index,item in enumerate(items):
        label=f"item[{index}]/{item.get('id','?')}"
        absent=REQUIRED_STORY-set(item)
        if index==0: absent-={"kind"}
        errors += [f"{label}: missing {x}" for x in sorted(absent)]
        if item.get("id"): ids.append(item["id"])
        if index and item.get("kind") not in KINDS: errors.append(f"{label}: invalid kind {item.get('kind')}")
        for key in ("sourceUrl","image"):
            if item.get(key):
                if not valid_url(item[key]): errors.append(f"{label}: invalid {key}")
                else: urls.append((label,key,item[key]))
        if len(item.get("summary",""))<40: warnings.append(f"{label}: unusually short summary")
    duplicates=sorted({x for x in ids if ids.count(x)>1}); errors += [f"duplicate id: {x}" for x in duplicates]
    if len(data.get("stories",[]))<8: warnings.append("fewer than 8 stories")
    source_count=len({url for _,key,url in urls if key=="sourceUrl"} | {data.get("newsletter",{}).get("sourceUrl","")})
    declared=data.get("meta",{}).get("sourceCount")
    if declared != source_count: warnings.append(f"sourceCount={declared}, calculated={source_count}")
    if args.check_links:
        for label,key,url in urls:
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"},method="HEAD")
                with urllib.request.urlopen(req,timeout=12) as r:
                    if r.status>=400: errors.append(f"{label}: {key} HTTP {r.status}")
            except Exception as exc: warnings.append(f"{label}: {key} check failed ({type(exc).__name__})")
    for message in warnings: print("WARN:",message)
    for message in errors: print("ERROR:",message)
    print(json.dumps({"stories":len(data.get('stories',[])),"ids":len(ids),"errors":len(errors),"warnings":len(warnings)},ensure_ascii=False))
    return 1 if errors else 0
if __name__ == "__main__": raise SystemExit(main())
