"""Candidate doc-URL discovery.

No keyless web-search endpoint is reachable from the pipeline, so candidates come from
three sources — the seed hint URL, deterministic doc-path patterns, and model-proposed
URLs — and every one of them is then *fetched* before it can be used. Proposals are
therefore only a guess at where to look; the fetch decides what is real.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from google import genai

from agent.gemini import generate_json
from agent.models import AppSeed

CANDIDATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "urls": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Candidate documentation URLs, most likely first.",
        }
    },
    "required": ["urls"],
}

PROPOSAL_PROMPT = """You are helping locate the *developer documentation* for an app.

App: {name}
Category: {category}
{hint}

List up to 10 URLs where this app's developer/API documentation most plausibly lives.
Cover both of these separately:
  1. Pages describing how to CALL the API once authenticated (API reference, auth docs).
  2. Pages describing how a FIRST-TIME developer OBTAINS credentials (signup, register an
     app, developer program, partner/API access request, pricing or contact-sales pages
     if access is gated).

Rules:
- Return plausible real URLs only. Do not invent deep paths you are unsure about; prefer
  shorter, more certain URLs (a docs homepage beats a guessed deep link).
- Every URL will be fetched and discarded if it 404s, so precision matters more than depth.
- Return only the JSON object.
"""

DOC_PATH_PATTERNS = (
    "https://docs.{domain}/",
    "https://developer.{domain}/",
    "https://developers.{domain}/",
    "https://api.{domain}/",
    "https://{domain}/docs",
    "https://{domain}/developers",
    "https://{domain}/api",
    "https://{domain}/developer",
)


# Second-level labels that are part of the public suffix rather than the name itself,
# so "docs.example.co.uk" still yields "example.co.uk".
SECOND_LEVEL_SUFFIXES = {"co", "com", "net", "org", "ac", "gov", "edu"}


def root_domain(url: str | None) -> str | None:
    """Registrable domain for a URL: docs.dealcloud.com -> dealcloud.com."""
    if not url:
        return None
    host = urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")
    if not host:
        return None
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    if labels[-2] in SECOND_LEVEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def pattern_candidates(domain: str | None) -> list[str]:
    if not domain:
        return []
    return [pattern.format(domain=domain) for pattern in DOC_PATH_PATTERNS]


def propose_candidates(
    client: genai.Client, seed: AppSeed
) -> tuple[list[str], str, str]:
    """Ask the model where the docs probably are. Returns (urls, raw_response, model_used)."""
    hint = f"Known starting URL: {seed.hint_url}" if seed.hint_url else "No starting URL known."
    prompt = PROPOSAL_PROMPT.format(name=seed.name, category=seed.category, hint=hint)
    data, raw, model_used = generate_json(client, prompt, CANDIDATE_SCHEMA)
    urls = [u for u in data.get("urls", []) if isinstance(u, str) and u.startswith("http")]
    return urls, raw, model_used


def dedupe(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        key = url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            out.append(url)
    return out
