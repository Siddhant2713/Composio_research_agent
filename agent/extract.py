"""Schema-constrained extraction over pages the pipeline actually fetched."""
from __future__ import annotations

import re
from typing import Any

from google import genai

from agent.fetch import Page
from agent.gemini import generate_json
from agent.models import (
    AccessType,
    AppRecord,
    AppSeed,
    AuthMethod,
    BuildabilityVerdict,
    Confidence,
)

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
                "tier": {"type": "string", "enum": ["self_serve", "gated", "mixed", "unknown"]},
                "notes": {"type": "string", "nullable": True},
            },
            "required": ["tier", "notes"],
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
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "claim": {"type": "string"},
                    "quote": {
                        "type": "string",
                        "nullable": True,
                        "description": "Verbatim sentence from that page supporting the claim.",
                    },
                },
                "required": ["url", "claim", "quote"],
            },
        },
        # Pass 2: each substantive field must name the line it rests on. Verified against the
        # fetched text afterwards, so an unquotable claim cannot survive.
        "support": {
            "type": "object",
            "properties": {
                field: {
                    "type": "object",
                    "nullable": True,
                    "properties": {
                        "url": {"type": "string"},
                        "quote": {"type": "string"},
                    },
                    "required": ["url", "quote"],
                }
                for field in ("auth", "access", "api_surface", "mcp")
            },
            "required": ["auth", "access", "api_surface", "mcp"],
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "one_liner", "auth", "access", "api_surface", "mcp",
        "evidence", "support", "confidence",
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
- Each evidence[].claim must state which specific fact that page supports, and
  evidence[].quote must be the sentence from THAT page which supports it, copied WORD FOR
  WORD. Quotes are checked against the page text automatically; a quote that does not appear
  there verbatim is discarded along with its claim, so do not paraphrase or stitch together
  fragments from different places.

## `support` — the line each finding rests on
For `auth`, `access`, `api_surface` and `mcp` you must fill `support.<field>` with the single
`{{url, quote}}` pair that most directly establishes that field, quoted WORD FOR WORD from that
page. These quotes are verified against the fetched text. If you cannot find a real sentence
for a field, set `support.<field>` to null AND set that field to unknown/null — do not answer
a field you cannot quote a line for. This applies especially to:
- `mcp.exists`: true requires a sentence describing the MCP server, not a menu entry.
- `api_surface`: each true boolean needs the text to actually mention that interface.
- `access`: the quote must be about OBTAINING credentials (see below), not about calling the
  API and not marketing copy.
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
   Decide it from POSITIVE signals on either side. The pages do not have to narrate a
   sign-up flow step by step.
   - "self_serve": the pages show an unaffiliated developer getting credentials on their
     own, and nothing suggests a gate. Any of these counts: a self-service sign-up or
     free-trial link; instructions to generate an API key, token, or app in the product's
     own settings / dashboard / developer console; "create an account, then find your key
     here". A developer minting their own key inside their own account IS self-serve.
   - "gated": there is a positive gate signal — contact sales, request or apply for access,
     a waitlist, partner-program or app-review approval, an account manager, or credentials
     that presuppose something the vendor must provision first (an existing enterprise
     contract, a provisioned tenant or site instance, an admin enabling API access).
   - "mixed": a self-serve tier exists but important capabilities sit behind a gate.
   - "unknown": the pages genuinely say nothing either way about getting credentials.
   Two failure modes to avoid, in both directions:
   - Thorough, polished API documentation is NOT evidence of self-serve access. Plenty of
     gated platforms publish excellent reference docs. Detail about *calling* the API says
     nothing about *getting in*.
   - Equally, do not answer "unknown" when the pages do show a developer creating their own
     credentials just because they never spell out the signup funnel. That is self_serve.

## buildability
Do not produce a buildability verdict. It is computed from `access`, `auth` and
`api_surface` after your answer is validated, so that it always follows from the fields it
depends on instead of being asserted on its own.

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
        if url not in allowed:
            continue
        quote = (item or {}).get("quote")
        # A citation whose quote is not really on the page is a misattribution, which was
        # the single worst-scoring field in the Pass-1 audit. Drop it.
        if quote and not quote_is_real(quote, allowed[url]):
            continue
        evidence.append(
            {
                "url": url,
                "claim": item.get("claim", ""),
                "quote": quote,
                "accessed_at": accessed[url],
            }
        )

    fields = {
        "auth": data.get("auth"),
        "access": data.get("access"),
        "api_surface": data.get("api_surface"),
        "mcp": data.get("mcp"),
    }
    support, rejected = verify_support(data.get("support") or {}, fields, allowed)

    record = AppRecord.model_validate(
        {
            "number": seed.number,
            "name": seed.name,
            "category": seed.category,
            "hint_url": seed.hint_url,
            "one_liner": data.get("one_liner"),
            **fields,
            "buildability": derive_buildability(fields),
            "evidence": evidence,
            "support": support,
            "unsupported_fields": rejected,
            "confidence": data.get("confidence") or "low",
        }
    )
    return downgrade_unsupported_confidence(record), raw, model_used


def _canonical(text: str) -> str:
    """Letters and digits only, lowercased.

    HTML-to-text conversion splits inline elements, so a real sentence can come out as
    "organized around REST ." with a stray space before the punctuation. Comparing on
    alphanumerics alone ignores those artefacts while still requiring the same word
    sequence — an earlier whitespace-only comparison rejected quotes that were genuinely
    on the page.
    """
    return re.sub(r"[^a-z0-9]+", "", text.lower())


# A supporting quote has to be a sentence, not a label. Requiring several words is what
# stops a bare menu entry — "Model Context Protocol" on its own — from passing as evidence
# that a product ships that capability, which is the exact error this check exists to catch.
MIN_QUOTE_CHARS = 20
MIN_QUOTE_WORDS = 5


def quote_is_real(quote: str, page: Page) -> bool:
    """Whether a quote is a real sentence that genuinely appears on the page."""
    if not quote:
        return False
    if len(quote.split()) < MIN_QUOTE_WORDS:
        return False
    needle = _canonical(quote)
    if len(needle) < MIN_QUOTE_CHARS:
        return False
    return needle in _canonical(page.text)


def verify_support(
    support: dict, fields: dict, allowed: dict[str, Page]
) -> tuple[dict, list[str]]:
    """Check each field's quote against the page it names; blank the field if it fails.

    This is the teeth behind the prompt: a field the model could not quote a real line for
    is reset to unknown rather than kept on trust.
    """
    verified: dict[str, dict] = {}
    rejected: list[str] = []

    for field in ("auth", "access", "api_surface", "mcp"):
        value = fields.get(field)
        if value is None:
            continue

        entry = support.get(field) or {}
        url, quote = entry.get("url"), entry.get("quote")
        page = allowed.get(url)

        if page and quote_is_real(quote, page):
            verified[field] = {"url": url, "quote": quote}
            continue

        reason = (
            "no support offered" if not entry
            else f"quoted line not found on {url}" if page
            else f"support cites unfetched url {url}"
        )
        rejected.append(f"{field}: {reason}")
        fields[field] = _blank_field(field, value, reason)

    return verified, rejected


def _blank_field(field: str, value: dict, reason: str):
    """Reset an unsupported field to its unknown form, keeping a note of why."""
    note = f"Reported value was discarded: {reason}."
    if field == "auth":
        return {"method": "unknown", "notes": note}
    if field == "access":
        return {"tier": "unknown", "notes": note}
    if field == "mcp":
        return {"exists": None, "url": None, "notes": note}
    if field == "api_surface":
        return {
            "rest": None, "graphql": None, "webhooks": None, "sdks": None, "notes": note,
        }
    return value


def derive_buildability(fields: dict) -> dict:
    """Compute buildability from access, auth and API surface.

    In the Pass-1 audit this was the worst-scoring field (23%), because no page ever states
    "this is easy to build against" — the model was asserting a judgement it could not source.
    Deriving it makes the verdict follow from the findings that *are* evidenced, and makes it
    reproducible: the same inputs always give the same verdict.
    """
    access = (fields.get("access") or {}).get("tier") or "unknown"
    auth = (fields.get("auth") or {}).get("method") or "unknown"
    surface = fields.get("api_surface") or {}
    has_surface = any(bool(surface.get(k)) for k in ("rest", "graphql", "webhooks")) or bool(
        surface.get("sdks")
    )

    if access == "self_serve" and auth != "unknown" and has_surface:
        verdict, why = "easy", (
            f"Credentials are self-serve ({auth}) and the pages document a usable API surface."
        )
    elif access == "self_serve" and auth != "unknown":
        verdict, why = "moderate", (
            f"Credentials are self-serve ({auth}), but the pages do not establish the API "
            "surface, so integration work is harder to scope."
        )
    elif access == "mixed":
        verdict, why = "moderate", (
            "A self-serve tier exists but important capabilities sit behind a gate."
        )
    elif access == "gated":
        verdict, why = "hard", (
            "Credentials require approval, sales contact, or vendor provisioning, so an "
            "outside developer cannot start unaided."
        )
    else:
        verdict, why = "unknown", (
            "The fetched pages did not establish how a developer obtains credentials, so "
            "buildability cannot be judged."
        )

    return {"verdict": verdict, "reasoning": why + " (Derived from access, auth and api_surface.)"}


def downgrade_unsupported_confidence(record: AppRecord) -> AppRecord:
    """Force confidence to low when the record did not actually establish anything.

    Models will happily report `confidence: high` on a record whose every substantive field
    is unknown, or which cites no evidence. High confidence in nothing is a contradiction,
    and it is the field a reader trusts to spot thin rows, so it is corrected here rather
    than left to the model's discretion.
    """
    if record.confidence == Confidence.low:
        return record

    auth_known = record.auth is not None and record.auth.method != AuthMethod.unknown
    access_known = record.access is not None and record.access.tier != AccessType.unknown
    build_known = (
        record.buildability is not None
        and record.buildability.verdict != BuildabilityVerdict.unknown
    )

    if not record.evidence or not (auth_known or access_known or build_known):
        record.confidence = Confidence.low
    return record
