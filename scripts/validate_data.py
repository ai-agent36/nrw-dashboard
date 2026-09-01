#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TOP = {
    "meta",
    "lead",
    "signals",
    "ticker",
    "focusTopics",
    "stories",
    "newsletter",
    "polling",
    "governmentCriticism",
    "socialRadar",
}
REQUIRED_STORY = {
    "id",
    "kind",
    "title",
    "summary",
    "whyItMatters",
    "category",
    "region",
    "publishedAt",
    "source",
    "sourceUrl",
}
KINDS = {"land", "local", "niche", "federal"}
CONTENT_URL_KEYS = {
    "sourceUrl",
    "methodologyUrl",
    "imageSourceUrl",
    "imageLicenseUrl",
    "url",
}
CRITICISM_LEVELS = {"hoch", "beobachten"}
PROFILE_STATUSES = {"vollständig", "eingeschränkt"}
POST_PERFORMANCE = {"Grundrauschen", "am Median", "über Median", "stark", "Ausreißer"}


def canonical_url(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        if scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        host = parsed.hostname.encode("idna").decode("ascii").lower()
        if ":" in host:
            host = f"[{host}]"
        port = parsed.port
        if port is not None and not (
            (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        ):
            host = f"{host}:{port}"
        return urlunsplit((scheme, host, parsed.path or "/", parsed.query, parsed.fragment))
    except (UnicodeError, ValueError):
        return None


def valid_url(value: object) -> bool:
    return canonical_url(value) is not None


def valid_iso_datetime(value: object, *, allow_date: bool = False) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        if allow_date and len(value) == 10:
            dt.date.fromisoformat(value)
            return True
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.tzinfo is not None
    except (TypeError, ValueError):
        return False


def is_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def is_nonnegative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def collect_source_urls(value: object, key: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            found |= collect_source_urls(child, child_key)
    elif isinstance(value, list):
        for child in value:
            found |= collect_source_urls(child, key)
    elif isinstance(value, str) and key in CONTENT_URL_KEYS:
        normalized = canonical_url(value)
        if normalized:
            found.add(normalized)
    return found


def valid_local_asset(value: object) -> bool:
    if not isinstance(value, str) or not value or value.startswith(("/", ".")):
        return False
    if ".." in Path(value).parts:
        return False
    try:
        candidate = (ROOT / value).resolve()
        return candidate.is_relative_to(ROOT.resolve()) and candidate.is_file()
    except Exception:
        return False


def missing_fields(item: object, required: set[str], label: str, errors: list[str]) -> bool:
    if not isinstance(item, dict):
        errors.append(f"{label}: expected object")
        return True
    missing = required - set(item)
    errors.extend(f"{label}: missing {field}" for field in sorted(missing))
    return bool(missing)


def require_strings(item: dict, fields: set[str], label: str, errors: list[str]) -> None:
    for field in sorted(fields):
        if not isinstance(item.get(field), str) or not item[field].strip():
            errors.append(f"{label}: {field} must be a non-empty string")


def validate_url_field(
    item: dict,
    field: str,
    label: str,
    errors: list[str],
    urls: list[tuple[str, str, str]],
) -> None:
    if not valid_url(item.get(field)):
        errors.append(f"{label}: invalid {field}")
        return
    urls.append((label, field, item[field]))


def validate_datetime_field(
    item: dict,
    field: str,
    label: str,
    errors: list[str],
    *,
    allow_date: bool = False,
) -> None:
    if not valid_iso_datetime(item.get(field), allow_date=allow_date):
        errors.append(f"{label}: invalid {field}")


def validate(data: object) -> tuple[list[str], list[str], list[tuple[str, str, str]], int]:
    errors: list[str] = []
    warnings: list[str] = []
    urls: list[tuple[str, str, str]] = []
    story_ids: list[str] = []

    if not isinstance(data, dict):
        return ["root: expected object"], warnings, urls, 0

    errors.extend(
        f"missing top-level key: {field}" for field in sorted(REQUIRED_TOP - set(data))
    )

    meta = data.get("meta", {})
    missing_fields(
        meta,
        {"title", "generatedAt", "edition", "sourceCount", "editorialNote"},
        "meta",
        errors,
    )
    if isinstance(meta, dict):
        require_strings(meta, {"title", "edition", "editorialNote"}, "meta", errors)
        validate_datetime_field(meta, "generatedAt", "meta", errors)
        if not is_nonnegative_int(meta.get("sourceCount")):
            errors.append("meta: sourceCount must be a non-negative integer")

    stories = data.get("stories", [])
    if not isinstance(stories, list):
        errors.append("stories: expected array")
        stories = []
    items = [data.get("lead", {})] + stories
    for index, item in enumerate(items):
        item_id = item.get("id", "?") if isinstance(item, dict) else "?"
        label = f"item[{index}]/{item_id}"
        required = set(REQUIRED_STORY)
        if index == 0:
            required.remove("kind")
        missing_fields(item, required, label, errors)
        if not isinstance(item, dict):
            continue
        require_strings(
            item,
            {"id", "title", "summary", "whyItMatters", "category", "region"},
            label,
            errors,
        )
        if isinstance(item.get("id"), str) and item["id"].strip():
            story_ids.append(item["id"])
        if index and item.get("kind") not in KINDS:
            errors.append(f"{label}: invalid kind {item.get('kind')}")
        source = item.get("source")
        if isinstance(source, dict):
            if not isinstance(source.get("name"), str) or not source["name"].strip():
                errors.append(f"{label}: source.name must be a non-empty string")
        elif not isinstance(source, str) or not source.strip():
            errors.append(f"{label}: source must be a string or object with name")
        validate_datetime_field(item, "publishedAt", label, errors)
        validate_url_field(item, "sourceUrl", label, errors, urls)

        image = item.get("image")
        if image:
            if valid_url(image):
                urls.append((label, "image", image))
            elif not valid_local_asset(image):
                errors.append(f"{label}: invalid or missing local image")
        for field in ("imageSourceUrl", "imageLicenseUrl"):
            if field in item:
                validate_url_field(item, field, label, errors, urls)
        if image and not valid_url(image):
            required_attribution = {
                "imageCredit",
                "imageLicense",
                "imageLicenseUrl",
                "imageSourceUrl",
                "imageProvider",
            }
            missing_fields(item, required_attribution, f"{label}/attribution", errors)
            require_strings(
                item,
                {"imageCredit", "imageLicense", "imageProvider"},
                f"{label}/attribution",
                errors,
            )
            source_target = canonical_url(item.get("imageSourceUrl"))
            license_target = canonical_url(item.get("imageLicenseUrl"))
            if source_target and license_target and source_target == license_target:
                errors.append(
                    f"{label}/attribution: imageSourceUrl and imageLicenseUrl must differ"
                )
        if isinstance(item.get("summary"), str) and len(item["summary"]) < 40:
            warnings.append(f"{label}: unusually short summary")

    duplicates = sorted({item_id for item_id in story_ids if story_ids.count(item_id) > 1})
    errors.extend(f"duplicate id: {item_id}" for item_id in duplicates)
    if len(stories) < 8:
        warnings.append("fewer than 8 stories")

    signals = data.get("signals")
    if not isinstance(signals, list):
        errors.append("signals: expected array")
        signals = []
    if not signals:
        errors.append("signals: expected at least one item")
    for index, signal in enumerate(signals):
        label = f"signals/item[{index}]"
        missing_fields(signal, {"title", "level", "intensity", "detail"}, label, errors)
        if not isinstance(signal, dict):
            continue
        require_strings(signal, {"title", "detail"}, label, errors)
        if signal.get("level") not in {"high", "watch"}:
            errors.append(f"{label}: invalid level {signal.get('level')}")
        if not is_number(signal.get("intensity")) or not 0 <= float(signal["intensity"]) <= 100:
            errors.append(f"{label}: intensity must be between 0 and 100")

    ticker = data.get("ticker")
    if not isinstance(ticker, list):
        errors.append("ticker: expected array")
        ticker = []
    if not ticker:
        errors.append("ticker: expected at least one item")
    for index, item in enumerate(ticker):
        label = f"ticker/item[{index}]"
        missing_fields(item, {"label"}, label, errors)
        if isinstance(item, dict):
            require_strings(item, {"label"}, label, errors)

    focus_topics = data.get("focusTopics")
    if not isinstance(focus_topics, list):
        errors.append("focusTopics: expected array")
        focus_topics = []
    if not focus_topics:
        errors.append("focusTopics: expected at least one item")
    focus_ids: list[str] = []
    for index, item in enumerate(focus_topics):
        label = f"focusTopics/item[{index}]"
        required = {
            "id",
            "title",
            "status",
            "daysActive",
            "summary",
            "latestUpdate",
            "sourceCount",
            "image",
        }
        missing_fields(item, required, label, errors)
        if not isinstance(item, dict):
            continue
        require_strings(
            item,
            {"id", "title", "status", "summary", "latestUpdate"},
            label,
            errors,
        )
        if isinstance(item.get("id"), str) and item["id"].strip():
            focus_ids.append(item["id"])
        if not is_nonnegative_int(item.get("daysActive")) or item.get("daysActive", 0) <= 0:
            errors.append(f"{label}: daysActive must be a positive integer")
        if not is_nonnegative_int(item.get("sourceCount")) or item.get("sourceCount", 0) <= 0:
            errors.append(f"{label}: sourceCount must be a positive integer")
        image = item.get("image")
        if valid_url(image):
            urls.append((label, "image", image))
        elif not valid_local_asset(image):
            errors.append(f"{label}: invalid or missing image")
    if len(set(focus_ids)) != len(focus_ids):
        errors.append("focusTopics: duplicate item id")

    newsletter = data.get("newsletter", {})
    missing_fields(
        newsletter,
        {"title", "publishedAt", "summary", "highlights", "sourceUrl"},
        "newsletter",
        errors,
    )
    if isinstance(newsletter, dict):
        require_strings(newsletter, {"title", "summary"}, "newsletter", errors)
        validate_datetime_field(newsletter, "publishedAt", "newsletter", errors)
        validate_url_field(newsletter, "sourceUrl", "newsletter", errors, urls)
        highlights = newsletter.get("highlights")
        if not isinstance(highlights, list) or not highlights or not all(
            isinstance(value, str) and value.strip() for value in highlights
        ):
            errors.append("newsletter: highlights must be a non-empty string array")

    polling = data.get("polling", {})
    polling_required = {
        "title",
        "publishedAt",
        "fieldwork",
        "sampleSize",
        "institute",
        "commissionedBy",
        "question",
        "comparisonLabel",
        "parties",
        "coalitionNote",
        "sourceUrl",
        "methodologyUrl",
        "note",
    }
    missing_fields(polling, polling_required, "polling", errors)
    parties: list[dict] = []
    if isinstance(polling, dict):
        require_strings(
            polling,
            {
                "title",
                "fieldwork",
                "institute",
                "commissionedBy",
                "question",
                "comparisonLabel",
                "coalitionNote",
                "note",
            },
            "polling",
            errors,
        )
        validate_datetime_field(polling, "publishedAt", "polling", errors)
        validate_url_field(polling, "sourceUrl", "polling", errors, urls)
        validate_url_field(polling, "methodologyUrl", "polling", errors, urls)
        if not is_nonnegative_int(polling.get("sampleSize")) or polling.get("sampleSize", 0) <= 0:
            errors.append("polling: sampleSize must be a positive integer")
        raw_parties = polling.get("parties")
        if not isinstance(raw_parties, list):
            errors.append("polling: parties must be an array")
        else:
            parties = raw_parties

    if len(parties) < 6:
        errors.append("polling: fewer than 6 parties")
    party_ids: list[str] = []
    for index, party in enumerate(parties):
        label = f"polling/party[{index}]"
        missing_fields(party, {"id", "name", "value", "delta"}, label, errors)
        if not isinstance(party, dict):
            continue
        require_strings(party, {"id", "name"}, label, errors)
        if isinstance(party.get("id"), str):
            party_ids.append(party["id"])
        if not is_number(party.get("value")) or not 0 <= float(party["value"]) <= 100:
            errors.append(f"{label}: value must be between 0 and 100")
        if not is_number(party.get("delta")) or not -100 <= float(party["delta"]) <= 100:
            errors.append(f"{label}: delta must be between -100 and 100")
    if len(set(party_ids)) != len(party_ids):
        errors.append("polling: duplicate party id")
    if parties and all(
        isinstance(party, dict) and is_number(party.get("value"))
        for party in parties
    ):
        total = sum(float(party["value"]) for party in parties)
        if not 99 <= total <= 101:
            errors.append(f"polling: party values add up to {total:g}, expected about 100")

    criticism_section = data.get("governmentCriticism", {})
    missing_fields(
        criticism_section,
        {"asOf", "intro", "items"},
        "governmentCriticism",
        errors,
    )
    criticism: list[dict] = []
    if isinstance(criticism_section, dict):
        require_strings(criticism_section, {"intro"}, "governmentCriticism", errors)
        validate_datetime_field(
            criticism_section,
            "asOf",
            "governmentCriticism",
            errors,
            allow_date=True,
        )
        raw_criticism = criticism_section.get("items")
        if not isinstance(raw_criticism, list):
            errors.append("governmentCriticism: items must be an array")
        else:
            criticism = raw_criticism
    if len(criticism) < 3:
        errors.append("governmentCriticism: fewer than 3 items")
    criticism_ids: list[str] = []
    for index, item in enumerate(criticism):
        label = f"governmentCriticism/item[{index}]"
        required = {
            "id",
            "topic",
            "title",
            "level",
            "criticism",
            "critic",
            "response",
            "source",
            "sourceUrl",
        }
        missing_fields(item, required, label, errors)
        if not isinstance(item, dict):
            continue
        require_strings(
            item,
            {"id", "topic", "title", "criticism", "critic", "response", "source"},
            label,
            errors,
        )
        if isinstance(item.get("id"), str):
            criticism_ids.append(item["id"])
        if item.get("level") not in CRITICISM_LEVELS:
            errors.append(f"{label}: invalid level {item.get('level')}")
        validate_url_field(item, "sourceUrl", label, errors, urls)
    if len(set(criticism_ids)) != len(criticism_ids):
        errors.append("governmentCriticism: duplicate item id")

    social = data.get("socialRadar", {})
    missing_fields(
        social,
        {"observedAt", "summary", "profiles", "tiktok", "limitations"},
        "socialRadar",
        errors,
    )
    profiles: list[dict] = []
    tiktok: dict = {}
    if isinstance(social, dict):
        require_strings(social, {"summary", "limitations"}, "socialRadar", errors)
        validate_datetime_field(social, "observedAt", "socialRadar", errors)
        raw_profiles = social.get("profiles")
        if not isinstance(raw_profiles, list):
            errors.append("socialRadar: profiles must be an array")
        else:
            profiles = raw_profiles
        if not isinstance(social.get("tiktok"), dict):
            errors.append("socialRadar: tiktok must be an object")
        else:
            tiktok = social["tiktok"]

    platforms: list[str] = []
    for index, profile in enumerate(profiles):
        label = f"socialRadar/profile[{index}]"
        required = {"platform", "handle", "url", "status", "note"}
        missing_fields(profile, required, label, errors)
        if not isinstance(profile, dict):
            continue
        require_strings(profile, {"platform", "handle", "status", "note"}, label, errors)
        if isinstance(profile.get("platform"), str):
            platforms.append(profile["platform"])
        if profile.get("status") not in PROFILE_STATUSES:
            errors.append(f"{label}: invalid status {profile.get('status')}")
        validate_url_field(profile, "url", label, errors, urls)
        if profile.get("status") == "vollständig":
            for field in ("followers", "videoCount", "profileLikes"):
                if not is_nonnegative_int(profile.get(field)):
                    errors.append(f"{label}: {field} must be a non-negative integer")
    if set(platforms) != {"TikTok", "Instagram", "Facebook"} or len(platforms) != 3:
        errors.append("socialRadar: expected exactly TikTok, Instagram and Facebook profiles")

    tiktok_required = {
        "accountVerified",
        "sampleSize",
        "viewsTotal",
        "viewsAverage",
        "viewsMedian",
        "interactionRate",
        "topVideoShare",
        "method",
        "posts",
    }
    missing_fields(tiktok, tiktok_required, "socialRadar/tiktok", errors)
    posts: list[dict] = []
    if isinstance(tiktok, dict):
        if not isinstance(tiktok.get("accountVerified"), bool):
            errors.append("socialRadar/tiktok: accountVerified must be boolean")
        if not isinstance(tiktok.get("method"), str) or not tiktok["method"].strip():
            errors.append("socialRadar/tiktok: method must be a non-empty string")
        for field in ("sampleSize", "viewsTotal", "viewsAverage", "viewsMedian"):
            if not is_nonnegative_int(tiktok.get(field)):
                errors.append(f"socialRadar/tiktok: {field} must be a non-negative integer")
        for field in ("interactionRate", "topVideoShare"):
            if not is_number(tiktok.get(field)) or not 0 <= float(tiktok[field]) <= 100:
                errors.append(f"socialRadar/tiktok: {field} must be between 0 and 100")
        raw_posts = tiktok.get("posts")
        if not isinstance(raw_posts, list):
            errors.append("socialRadar/tiktok: posts must be an array")
        else:
            posts = raw_posts

    if len(posts) < 3:
        errors.append("socialRadar: fewer than 3 TikTok posts")
    post_ids: list[str] = []
    for index, post in enumerate(posts):
        label = f"socialRadar/post[{index}]"
        required = {
            "id",
            "title",
            "publishedAt",
            "durationSeconds",
            "views",
            "likes",
            "comments",
            "reposts",
            "performance",
            "url",
        }
        missing_fields(post, required, label, errors)
        if not isinstance(post, dict):
            continue
        require_strings(post, {"id", "title", "performance"}, label, errors)
        if isinstance(post.get("id"), str):
            post_ids.append(post["id"])
        validate_datetime_field(post, "publishedAt", label, errors)
        validate_url_field(post, "url", label, errors, urls)
        for field in ("durationSeconds", "views", "likes", "comments", "reposts"):
            if not is_nonnegative_int(post.get(field)):
                errors.append(f"{label}: {field} must be a non-negative integer")
        if post.get("performance") not in POST_PERFORMANCE:
            errors.append(f"{label}: invalid performance {post.get('performance')}")
    if len(set(post_ids)) != len(post_ids):
        errors.append("socialRadar: duplicate TikTok post id")

    if posts and all(
        isinstance(post, dict) and is_nonnegative_int(post.get(field))
        for post in posts
        for field in ("views", "likes", "comments", "reposts")
    ):
        views = [post["views"] for post in posts]
        total_views = sum(views)
        interactions = sum(
            post["likes"] + post["comments"] + post["reposts"] for post in posts
        )
        expected = {
            "sampleSize": len(posts),
            "viewsTotal": total_views,
            "viewsAverage": round(statistics.mean(views)),
            "viewsMedian": round(statistics.median(views)),
            "interactionRate": round(interactions / total_views * 100, 1)
            if total_views
            else 0.0,
            "topVideoShare": round(max(views) / total_views * 100, 1)
            if total_views
            else 0.0,
        }
        for field, expected_value in expected.items():
            actual = tiktok.get(field)
            if not is_number(actual) or not math.isclose(
                float(actual), float(expected_value), abs_tol=0.05
            ):
                errors.append(
                    f"socialRadar/tiktok: {field}={actual!r}, calculated={expected_value!r}"
                )

    source_urls = collect_source_urls(data)
    source_count = len(source_urls)
    declared = meta.get("sourceCount") if isinstance(meta, dict) else None
    if declared != source_count:
        errors.append(f"sourceCount={declared}, calculated={source_count}")

    return errors, warnings, urls, len(story_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(ROOT / "data/news.json"))
    parser.add_argument("--check-links", action="store_true")
    args = parser.parse_args()

    try:
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: invalid JSON: {exc}")
        return 1

    errors, warnings, urls, id_count = validate(data)

    if args.check_links:
        checked: set[str] = set()
        source_urls = collect_source_urls(data)
        extended = [(f"extended/{url}", "source", url) for url in sorted(source_urls)]
        for label, key, url in urls + extended:
            if url in checked:
                continue
            checked.add(url)
            try:
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    method="HEAD",
                )
                with urllib.request.urlopen(request, timeout=12) as response:
                    if response.status >= 400:
                        errors.append(f"{label}: {key} HTTP {response.status}")
            except Exception as exc:
                warnings.append(
                    f"{label}: {key} check failed ({type(exc).__name__}: {exc})"
                )

    for message in warnings:
        print("WARN:", message)
    for message in errors:
        print("ERROR:", message)
    print(
        json.dumps(
            {
                "stories": len(data.get("stories", [])) if isinstance(data, dict) else 0,
                "ids": id_count,
                "errors": len(errors),
                "warnings": len(warnings),
            },
            ensure_ascii=False,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
