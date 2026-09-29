# Pass 2 — what changed, and what it cost

Pass 1 was audited, the failure patterns were turned into prompt and code changes, and all
100 apps were re-researched. This is what that produced, including the parts that got worse.

## What the Pass-1 audit found

Scored by the adversarial pass over 120 rows (20 stratified apps × 6 fields):

| Field | Pass 1 | The specific failure |
| --- | --- | --- |
| `auth.method` | 75.0% | mostly sound |
| `api_surface` | 55.0% | booleans asserted from feature lists |
| `access.tier` | 52.5% | 4 rows rested on nothing, 2 on marketing copy |
| `mcp.exists` | 47.5% | capability claimed from menu entries |
| `evidence_supports_claims` | 30.0% | the cited URL did not say what was claimed |
| `buildability.verdict` | 25.0% | no page ever states it; it was being invented |
| **Overall** | **47.5%** | |

The common root cause: **nothing forced the model to point at a line.** It could assert a
value, cite a plausible URL, and never be held to what that page actually said.

## The three changes

1. **Every field must quote its source, and the quote is verified in code.** `support.<field>`
   carries a `{url, quote}`; the quote is checked as a real substring of that page's fetched
   text. Fail and the field is reset to unknown and listed in `unsupported_fields`.
2. **A quote must be a sentence** (≥ 5 words). This closes the menu-entry loophole directly:
   "Model Context Protocol" on its own can no longer prove a product ships an MCP server.
3. **`buildability` is derived, not asserted** — computed from `access`, `auth` and
   `api_surface`. It scored worst precisely because it is a synthesis no page states, so
   asking a model to source it invited invention. It is now reproducible by construction.

## What that bought: evidence integrity

| Measure | Pass 1 | Pass 2 |
| --- | --- | --- |
| Evidence items carrying a verified quote | 0 of 309 | **287 of 287 (100%)** |
| Fields rejected for unverifiable support | n/a | 133 |
| — of which the quote was **not on the page** | n/a | **41** |
| Records with at least one verified supporting line | n/a | 88 of 100 |

Those **41 rejections are caught hallucinations**: the model produced a supporting quote that
does not exist in the text it was given, or cited a page the pipeline never fetched. Pass 1
had no mechanism to notice any of them — they would have shipped as evidence-backed claims.

## What it cost: coverage

| | Pass 1 | Pass 2 |
| --- | --- | --- |
| `access: self_serve` | 66 | 58 |
| `access: unknown` | 20 | 34 |
| `auth: unknown` | 24 | 35 |
| `confidence: high` | 74 | 60 |

Pass 2 answers "unknown" considerably more often. Some of that is the point — an unsupported
claim *should* collapse to unknown. But not all of it is virtuous, and the breakdown says so:
of the 133 rejected fields, only 41 were demonstrably wrong. The other **92 were rejected
because the model simply did not supply a quote at all**, which is not the same as evidence
being absent from the page.

## The confound, stated plainly

**Every Pass-2 extraction ran on `gemini-3.5-flash-lite`** — the weakest model in the fallback
chain — because all four stronger models were quota-exhausted for the duration of the run.
Pass 1 ran mostly on `gemini-3.6-flash` and `gemini-3-flash-preview`.

A weaker model is more likely to omit an optional `support` block than to be unable to find
evidence. So the coverage drop is partly the prompt change working as designed and partly a
model downgrade, and this comparison cannot cleanly separate the two.

The comparison is therefore **not a clean measurement of the prompt patch alone**. What can be
said without qualification is narrower and still worth saying: even handicapped by a weaker
model, Pass 2 produces strictly better-evidenced output — every surviving citation is
verifiable, and 41 fabricated ones were caught and removed.

Re-running Pass 2 on `gemini-3.6-flash` once quota resets would settle it. That run is one
command (`python -m agent.run --pass pass2 --force`) and is the first thing I would do with
more budget.

## The measured result: the gate failed

| | Pass 1 | Pass 2 | Change |
| --- | --- | --- | --- |
| **Overall** | **47.5%** | **45.4%** | **−2.1 pp** |
| `access.tier` | 52.5% | 55.0% | +2.5 |
| `mcp.exists` | 47.5% | 52.5% | +5.0 |
| `evidence_supports_claims` | 30.0% | 32.5% | +2.5 |
| `buildability.verdict` | 25.0% | 22.5% | −2.5 |
| `api_surface` | 55.0% | 47.5% | −7.5 |
| `auth.method` | 75.0% | 62.5% | −12.5 |

Spec 5 asked for a measurable gain. **There isn't one.** The three fields the patch targeted
all improved; the overall number still fell.

Decomposing it shows why:

| | Pass 1 | Pass 2 |
| --- | --- | --- |
| Rows where a value is **asserted** | 68.5% (n=54) | **72.1%** (n=43) |
| Rows where the record says **unknown** | 11.5% (n=26) | 20.3% (n=37) |

Pass 2 is more accurate on the claims it makes, and makes fewer of them. The auditor scores
an abstention by asking "does the page confirm 'unknown'?", which is nearly always no — so it
penalises honest abstention exactly as hard as being wrong, which is the precise behaviour
Pass 2 was built to have. That is a flaw in the instrument, not a defence of the result: the
honest reading is that this measurement cannot yet distinguish "declined to answer" from
"answered wrongly", and the headline number should be read with that in mind.

Fixing it means asking the auditor a different question for abstentions — "is the text
genuinely silent here?" — and re-scoring both passes identically. Worth noting: that flaw was
noticed *after* seeing a result I did not like, and fixing it would help Pass 2 more than
Pass 1 (37 abstentions against 26). Both numbers should be published if it is done.

## The quote requirement can reward cherry-picking

The most damaging finding, and it came from checking the auto-selected worked example rather
than trusting it.

The ranking picked **LinkedIn Ads / access.tier** as the showcase correction: Pass 1 said
`mixed`, Pass 2 said `self_serve` with the verified line *"Create a developer application in
the Developer Portal."* The judge moved from "no" to "yes". It looks like a clean fix.

It is the opposite. The same fetched page also contains:

> Step 1: Apply for API Access
> After you build and test your application, apply for Standard tier access. To upgrade to
> Advertising API Standard tier, submit a tier upgrade request with a video demonstrating how
> your platform creates, edits, or optimizes LinkedIn campaigns.

Pass 1's `mixed` was the **more accurate** answer. Pass 2 found one line that supported a
simpler claim and never had to weigh the lines that contradicted it.

**Requiring a supporting quote proves a claim is _sourced_; it does not prove the claim is
_right_.** Nothing in the design forces the model to look for disconfirming evidence on the
same page, and the auditor shares the blind spot, because it too is asked to find a supporting
line rather than to weigh the page as a whole. This partly explains why accuracy did not
improve despite evidence integrity improving sharply.

The fix is a disconfirmation step: for `access` specifically, require the model to state
whether the page contains any gate language (apply, request access, upgrade, review, contact
sales) and to reconcile it before answering. That is the next change I would make, and it is
not in this pass.

The worked example shipped in `worked_example.json` is therefore a hand-checked one —
**Pinterest / mcp.exists** — not the auto-selected pick. Pass 1 read *"Pinterest MCP is on the
way"* as an MCP server existing (`true`); Pass 2 read the same line correctly as a capability
that has not shipped (`false`). Anyone can check that against the quoted line.

## Judge defects found while building the auditor

The measuring instrument needed fixing before it could measure anything:

- **A sceptical framing made "yes" unreachable.** The first auditor returned *zero* `yes`
  verdicts across 78 rows, and 54 of those rows were self-contradictory — answering "no"
  while quoting a line that supported the claim. It was scoring nothing.
- **The fix was ordering, not wording.** The schema now asks for `supporting_line` and
  `evidence_type` *before* `confirmed`, so the verdict follows the evidence instead of
  preceding it. Verdicts became a real spread immediately.
- **Per-field calls exhausted the rate limit** by sending the same page corpus six times per
  app. All six fields are now judged in one request.
- **Groq's free tier allows ~8k tokens/minute** and one audit call is several thousand, so
  consecutive apps tripped a `retry-after` of up to 30 minutes and stalled the batch. Calls
  are now paced under the limit and any honored wait is capped.
