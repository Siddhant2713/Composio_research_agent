"""Research one app end to end.

This is the single implementation of the pipeline. Both the Phase 1 pilot and the 100-app
batch call `research_app`, so the batch cannot drift from what the pilot validated.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from urllib.parse import urlparse

from agent import discover, fetch as fetchmod
from agent.extract import extract_record
from agent.gemini import model_chain
from agent.models import AppRecord, AppSeed

MAX_FIRST_HOP = 8
MAX_SECOND_HOP = 5
MAX_PAGES = 10
PAGE_CHARS = 5000


def gather_pages(client, seed: AppSeed, log: dict) -> list[fetchmod.Page]:
    """Discover candidate URLs, fetch them, then fetch a second hop of relevant links."""
    proposed, raw_proposals, proposal_model = discover.propose_candidates(client, seed)
    log["raw_candidate_proposals"] = raw_proposals
    log["candidate_proposal_model"] = proposal_model

    domain = discover.root_domain(seed.hint_url)
    candidates = discover.dedupe(
        ([seed.hint_url] if seed.hint_url else [])
        + proposed
        + discover.pattern_candidates(domain)
    )
    log["candidates_considered"] = candidates

    pages: list[fetchmod.Page] = []
    failures: list[dict] = []

    with fetchmod.make_client() as http:
        for url in candidates[:MAX_FIRST_HOP]:
            result = fetchmod.fetch(http, url, max_chars=PAGE_CHARS)
            if isinstance(result, fetchmod.Page):
                if all(result.url != p.url for p in pages):
                    pages.append(result)
            else:
                failures.append(asdict(result))

        # Second hop: follow auth/access-looking links off the pages that worked, biased
        # toward the section the hint URL points at.
        prefer = None
        if seed.hint_url:
            segments = [s for s in urlparse(seed.hint_url).path.split("/") if s]
            prefer = f"/{segments[0]}" if segments else None

        second_hop: list[str] = []
        for page in list(pages):
            second_hop.extend(fetchmod.harvest_links(page, limit=6, prefer_prefix=prefer))
        already = {p.url.rstrip("/").lower() for p in pages}
        second_hop = [
            u for u in discover.dedupe(second_hop) if u.rstrip("/").lower() not in already
        ]
        log["second_hop_considered"] = second_hop

        for url in second_hop[:MAX_SECOND_HOP]:
            if len(pages) >= MAX_PAGES:
                break
            result = fetchmod.fetch(http, url, max_chars=PAGE_CHARS)
            if isinstance(result, fetchmod.Page):
                if all(result.url != p.url for p in pages):
                    pages.append(result)
            else:
                failures.append(asdict(result))

    log["boilerplate_lines_removed"] = fetchmod.strip_shared_boilerplate(pages)
    log["fetch_failures"] = failures
    log["sources_fetched"] = [
        {
            "url": p.url,
            "requested_url": p.requested_url,
            "status": p.status,
            "title": p.title,
            "chars": len(p.text),
            "accessed_at": p.accessed_at,
        }
        for p in pages
    ]
    return pages[:MAX_PAGES]


def no_docs_record(seed: AppSeed, failures: list[dict]) -> AppRecord:
    """The record for an app whose documentation produced no readable text.

    Two very different causes, and conflating them produces a confidently wrong answer:

    - Nothing was *reachable* (DNS failures, 403, 404 everywhere). There is no public path
      an outside developer could follow, so the spec's verdict applies: gated, buildability
      "no".
    - Pages *answered 2xx* but rendered their content client-side, so we know documentation
      exists and simply could not read it. Calling that "gated" would be a false claim about
      a product that may well be self-serve, so it is reported as unknown instead.

    Either way no API shape is guessed and evidence stays empty.
    """
    reasons = "; ".join(
        f"{f['requested_url']} ({f['reason']})" for f in failures[:6]
    ) or "no candidate URLs produced"
    reachable_but_unreadable = any(f.get("kind") == "thin" for f in failures)

    if reachable_but_unreadable:
        access = {
            "tier": "unknown",
            "notes": (
                "Documentation pages responded successfully but render their content in the "
                "browser, so no text could be extracted and the credential path could not be "
                f"read. This is a limit of this pipeline, not evidence of gating. Tried: {reasons}"
            ),
        }
        buildability = {
            "verdict": "unknown",
            "reasoning": (
                "Documentation exists but is client-rendered, so nothing could be read to "
                "judge buildability. Deliberately not scored as unbuildable."
            ),
        }
        auth_notes = "Documentation was reachable but client-rendered; no text to read."
    else:
        access = {
            "tier": "gated",
            "notes": (
                "No public developer documentation could be fetched at all, so there is no "
                f"self-serve path an outside developer could follow. Tried: {reasons}"
            ),
        }
        buildability = {
            "verdict": "no",
            "reasoning": (
                "No reachable public API documentation, so an outside developer has no "
                "documented way in. Not a judgement about the API's quality — nothing was "
                "readable to judge."
            ),
        }
        auth_notes = "No public documentation was reachable."

    return AppRecord.model_validate(
        {
            "number": seed.number,
            "name": seed.name,
            "category": seed.category,
            "hint_url": seed.hint_url,
            "one_liner": None,
            "auth": {"method": "unknown", "notes": auth_notes},
            "access": access,
            "api_surface": None,
            "mcp": None,
            "buildability": buildability,
            "evidence": [],
            "confidence": "low",
        }
    )


def research_app(client, seed: AppSeed) -> dict:
    """Research one app. Returns a log dict containing the record plus full provenance."""
    log: dict = {
        "app": seed.name,
        "number": seed.number,
        "category": seed.category,
        "model_chain": model_chain(),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    pages = gather_pages(client, seed, log)

    if not pages:
        log["no_public_docs"] = True
        log["record"] = no_docs_record(seed, log.get("fetch_failures", [])).model_dump(mode="json")
    else:
        record, raw, extraction_model = extract_record(client, seed, pages)
        log["raw_extraction_output"] = raw
        log["extraction_model"] = extraction_model
        log["record"] = record.model_dump(mode="json")

    log["sources_text"] = "\n".join(
        f"===== {p.url}\nTITLE: {p.title}\nACCESSED: {p.accessed_at}\n\n{p.text}\n"
        for p in pages
    )
    log["finished_at"] = datetime.now(timezone.utc).isoformat()
    return log


def summarize(log: dict) -> str:
    """One-line human summary of a finished app log."""
    record = log.get("record") or {}
    if not record:
        return f"ERROR {log.get('error', 'unknown')}"
    auth = (record.get("auth") or {}).get("method", "null")
    access = (record.get("access") or {}).get("tier", "null")
    build = (record.get("buildability") or {}).get("verdict", "null")
    return (
        f"auth={auth} access={access} build={build} "
        f"conf={record.get('confidence')} evidence={len(record.get('evidence', []))}"
        + ("  [no public docs]" if log.get("no_public_docs") else "")
    )
