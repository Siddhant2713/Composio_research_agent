"""Schema-constrained extraction over pages the pipeline actually fetched."""
from __future__ import annotations

from typing import Any

from google import genai

from agent.fetch import Page
from agent.gemini import generate_json
from agent.models import AppRecord, AppSeed

# Gemini's response_schema is a shape hint; schema.json remains the contract that the
# finished record is validated against.
EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "one_liner": {"type": "string", "nullable": True},
        "auth": {
            "type": "object",
            "nullable": True,
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["oauth2", "api_key", "basic_auth", "jwt", "mtls", "saml", "none", "other", "unknown"],
                },
                "notes": {"type": "string", "nullable": True},
            },
            "required": ["method", "notes"],
        },
        "access": {
            "type": "object",
            "nullable": True,
            "properties": {
                "type": {"type": "string", "enum": ["self_serve", "gated", "mixed", "unknown"]},
                "notes": {"type": "string", "nullable": True},
            },
            "required": ["type", "notes"],
        },
        "api_surface": {
            "type": "object",
            "nullable": True,
            "properties": {
                "rest": {"type": "boolean", "nullable": True},
                "graphql": {"type": "boolean", "nullable": True},
                "webhooks": {"type": "boolean", "nullable": True},
                "sdks": {"type": "array", "items": {"type": "string"}, "nullable": True},
                "notes": {"type": "string", "nullable": True},
            },
            "required": ["rest", "graphql", "webhooks", "sdks", "notes"],
        },
        "mcp": {
            "type": "object",
            "nullable": True,
            "properties": {
                "exists": {"type": "boolean", "nullable": True},
                "url": {"type": "string", "nullable": True},
                "notes": {"type": "string", "nullable": True},
            },
            "required": ["exists", "notes"],
        },
        "buildability": {
            "type": "object",
            "nullable": True,
            "properties": {
                "verdict": {"type": "string", "enum": ["easy", "moderate", "hard", "blocked", "unknown"]},
                "reasoning": {"type": "string", "nullable": True},
            },
            "required": ["verdict", "reasoning"],
        },
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "claim": {"type": "string"},
                },
                "required": ["url", "claim"],
            },
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "one_liner", "auth", "access", "api_surface", "mcp", "buildability",
        "evidence", "confidence",
    ],
}

EXTRACTION_PROMPT = """You are a meticulous technical researcher. Below is the FULL TEXT of
pages that were actually fetched over HTTP for the app "{name}" ({category}).

Your job: fill in the record from THESE PAGES ONLY.

## Absolute rules
- State a fact ONLY if the page text below says it. You have no other permitted source.
  Your own prior knowledge about this app is NOT evidence and must not appear in the output.
- If the pages do not answer a field, set that field to null (or "unknown" for an enum) and
  set overall confidence to "low". A null is a correct answer. A guess is a failure.
- Every evidence[].url MUST be copied verbatim from the "SOURCE" lines below. Do not
  construct, shorten, or modify a URL, and never cite a URL that is not listed.
- Each evidence[].claim must state which specific fact that page supports.
- A bare capability NAME in a list of links, menu, sidebar, or table of contents is NOT
  evidence that the product has that capability. Treat a lone phrase such as
  "Model Context Protocol", "Webhooks" or "GraphQL", with no sentence explaining it, as
  navigation noise. Only count a capability when the page says something substantive about
  it. If the only trace of a feature is its name in a list, that feature is null/unknown.

## Which API to describe
If the product exposes several APIs, describe the one a THIRD-PARTY INTEGRATION would use
to automate the product on a user's behalf (the public developer/bot/partner API), not an
internal, client-implementation, or protocol-level API. Say which one you chose in
`one_liner` or the notes.

## Two separate questions — do not conflate them
1. `auth` = how an ALREADY-REGISTERED developer authenticates API calls. Pick by mechanism:
   - "api_key": a long-lived secret the developer copies and sends on each request — an API
     key, a bot token, a personal access token — whether it travels in a header, query
     string, or URL path.
   - "oauth2": an authorization flow exchanging client id/secret or a user consent redirect
     for a token (including the client-credentials grant).
   - "basic_auth": HTTP Basic. "jwt": a signed JWT the caller mints. "mtls"/"saml": as named.
   - "other" only when the mechanism genuinely fits none of the above — not merely because
     several mechanisms exist. If several exist, pick the one for the integration API above
     and describe the rest in `notes`.
2. `access` = how a FIRST-TIME developer OBTAINS credentials in the first place.
   - "self_serve": anyone can sign up and get working credentials themselves, unaided.
   - "gated": credentials require sales contact, an existing paid/enterprise contract,
     partner-program approval, manual review, or an account manager.
   - "mixed": a self-serve tier exists but important capabilities are gated.
   Thorough, polished public API documentation is NOT evidence of self-serve access.
   Many gated platforms publish excellent docs. Judge `access` only on what the pages say
   about OBTAINING credentials. If the pages describe calling the API in detail but never
   show a self-serve way to get keys, that is evidence for "gated" or "unknown" — not
   "self_serve".

## buildability
Judge whether an agent integration is realistically buildable by an outside developer today:
"easy" (self-serve creds + documented API), "moderate" (extra hoops: review, app approval,
partner OAuth), "hard" (major friction/cost), "blocked" (no outside access at all),
"unknown" (pages don't say). Explain in `reasoning`, referencing access AND auth.

## Fetched pages
{corpus}

Return only the JSON object.
"""


def build_corpus(pages: list[Page]) -> str:
    blocks = []
    for i, page in enumerate(pages, 1):
        blocks.append(
            f"----- PAGE {i} -----\n"
            f"SOURCE: {page.url}\n"
            f"TITLE: {page.title}\n"
            f"TEXT:\n{page.text}\n"
        )
    return "\n".join(blocks)


def extract_record(
    client: genai.Client,
    seed: AppSeed,
    pages: list[Page],
) -> tuple[AppRecord, str, str]:
    """Extract a record for one app. Returns (record, raw_model_output, model_used)."""
    prompt = EXTRACTION_PROMPT.format(
        name=seed.name, category=seed.category, corpus=build_corpus(pages)
    )
    data, raw, model_used = generate_json(client, prompt, EXTRACTION_SCHEMA)

    allowed = {page.url: page for page in pages}
    accessed = {page.url: page.accessed_at for page in pages}

    # Drop any evidence URL that was not in the fetched set. This is the backstop against
    # the model inventing or mangling a citation despite the prompt.
    evidence = []
    for item in data.get("evidence") or []:
        url = (item or {}).get("url")
        if url in allowed:
            evidence.append(
                {"url": url, "claim": item.get("claim", ""), "accessed_at": accessed[url]}
            )

    record = AppRecord.model_validate(
        {
            "number": seed.number,
            "name": seed.name,
            "category": seed.category,
            "hint_url": seed.hint_url,
            "one_liner": data.get("one_liner"),
            "auth": data.get("auth"),
            "access": data.get("access"),
            "api_surface": data.get("api_surface"),
            "mcp": data.get("mcp"),
            "buildability": data.get("buildability"),
            "evidence": evidence,
            "confidence": data.get("confidence") or "low",
        }
    )
    return record, raw, model_used
