"""Pydantic models mirroring schema.json.

Anything the fetched pages did not support is None — never a guess.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    oauth2 = "oauth2"
    api_key = "api_key"
    basic_auth = "basic_auth"
    jwt = "jwt"
    mtls = "mtls"
    saml = "saml"
    none = "none"
    other = "other"
    unknown = "unknown"


class AccessType(str, Enum):
    self_serve = "self_serve"
    gated = "gated"
    mixed = "mixed"
    unknown = "unknown"


class BuildabilityVerdict(str, Enum):
    easy = "easy"
    moderate = "moderate"
    hard = "hard"
    blocked = "blocked"
    unknown = "unknown"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Auth(BaseModel):
    """How an already-registered developer signs API calls."""

    method: AuthMethod = AuthMethod.unknown
    notes: Optional[str] = None


class Access(BaseModel):
    """How a first-time developer gets credentials at all."""

    type: AccessType = AccessType.unknown
    notes: Optional[str] = None


class ApiSurface(BaseModel):
    rest: Optional[bool] = None
    graphql: Optional[bool] = None
    webhooks: Optional[bool] = None
    sdks: Optional[list[str]] = None
    notes: Optional[str] = None


class Mcp(BaseModel):
    exists: Optional[bool] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class Buildability(BaseModel):
    verdict: BuildabilityVerdict = BuildabilityVerdict.unknown
    reasoning: Optional[str] = None


class Evidence(BaseModel):
    url: str
    claim: str
    accessed_at: Optional[str] = None


class AppSeed(BaseModel):
    """Raw entry loaded from data/apps.json before any research happens."""

    number: int
    name: str
    category: str
    hint_url: Optional[str] = None


class AppRecord(BaseModel):
    """Fully researched record for one app, matching schema.json."""

    number: int
    name: str
    category: str
    hint_url: Optional[str] = None
    one_liner: Optional[str] = None
    auth: Optional[Auth] = None
    access: Optional[Access] = None
    api_surface: Optional[ApiSurface] = None
    mcp: Optional[Mcp] = None
    buildability: Optional[Buildability] = None
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: Confidence = Confidence.low
