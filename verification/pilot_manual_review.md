# Phase 1 — manual review of raw model output

Gate: *"Manual read of all 3 raw LLM outputs confirms no invented facts beyond what the
fetched pages actually say."*

Method: for each record, every claim was grepped against the exact page text that fed the
extraction (`data/pilot/<app>.sources.txt`), and each evidence URL was re-fetched.

## Defects found and fixed

### 1. Navigation chrome read as capability evidence (the significant one)

Both Stripe and DealCloud were tagged `mcp.exists: true`. The entire basis was the string
"Model Context Protocol" / "MCP" appearing in a **sidebar nav list**:

```
File uploads
AI tools
Agent plugins
Model Context Protocol      <- the only "evidence"
Agent skills
```

On DealCloud the same nav block repeated on all 9 fetched pages, so the claim looked
corroborated by many sources when it was one menu, duplicated. A menu entry is not a
statement that the product ships an MCP server, and across 100 apps this would have
inflated every capability field, not just MCP.

Fixed three ways, because markup heuristics alone are fragile:
- `fetch.py` strips `nav`/`aside`/`footer`/`header`, navigation ARIA roles, and nav-ish
  class/id elements, and prefers the `<main>` subtree.
- `fetch.strip_shared_boilerplate()` drops short lines repeating across ≥60% of a site's
  pages — content-based, so it catches chrome the selectors miss.
- The extraction prompt states that a bare capability name in a link list is not evidence.

A regression test (`test_no_capability_claimed_from_navigation_alone`) now fails any
`mcp.exists: true` that carries neither a URL nor substantive notes.

### 2. Over-aggressive chrome stripping deleted whole pages

The first version of the fix decomposed every element whose class matched a nav pattern.
Stripe's outer content wrapper carries `Sidebar--expanded` among its classes, so the whole
document was removed — DealCloud dropped to 0 fetched pages and Stripe to 3, with
misleading `page too thin` failures. Caught by re-running the pilot and noticing the page
counts collapse. Chrome removal now skips any element holding >30% of the page text or
>2000 characters, so a wrapper can never be mistaken for chrome.

### 3. Geo-varying page content, and a claim attributed to the wrong page

Stripe's record said access is "invite-only in India". That sentence is real and was in the
fetched corpus — but it came from `stripe.com/in/contact/sales`, served because the
pipeline runs from an Indian IP, while the cited evidence URL was
`docs.stripe.com/get-started`, which does not say it. Two lessons carried into Phase 2:
fetch location silently changes the answer for global-vs-regional access, and a claim can
be traceable to *the corpus* yet still be attached to the wrong URL.

### 4. Corpus drift changed the auth verdict

Between runs, Telegram's fetched page set shifted from Bot API pages toward MTProto/SRP
pages, and `auth` moved from `api_key` to `other` — the model described the client protocol
instead of the integration-facing Bot API. Two fixes: the prompt now defines the auth enum
by mechanism (a long-lived bot token is an `api_key`) and says to describe the API a
third-party integration would use; and second-hop link harvesting is biased toward the
hint URL's own section, so discovery stops drifting across a large docs site.

## Final pilot verdicts

| App | auth | access | buildability | confidence | evidence |
| --- | --- | --- | --- | --- | --- |
| Telegram | `api_key` (bot token) | `self_serve` | easy | high | 5 |
| Stripe | `api_key` | `self_serve` | easy | high | 4 |
| DealCloud | `oauth2` (client credentials) | **`gated`** | moderate | high | 4 |

DealCloud's `auth` settled on `oauth2` rather than `api_key`: its own auth docs call
"OAuth2 Client Credentials" the most common method for API integrations and show a
`grant_type` exchange, with API keys offered alongside. That is the more accurate reading of
the fetched pages. The trap the case exists to test — thorough public docs being mistaken
for self-serve access — is still correctly avoided: `access` is `gated`, cited to the
credential-obtaining path, not to the quality of the reference docs.

After the nav-chrome fix, `mcp.exists` is `null` for both Stripe and DealCloud, each with a
note explaining that the only trace was an undescribed menu entry. That is the intended
behaviour: absence of substantiation is reported as unknown, not as a capability.

## Claims spot-checked against source text

| Claim | Source check |
| --- | --- |
| Telegram bot tokens come from @BotFather | present in fetched text (12 hits) |
| Telegram TDLib / Gateway API exist | present (12 / 8 hits) |
| Telegram api_id + api_hash via my.telegram.org | present on `core.telegram.org/api/obtaining_api_id` |
| Stripe uses API keys, Basic or Bearer auth | present on `docs.stripe.com/api/authentication` |
| Stripe SDK list (Ruby/Python/PHP/Java/Node/Go/.NET) | present on `docs.stripe.com/api` |
| DealCloud "Schedule a demo", no self-serve signup | present on `intapp.com/dealcloud` |
| DealCloud REST client + Python/C# SDKs | present on the `api.docs.dealcloud.com/sdk/*` pages |

No claim was found that had no basis anywhere in the fetched corpus. The failures were
*attribution* and *over-reading nav*, not free invention.
