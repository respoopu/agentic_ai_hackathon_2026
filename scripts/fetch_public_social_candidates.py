#!/usr/bin/env python3
"""Collect review-safe activity leads from explicitly public social sources.

This is a discovery aid, not a CKB publisher. It currently reads Telegram's
public web previews and stores compact metadata, detected fact tokens, a short
excerpt and the stable post URL. It never marks a row verified, guesses absent
CKB fields, accesses private groups, or attempts to bypass a login wall.

Instagram and Facebook entries in the source catalogue are intentionally
``lead_only``. Their public profiles help humans find organisers, while a stable
organiser/event page is preferred for canonical evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ROOT / "data" / "public_activity_sources.json"
DEFAULT_OUT = ROOT / "data" / "draft_social_candidates.json"
USER_AGENT = "hobbi-public-source-research/1.0 (+local hackathon prototype)"
MAX_RESPONSE_BYTES = 2_000_000
MAX_EXCERPT_CHARS = 280

MONTHS = (
    "jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    "jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    "nov(?:ember)?|dec(?:ember)?"
)
DATE_PATTERNS = (
    re.compile(
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})(?:\s+20\d{{2}})?\b", re.IGNORECASE
    ),
    re.compile(
        rf"\b(?:{MONTHS})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+20\d{{2}})?\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),
)
TIME_PATTERN = re.compile(r"\b\d{1,2}(?:(?::|\.)\d{2})?\s*(?:am|pm)\b", re.IGNORECASE)
COST_PATTERN = re.compile(
    r"(?<!\w)(?:S\$|SGD|\$)\s*\d+(?:\.\d{1,2})?|\b(?:free|complimentary|FOC)\b",
    re.IGNORECASE,
)
AGE_PATTERN = re.compile(
    r"\b(?:aged?|ages?|youths?\s*\(?aged)\s*\d{1,2}"
    r"(?:\s*(?:-|–|to)\s*\d{1,2})?(?:\s*(?:years?|yo|y/o)\s*old)?|"
    r"\ball ages\b",
    re.IGNORECASE,
)
POSTAL_PATTERN = re.compile(r"(?<!\d)\d{6}(?!\d)")
EVENT_HINT_PATTERN = re.compile(
    r"\b(?:register|registration|sign up|workshop|class|course|session|event|"
    r"festival|walk|ride|cycling|performance|screening|volunteer|open house|"
    r"drop[- ]?in|market|swap|tour|training|programme|program)\b",
    re.IGNORECASE,
)


@dataclass
class TelegramMessage:
    post_path: str
    published_at: str | None = None
    text_parts: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        value = html.unescape("".join(self.text_parts))
        lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
        return "\n".join(line for line in lines if line)


class TelegramPreviewParser(HTMLParser):
    """Extract message text and stable links from Telegram's public preview."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.messages: list[TelegramMessage] = []
        self._message: TelegramMessage | None = None
        self._message_div_depth = 0
        self._text_div_depth: int | None = None
        self.previous_url: str | None = None

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = self._attrs(attrs)
        classes = set(values.get("class", "").split())
        if (
            tag == "div"
            and values.get("data-post")
            and "tgme_widget_message" in classes
        ):
            # A new message root proves the previous one was malformed if its
            # closing div never arrived. Drop that partial message rather than
            # letting it swallow all subsequent posts or emit invented fields.
            self._message = TelegramMessage(post_path=values["data-post"])
            self._message_div_depth = 1
            return

        if self._message is not None:
            if tag == "div":
                self._message_div_depth += 1
                if "tgme_widget_message_text" in classes:
                    self._text_div_depth = self._message_div_depth
            if tag == "time" and values.get("datetime"):
                self._message.published_at = values["datetime"]
            if tag == "a" and values.get("href"):
                self._message.links.append(values["href"])
            if tag == "br" and self._text_div_depth is not None:
                self._message.text_parts.append("\n")
            return

        if tag == "a" and "tme_messages_more" in classes and values.get("href"):
            self.previous_url = urllib.parse.urljoin("https://t.me", values["href"])

    def handle_endtag(self, tag: str) -> None:
        if self._message is None or tag != "div":
            return
        if self._text_div_depth == self._message_div_depth:
            self._text_div_depth = None
        self._message_div_depth -= 1
        if self._message_div_depth == 0:
            self.messages.append(self._message)
            self._message = None

    def handle_data(self, data: str) -> None:
        if self._message is not None and self._text_div_depth is not None:
            self._message.text_parts.append(data)


def _fetch(url: str, *, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status >= 400:
            raise urllib.error.HTTPError(
                url, response.status, response.reason, response.headers, None
            )
        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError(f"response exceeded {MAX_RESPONSE_BYTES} bytes")
    return payload.decode("utf-8", errors="replace")


def _unique_matches(patterns: tuple[re.Pattern[str], ...], text: str) -> list[str]:
    values: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = re.sub(r"\s+", " ", match.group(0)).strip()
            if value.lower() not in {existing.lower() for existing in values}:
                values.append(value)
    return values


def _clean_links(links: list[str], post_url: str) -> list[str]:
    output: list[str] = []
    for link in links:
        absolute = urllib.parse.urljoin("https://t.me", link)
        parsed = urllib.parse.urlsplit(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc.endswith("t.me") and absolute != post_url:
            continue
        if absolute not in output:
            output.append(absolute)
    return output


def message_to_candidate(
    message: TelegramMessage, source: dict[str, Any]
) -> dict[str, Any] | None:
    text = message.text
    if not text:
        return None
    dates = _unique_matches(DATE_PATTERNS, text)
    times = _unique_matches((TIME_PATTERN,), text)
    costs = _unique_matches((COST_PATTERN,), text)
    ages = _unique_matches((AGE_PATTERN,), text)
    postals = _unique_matches((POSTAL_PATTERN,), text)
    event_score = sum(
        (
            bool(dates),
            bool(times),
            bool(costs),
            bool(ages),
            bool(postals),
            bool(EVENT_HINT_PATTERN.search(text)),
        )
    )
    if event_score < 2:
        return None

    post_url = f"https://t.me/{message.post_path}"
    excerpt = re.sub(r"\s+", " ", text).strip()[:MAX_EXCERPT_CHARS]
    first_line = text.splitlines()[0][:120]
    return {
        "candidate_id": "SOC-" + hashlib.sha256(post_url.encode()).hexdigest()[:12],
        "source_id": source["source_id"],
        "platform": "telegram",
        "source_name": source["name"],
        "source_url": post_url,
        "published_at": message.published_at,
        "verification": "unverified",
        "is_fictional": False,
        "title_hint": first_line,
        "excerpt": excerpt,
        "content_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "registration_urls": _clean_links(message.links, post_url),
        "detected": {
            "dates": dates,
            "times": times,
            "costs": costs,
            "ages": ages,
            "postal_codes": postals,
        },
        "area_hints": source.get("area_hints", []),
        "topic_hints": source.get("topic_hints", []),
        "review_required": [
            "confirm exact event title and provider",
            "confirm future schedule and duration",
            "confirm venue, postal code, and URA planning area",
            "confirm total first-session and equipment cost",
            "confirm age range and 13-17 eligibility",
            "confirm beginner, join-alone, and guest rules",
            "prefer a stable organiser or registration page when available",
        ],
    }


def collect_telegram(
    source: dict[str, Any], *, pages: int, delay: float, timeout: float
) -> tuple[list[dict[str, Any]], list[str]]:
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []
    next_url: str | None = source["url"]
    seen_posts: set[str] = set()
    for page_index in range(pages):
        if next_url is None:
            break
        try:
            body = _fetch(next_url, timeout=timeout)
        except (OSError, TimeoutError, ValueError, urllib.error.URLError) as exc:
            errors.append(f"{source['source_id']}: {type(exc).__name__}: {exc}")
            break
        parser = TelegramPreviewParser()
        parser.feed(body)
        for message in parser.messages:
            if message.post_path in seen_posts:
                continue
            seen_posts.add(message.post_path)
            candidate = message_to_candidate(message, source)
            if candidate is not None:
                candidates.append(candidate)
        next_url = parser.previous_url
        if next_url is not None and page_index + 1 < pages:
            time.sleep(delay)
    return candidates, errors


def run(
    source_path: Path,
    out_path: Path,
    *,
    pages: int,
    delay: float,
    timeout: float,
) -> dict[str, Any]:
    catalogue = json.loads(source_path.read_text(encoding="utf-8"))
    sources = catalogue.get("sources")
    if not isinstance(sources, list):
        raise TypeError("source catalogue must contain a sources list")

    candidates: list[dict[str, Any]] = []
    errors: list[str] = []
    lead_only: list[dict[str, Any]] = []
    for source in sources:
        if source.get("mode") == "lead_only":
            lead_only.append(source)
            continue
        if (
            source.get("platform") != "telegram"
            or source.get("mode") != "public_preview"
        ):
            errors.append(
                f"{source.get('source_id', '<unknown>')}: unsupported source mode"
            )
            continue
        found, source_errors = collect_telegram(
            source, pages=pages, delay=delay, timeout=timeout
        )
        candidates.extend(found)
        errors.extend(source_errors)
        time.sleep(delay)

    deduplicated = {candidate["source_url"]: candidate for candidate in candidates}
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "status": "unverified discovery candidates; not a canonical CKB artifact",
        "policy": catalogue.get("policy", {}),
        "summary": {
            "public_preview_sources": len(sources) - len(lead_only),
            "lead_only_sources": len(lead_only),
            "candidate_count": len(deduplicated),
            "error_count": len(errors),
        },
        "lead_only_sources": lead_only,
        "errors": errors,
        "candidates": sorted(
            deduplicated.values(),
            key=lambda row: (row.get("published_at") or "", row["source_url"]),
            reverse=True,
        ),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    temporary.replace(out_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pages", type=int, default=2)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    if args.pages < 1 or args.pages > 10:
        parser.error("--pages must be between 1 and 10")
    if args.delay < 0.25:
        parser.error("--delay must be at least 0.25 seconds")
    payload = run(
        args.sources,
        args.out,
        pages=args.pages,
        delay=args.delay,
        timeout=args.timeout,
    )
    summary = payload["summary"]
    print(
        f"Collected {summary['candidate_count']} unverified candidates from "
        f"{summary['public_preview_sources']} public previews; "
        f"{summary['lead_only_sources']} social profiles retained as leads; "
        f"{summary['error_count']} errors."
    )
    return 0 if summary["candidate_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
