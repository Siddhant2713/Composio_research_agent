"""Pydantic models mirroring schema.json — the six-field app record plus identity fields."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    oauth2 = "oauth2"
    api_key = "api_key"
    basic_auth = "basic_auth"
    jwt = "jwt"
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
    method: AuthMethod
    notes: str = ""


class Access(BaseModel):
    type: AccessType
    notes: str = ""


class ApiSurface(BaseModel):
    rest: bool = False
    graphql: bool = False
    webhooks: bool = False
    sdks: list[str] = Field(default_factory=list)
    notes: str = ""


class Mcp(BaseModel):
    exists: bool = False
    url: Optional[str] = None
    notes: str = ""


class Buildability(BaseModel):
    verdict: BuildabilityVerdict
    reasoning: str = ""


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
    one_liner: str
    auth: Auth
    access: Access
    api_surface: ApiSurface
    mcp: Optional[Mcp] = None
    buildability: Buildability
    evidence: list[Evidence] = Field(min_length=1)
    confidence: Confidence
