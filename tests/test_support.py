"""Unit tests for the Pass-2 quote verification and derived buildability."""
from agent.extract import derive_buildability, quote_is_real, verify_support
from agent.fetch import Page


def page(text: str, url: str = "https://example.com/docs") -> Page:
    return Page(url=url, requested_url=url, status=200, title="t", text=text)


PAGE_TEXT = (
    "Getting started\n"
    "Create an account, then generate an API key from the Settings page.\n"
    "The API is organized around REST and returns JSON.\n"
)


def test_quote_matches_ignoring_whitespace_and_case():
    p = page(PAGE_TEXT)
    assert quote_is_real("generate an API key from the   SETTINGS page", p)


def test_quote_matches_despite_html_punctuation_artefacts():
    """HTML-to-text splits inline tags, so a real sentence can gain a space before its period."""
    p = page("The Stripe API is organized around REST .\nOur API has predictable URLs.")
    assert quote_is_real("The Stripe API is organized around REST.", p)


def test_quote_not_on_page_is_rejected():
    assert not quote_is_real("Contact our sales team for API access", page(PAGE_TEXT))


def test_short_fragment_is_not_accepted_as_support():
    """Any few words can be found in a long page; that is not evidence."""
    assert not quote_is_real("the API", page(PAGE_TEXT))


def test_bare_capability_name_is_not_a_supporting_quote():
    """A menu entry is present on the page but says nothing; it must not count as support."""
    nav = page("Docs\nAI tools\nModel Context Protocol\nAgent skills\nExtend the platform")
    assert not quote_is_real("Model Context Protocol", nav)


def test_unsupported_field_is_blanked_and_reported():
    allowed = {"https://example.com/docs": page(PAGE_TEXT)}
    fields = {"access": {"tier": "gated", "notes": "n"}}
    support = {
        "access": {
            "url": "https://example.com/docs",
            "quote": "Access requires approval from your account manager",
        }
    }
    verified, rejected = verify_support(support, fields, allowed)

    assert "access" not in verified
    assert fields["access"]["tier"] == "unknown"
    assert rejected and "access" in rejected[0]


def test_supported_field_survives():
    allowed = {"https://example.com/docs": page(PAGE_TEXT)}
    fields = {"access": {"tier": "self_serve", "notes": "n"}}
    support = {
        "access": {
            "url": "https://example.com/docs",
            "quote": "Create an account, then generate an API key from the Settings page.",
        }
    }
    verified, rejected = verify_support(support, fields, allowed)

    assert verified["access"]["url"] == "https://example.com/docs"
    assert fields["access"]["tier"] == "self_serve"
    assert not rejected


def test_support_citing_unfetched_url_is_rejected():
    allowed = {"https://example.com/docs": page(PAGE_TEXT)}
    fields = {"mcp": {"exists": True, "notes": "n"}}
    support = {"mcp": {"url": "https://elsewhere.test/mcp", "quote": "We ship an MCP server."}}
    verified, rejected = verify_support(support, fields, allowed)

    assert "mcp" not in verified
    assert fields["mcp"]["exists"] is None
    assert "unfetched" in rejected[0]


def test_buildability_follows_access_and_auth():
    surface = {"rest": True, "graphql": False, "webhooks": False, "sdks": []}
    assert derive_buildability(
        {"access": {"tier": "self_serve"}, "auth": {"method": "api_key"}, "api_surface": surface}
    )["verdict"] == "easy"
    assert derive_buildability(
        {"access": {"tier": "gated"}, "auth": {"method": "oauth2"}, "api_surface": surface}
    )["verdict"] == "hard"
    assert derive_buildability(
        {"access": {"tier": "mixed"}, "auth": {"method": "api_key"}, "api_surface": surface}
    )["verdict"] == "moderate"
    assert derive_buildability(
        {"access": {"tier": "unknown"}, "auth": {"method": "unknown"}, "api_surface": None}
    )["verdict"] == "unknown"


def test_buildability_is_deterministic():
    inputs = {
        "access": {"tier": "self_serve"},
        "auth": {"method": "api_key"},
        "api_surface": {"rest": True},
    }
    assert derive_buildability(inputs) == derive_buildability(inputs)
