#!/usr/bin/env python3
"""Discover recent NRW news candidates without storing credentials.

The script is a discovery aid, not the editor: it gathers recent links and
metadata. A curator must still verify, rank and summarize candidates before
publishing data/news.json.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import email.utils
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "NRW-Lagebild/1.0 (+https://github.com/ai-agent36/nrw-dashboard)"
QUERIES = [
    ("land", "NRW Landespolitik"),
    ("land", "Nordrhein-Westfalen Schule Bildung"),
    ("land", "NRW Verkehr Bahn Autobahn"),
    ("land", "NRW Klima Umwelt Rhein"),
    ("land", "NRW Wirtschaft Industrie Arbeitsplätze"),
    ("local", "Köln Kommunalpolitik Verkehr Wohnen"),
    ("local", "Düsseldorf Niederrhein Nachrichten Politik"),
    ("local", "Ruhrgebiet Kommunen Wirtschaft Verkehr"),
    ("local", "Münsterland Politik Nachrichten"),
    ("local", "Ostwestfalen-Lippe Politik Nachrichten"),
    ("local", "Aachen Eifel Politik Nachrichten"),
    ("local", "Südwestfalen Politik Nachrichten"),
    ("niche", "Nordrhein-Westfalen ungewöhnlich Forschung Natur Kultur"),
    ("federal", "Bundespolitik Auswirkungen Nordrhein-Westfalen"),
]
REGION_HINTS = {
    "köln": "Köln/Bonn", "bonn": "Köln/Bonn",
    "düsseldorf": "Düsseldorf/Niederrhein", "niederrhein": "Düsseldorf/Niederrhein",
    "duisburg": "Ruhrgebiet", "essen": "Ruhrgebiet", "bochum": "Ruhrgebiet",
    "dortmund": "Ruhrgebiet", "gelsenkirchen": "Ruhrgebiet", "ruhr": "Ruhrgebiet",
    "münster": "Münsterland", "bielefeld": "Ostwestfalen-Lippe", "owl": "Ostwestfalen-Lippe",
    "aachen": "Aachen/Eifel", "eifel": "Aachen/Eifel",
    "siegen": "Südwestfalen", "sauerland": "Südwestfalen", "südwestfalen": "Südwestfalen",
}


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return
        values = {str(k).lower(): (v or "") for k, v in attrs}
        key = values.get("property") or values.get("name")
        value = values.get("content")
        if key and value:
            self.meta[key.lower()] = html.unescape(value.strip())


def request_bytes(url: str, timeout: int = 20, max_bytes: int = 1_500_000) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read(max_bytes)


def direct_url(bing_url: str) -> str:
    parsed = urllib.parse.urlparse(bing_url)
    candidate = urllib.parse.parse_qs(parsed.query).get("url", [bing_url])[0]
    return urllib.parse.unquote(candidate)


def infer_region(text: str) -> str:
    lowered = text.casefold()
    for needle, region in REGION_HINTS.items():
        if needle in lowered:
            return region
    return "NRW"


def parse_date(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        return parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def fetch_query(kind: str, query: str, cutoff: dt.datetime) -> list[dict]:
    endpoint = "https://www.bing.com/news/search?" + urllib.parse.urlencode({"q": query, "format": "rss", "setlang": "de-de"})
    root = ET.fromstring(request_bytes(endpoint))
    namespace = {"news": "https://www.bing.com/news/search?q=" + urllib.parse.quote_plus(query) + "&format=rss"}
    items: list[dict] = []
    for node in root.findall(".//item")[:12]:
        published = parse_date(node.findtext("pubDate"))
        if not published or published < cutoff:
            continue
        title = html.unescape((node.findtext("title") or "").strip())
        description = re.sub(r"<[^>]+>", " ", html.unescape(node.findtext("description") or ""))
        description = re.sub(r"\s+", " ", description).strip()
        source = ""
        image = ""
        for child in list(node):
            local = child.tag.split("}")[-1].lower()
            if local == "source": source = (child.text or "").strip()
            if local == "image": image = (child.text or "").strip()
        url = direct_url(node.findtext("link") or "")
        if not url.startswith(("http://", "https://")):
            continue
        items.append({
            "title": title,
            "description": description,
            "publishedAt": published.isoformat().replace("+00:00", "Z"),
            "source": source or urllib.parse.urlparse(url).netloc.removeprefix("www."),
            "url": url,
            "image": image,
            "kind": kind,
            "region": infer_region(f"{title} {description} {query}"),
            "discoveredBy": query,
        })
    return items


def enrich(candidate: dict) -> dict:
    try:
        raw = request_bytes(candidate["url"], timeout=12, max_bytes=900_000)
        text = raw.decode("utf-8", errors="replace")
        parser = MetaParser()
        parser.feed(text)
        meta = parser.meta
        image = meta.get("og:image") or meta.get("twitter:image") or candidate.get("image", "")
        description = meta.get("og:description") or meta.get("description") or candidate.get("description", "")
        candidate["image"] = image
        candidate["description"] = re.sub(r"\s+", " ", description).strip()[:700]
        candidate["publisher"] = meta.get("og:site_name") or candidate.get("source", "")
        candidate["metadataVerified"] = True
    except Exception as exc:  # individual publishers often block automated metadata reads
        candidate["metadataVerified"] = False
        candidate["metadataError"] = type(exc).__name__
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=10)
    parser.add_argument("--output", default=str(ROOT / "data" / "candidates.json"))
    parser.add_argument("--no-enrich", action="store_true")
    args = parser.parse_args()

    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)
    candidates: list[dict] = []
    errors: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {pool.submit(fetch_query, kind, query, cutoff): query for kind, query in QUERIES}
        for future in concurrent.futures.as_completed(jobs):
            query = jobs[future]
            try:
                candidates.extend(future.result())
            except Exception as exc:
                errors.append({"query": query, "error": f"{type(exc).__name__}: {exc}"})

    unique: dict[str, dict] = {}
    for item in sorted(candidates, key=lambda x: x["publishedAt"], reverse=True):
        normalized = urllib.parse.urlsplit(item["url"])._replace(query="", fragment="").geturl().rstrip("/")
        unique.setdefault(normalized, item)
    candidates = list(unique.values())

    if not args.no_enrich:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            candidates = list(pool.map(enrich, candidates))

    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "count": len(candidates),
        "errors": errors,
        "candidates": candidates,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "count": len(candidates), "errors": len(errors)}, ensure_ascii=False))
    return 0 if candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
