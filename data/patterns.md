# What the 100 apps say

Every figure below is a count in `data/patterns.json`, computed from `pass2_full.json`.
All cross-tabs sum to exactly 100; the cross-check is enforced in `agent/patterns.py` and
fails the build if any bucket drops an app.

## Headlines

1. **58 of 100 apps let an unaffiliated developer obtain working credentials on their own,
   and only 5 are gated behind sales or partner approval.** The common intuition that
   enterprise software hides its API behind a salesperson is not what the evidence shows:
   outright gating is the rarest outcome in the set, behind self-serve (58), unknown (35)
   and mixed (2).

2. **Category predicts access far better than company size does: Support and Helpdesk is
   80% self-serve (8/10), while Finance and Fintech and Data, SEO and Scraping are both 40%
   (4/10).** The apps a developer can start using this afternoon cluster in categories where
   the buyer is the developer; where the buyer is a compliance or procurement function, the
   credential path gets longer.

3. **Every one of the 5 apps rated hard to build against is blocked by exactly the same
   thing — a partner or sales gate (5 of 5).** This is the falsifiable one: filter the table
   to `buildability = hard` and every row should show a partner or sales gate as its blocker,
   with no other cause appearing. No app in the set is hard to build against because its API
   is technically awkward.

4. **Among the 58 apps whose access path was established, API keys beat OAuth2 by 26 to 18.**
   A long-lived secret the developer copies out of a settings page remains the most common
   way in, which matters for an integration platform: those 26 need a credential vault, while
   the 18 OAuth2 apps need a redirect flow and token refresh.

5. **42 of 100 apps describe an MCP server in their own documentation.** MCP is no longer a
   niche: it appears in more apps' docs than any single blocker category, and 1 app explicitly
   documents not having one.

6. **The largest obstacle in this research was not gating but readability — 35 apps end with
   access unknown, 6 of them because their documentation renders in the browser and returns an
   empty HTML shell to a plain fetch.** Those are reported as unknown rather than guessed.
   This is a limit of the pipeline, not a finding about the products, and it is the first
   thing a headless browser would fix.

## Where the numbers come from

| Cross-tab | What it answers |
| --- | --- |
| `auth_by_category` | which auth pattern dominates each category |
| `access_by_category` | the self-serve share behind headline 2 |
| `buildability_by_blocker` | headline 3: every `hard` row is a partner/sales gate |
| `access_by_auth` | headline 4: 26 api_key vs 18 oauth2 among self-serve |
| `blocker_by_category` | where each blocker concentrates |

Blockers use a fixed vocabulary rather than free text, so they are countable:
`none`, `no_public_api`, `docs_not_machine_readable`, `paid_plan_gate`,
`partner_or_sales_gate`, `app_review_gate`, `admin_account_only`, `unknown`.

## Reading these honestly

Pass 2 requires every field to quote a line that is verifiably present on a fetched page, so
it reports `unknown` more often than Pass 1 did (access unknown: 35 vs 20). The counts above
are therefore a floor, not a census: they describe what the documentation demonstrably said,
not everything that is true. Pass 2 also ran entirely on the weakest model in the fallback
chain because the stronger ones were quota-exhausted, which inflates the unknown counts
further — see `verification/pass2_review.md`.
