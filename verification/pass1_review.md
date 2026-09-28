# Phase 2 — review of the 100-app pass

What the batch itself exposed, and what was fixed. The pipeline logic is unchanged from
Phase 1; everything here is about accuracy and survivability at 100 runs.

## Defects found and fixed

### 1. Bot blocking read as "no docs" (403)

`developer.salesforce.com` returned **403** to a request carrying only a `User-Agent`, so
Salesforce fell back to marketing pages and produced `auth: unknown`. Sending the rest of a
real browser's headers (`Accept-Language`, `Sec-Fetch-*`, `Sec-Ch-Ua`, …) turns it into a
200. Left unfixed, this would have quietly degraded an unknown number of the 100.

### 2. Client-rendered docs reported as gated — a confidently wrong answer

Seven apps produced no readable text. The first implementation applied the spec's rule to
all of them: `access: gated`, `buildability: "no"`. But five — Lark, Gumroad, Binance,
QuickBooks, Consensus — had answered **HTTP 200** and simply rendered their documentation in
the browser. Their docs plainly exist, and several (QuickBooks, Gumroad) are self-serve. The
pipeline was asserting the opposite.

`FetchFailure` now carries a `kind`, and the two causes are handled separately:

| Cause | Verdict |
| --- | --- |
| Nothing reachable (DNS failure, 403, 404 everywhere) | `gated` + `buildability: no` — the spec's rule |
| 2xx but empty HTML shell (client-rendered) | `access: unknown` + `buildability: unknown` |

PitchBook (403 throughout) correctly keeps `gated`/`no`, matching the spec's expectation for
partner-gated apps. The rest are now honest about being a pipeline limit rather than a
finding about the product.

### 3. The Phase 1 anti-trap wording over-corrected

Phase 1 hardened the prompt so that thorough documentation could not be mistaken for
self-serve access (the DealCloud trap). At 100 apps that rule proved too strict in the other
direction: **26 records came back `access: unknown` while their own notes described a
developer creating their own credentials.**

- Pipedrive — "the API token can be obtained manually from the Pipedrive settings"
- Harvest — "creating personal access tokens and OAuth2 applications from the account"
- Gladly — "setting up an account and generating tokens in settings"
- higgsfield — "creating credentials in the Higgsfield Console"
- GitHub, Stripe, SendGrid, Datadog — similar

**Stripe regressed from `self_serve` in Phase 1 to `unknown` here**, which is what made the
over-correction obvious: the same app, the same pipeline, a worse answer.

The rule is now symmetric — decide from positive signals on *either* side. Generating your
own key in the product's own settings is self-serve even when the docs never narrate a
signup funnel; `gated` requires a positive gate signal (contact sales, apply, waitlist,
app review, or credentials presupposing a vendor-provisioned tenant). Both failure modes are
now named explicitly in the prompt, so neither correction erases the other.

### 4. `--force` destroyed good records during a network outage

A transient DNS failure hit midway through a `--force` re-run. Every app errored, and each
error stub overwrote the real record underneath it — the merged set dropped from 99 to 91.
A failed attempt now refuses to overwrite an existing record, so a re-run can only improve
the dataset, never damage it.

### 5. Confidence asserted on empty records

Pylon returned `auth/access/buildability` all `unknown` with `confidence: high`. Confidence
is the field a reader uses to spot thin rows, so it is now downgraded deterministically when
a record carries no evidence or establishes nothing (`downgrade_unsupported_confidence`,
unit-tested) rather than left to the model.

### 6. Quota retries wasted the batch's time

Free-tier quota is per-model, and the runner was retrying an already-exhausted model three
times per call — roughly 20s of sleeping each time, on every app. Quota errors now fall
through to the next model instantly and that model stays skipped for the rest of the
process, with a single pause if the whole chain is exhausted.

## MCP claims — audited, not assumed

39 of 99 records report an MCP server, which is high enough to suspect the Phase 1
nav-chrome defect had returned. Spot-checking the two weakest-looking notes against the
fetched text:

- Vonage — the page carries a real descriptive sentence ("MCP Server — Communicate with
  tools through a standardized interface…"), not just a menu entry.
- Twenty — "MCP server" sits in a product feature list on a pricing page, where the list is
  the content rather than chrome, and the note says exactly that.

The Phase 1 fix is holding: notes now state the basis for the claim instead of asserting a
capability from a sidebar link.

## Known limits carried forward

- **JavaScript-rendered documentation** is invisible to plain HTTP fetching. Those apps are
  reported `unknown`, never guessed. A headless browser would close this gap.
- **Fetch geography** shapes answers: Salesforce and Stripe both served India-specific pages
  (Stripe's said "invite only in India"). Access verdicts reflect where the fetch ran from.
- **Hosts that 403 regardless of headers** are recorded as fetch failures rather than
  silently dropped.
